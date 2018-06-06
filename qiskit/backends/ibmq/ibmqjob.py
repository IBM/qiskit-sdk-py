# -*- coding: utf-8 -*-

# Copyright 2017, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""IBMQJob module

This module is used for creating asynchronous job objects for the
IBM Q Experience.
"""

from concurrent import futures
import time
import logging
import pprint
import json
import numpy

from qiskit.backends import BaseJob
from qiskit.backends.basejob import JobStatus
from qiskit._qiskiterror import QISKitError
from qiskit._result import Result
from qiskit._resulterror import ResultError
from qiskit._compiler import compile_circuit

logger = logging.getLogger(__name__)


class IBMQJob(BaseJob):
    """IBM Q Job class

    Attributes:
        _executor (futures.Executor): executor to handle asynchronous jobs
    """
    _executor = futures.ThreadPoolExecutor()

    def __init__(self, q_job, api, is_device):
        """IBMQJob init function.

        Args:
            q_job (QuantumJob): job description
            api (IBMQuantumExperience): IBM Q API
            is_device (bool): whether backend is a real device  # TODO: remove this after Qobj
        """
        super().__init__()
        self._q_job = q_job
        self._qobj = q_job.qobj
        self._api = api
        self._job_id = None  # this must be before creating the future
        self._backend_name = self._qobj.get('config').get('backend_name')
        self._status = JobStatus.INITIALIZING
        self._future_submit = self._executor.submit(self._submit)
        self._status_msg = None
        self._cancelled = False
        self._exception = None
        self._is_device = is_device
        self._from_api = False

    @classmethod
    def from_api(cls, job_info, api, is_device):
        """Instantiates job using information returned from
        IBMQuantumExperience about a particular job.

        Args:
            job_info (dict): This is the information about a job returned from
                the API. It has the simplified structure:

                {'backend': {'id', 'backend id string',
                             'name', 'ibmqx4'},
                 'id': 'job id string',
                 'qasms': [{'executionId': 'id string',
                            'qasm': 'qasm string'},
                          ]
                 'status': 'status string',
                 'seed': '1',
                 'shots': 1024,
                 'status': 'status string',
                 'usedCredits': 3,
                 'userId': 'user id'}
            api (IBMQuantumExperience): IBM Q API
            is_device (bool): whether backend is a real device  # TODO: remove this after Qobj

        Returns:
            IBMQJob: an instance of this class
        """
        job_instance = cls.__new__(cls)
        job_instance._status = JobStatus.QUEUED
        job_instance._backend_name = job_info.get('backend').get('name')
        job_instance._api = api
        job_instance._job_id = job_info.get('id')
        job_instance._exception = None  # needs to be before status call below
        # update status (need _api and _job_id)
        # pylint: disable=pointless-statement
        job_instance.status
        job_instance._status_msg = None
        job_instance._cancelled = False
        job_instance._is_device = is_device
        job_instance._from_api = True
        return job_instance

    def result(self, timeout=None, wait=5):
        """Return the result from the job.

        Args:
           timeout (int): number of seconds to wait for job
           wait (int): time between queries to IBM Q server

        Returns:
            Result: Result object

        Raises:
            IBMQJobError: exception raised during job initialization
        """
        # pylint: disable=arguments-differ
        while self._status == JobStatus.INITIALIZING:
            if self._future_submit.exception():
                raise IBMQJobError('error submitting job: {}'.format(
                    repr(self._future_submit.exception())))
            time.sleep(0.1)
        this_result = self._wait_for_job(timeout=timeout, wait=wait)
        if self._is_device and self.done:
            _reorder_bits(this_result)
        if this_result.get_status() == 'ERROR':
            self._status = JobStatus.ERROR
        else:
            self._status = JobStatus.DONE
        return this_result

    def cancel(self):
        """Attempt to cancel job. Currently this is only possible on
        commercial systems.
        Returns:
            bool: True if job can be cancelled, else False.

        Raises:
            QISKitError: if server returned error
        """
        if self._is_commercial:
            hub = self._api.config['hub']
            group = self._api.config['group']
            project = self._api.config['project']
            response = self._api.cancel_job(self._job_id, hub, group, project)
            if 'error' in response:
                err_msg = response.get('error', '')
                self._exception = QISKitError('Error cancelling job: %s' % err_msg)
                raise QISKitError('Error canceelling job: %s' % err_msg)
            else:
                self._cancelled = True
                return True
        else:
            self._cancelled = False
            return False

    @property
    def status(self):
        if self._status == JobStatus.INITIALIZING:
            stats = {'job_id': None,
                     'status': self._status,
                     'status_msg': 'job is begin initialized please wait a moment'}
            return stats
        job_result = self._api.get_job(self._job_id)
        stats = {'job_id': self._job_id}
        self._status = None
        _status_msg = None
        if 'status' not in job_result:
            self._exception = QISKitError("get_job didn't return status: %s" %
                                          (pprint.pformat(job_result)))
            raise QISKitError("get_job didn't return status: %s" %
                              (pprint.pformat(job_result)))
        elif job_result['status'] == 'RUNNING':
            self._status = JobStatus.RUNNING
            # we may have some other information here
            if 'infoQueue' in job_result:
                if 'status' in job_result['infoQueue']:
                    if job_result['infoQueue']['status'] == 'PENDING_IN_QUEUE':
                        self._status = JobStatus.QUEUED
                if 'position' in job_result['infoQueue']:
                    stats['queue_position'] = job_result['infoQueue']['position']
        elif job_result['status'] == 'COMPLETED':
            self._status = JobStatus.DONE
        elif job_result['status'] == 'CANCELLED':
            self._status = JobStatus.CANCELLED
        elif self.exception or self._future_submit.exception():
            self._status = JobStatus.ERROR
            if self._future_submit.exception():
                self._exception = self._future_submit.exception()
            self._status_msg = str(self.exception)
        elif 'ERROR' in job_result['status']:
            # ERROR_CREATING_JOB or ERROR_RUNNING_JOB
            self._status = JobStatus.ERROR
            self._status_msg = job_result['status']
        else:
            self._status = JobStatus.ERROR
            raise IBMQJobError('Unexpected behavior of {0}\n{1}'.format(
                self.__class__.__name__,
                pprint.pformat(job_result)))
        stats['status'] = self._status
        stats['status_msg'] = _status_msg
        return stats

    @property
    def queued(self):
        """
        Returns whether job is queued.

        Returns:
            bool: True if job is queued, else False.

        Raises:
            QISKitError: couldn't get job status from server
        """
        return self.status['status'] == JobStatus.QUEUED

    @property
    def running(self):
        """
        Returns whether job is actively running

        Returns:
            bool: True if job is running, else False.

        Raises:
            QISKitError: couldn't get job status from server
        """
        return self.status['status'] == JobStatus.RUNNING

    @property
    def done(self):
        """
        Returns True if job successfully finished running.

        Note behavior is slightly different than Future objects which would
        also return true if successfully cancelled.
        """
        return self.status['status'] == JobStatus.DONE

    @property
    def cancelled(self):
        return self._cancelled

    @property
    def exception(self):
        """
        Return Exception object previously raised by job else None

        Returns:
            Exception: exception raised by job
        """
        if isinstance(self._exception, Exception):
            self._status_msg = str(self._exception)
        return self._exception

    @property
    def _is_commercial(self):
        config = self._api.config
        # this check may give false positives so should probably be improved
        return config.get('hub') and config.get('group') and config.get('project')

    @property
    def job_id(self):
        """
        Return backend determined job_id (also available in status method).
        """
        while not self._job_id:
            # job is initializing and hasn't gotten a job_id yet.
            time.sleep(0.1)
        return self._job_id

    @property
    def backend_name(self):
        """
        Return backend name used for this job
        """
        return self._backend_name

    def _submit(self):
        """Submit job to IBM Q.

        Returns:
            dict: submission info including job id from server

        Raises:
            QISKitError: The backend name in the job doesn't match this backend.
            ResultError: If the API reported an error with the submitted job.
            RegisterSizeError: If the requested register size exceeded device
                capability.
        """
        qobj = self._qobj
        api_jobs = []
        for circuit in qobj['circuits']:
            job = {}
            if (('compiled_circuit_qasm' not in circuit) or
                    (circuit['compiled_circuit_qasm'] is None)):
                compiled_circuit = compile_circuit(circuit['circuit'])
                circuit['compiled_circuit_qasm'] = compiled_circuit.qasm(qeflag=True)
            if isinstance(circuit['compiled_circuit_qasm'], bytes):
                job['qasm'] = circuit['compiled_circuit_qasm'].decode()
            else:
                job['qasm'] = circuit['compiled_circuit_qasm']
            if 'name' in circuit:
                job['name'] = circuit['name']
            # convert numpy types for json serialization
            compiled_circuit = json.loads(
                json.dumps(circuit['compiled_circuit'],
                           default=_numpy_type_converter))
            job['metadata'] = {'compiled_circuit': compiled_circuit}
            api_jobs.append(job)
        seed0 = qobj['circuits'][0]['config']['seed']
        hpc = None
        if 'hpc' in qobj['config']:
            try:
                # Use CamelCase when passing the hpc parameters to the API.
                hpc = {
                    'multiShotOptimization':
                        qobj['config']['hpc']['multi_shot_optimization'],
                    'ompNumThreads':
                        qobj['config']['hpc']['omp_num_threads']
                }
            except (KeyError, TypeError):
                hpc = None
        backend_name = qobj['config']['backend_name']
        if backend_name != self._backend_name:
            raise QISKitError("inconsistent qobj backend "
                              "name ({0} != {1})".format(backend_name,
                                                         self._backend_name))
        submit_info = {}
        try:
            submit_info = self._api.run_job(api_jobs, backend=backend_name,
                                            shots=qobj['config']['shots'],
                                            max_credits=qobj['config']['max_credits'],
                                            seed=seed0,
                                            hpc=hpc)
        # pylint: disable=broad-except
        except Exception as err:
            self._status = JobStatus.ERROR
            self._exception = err
        if 'error' in submit_info:
            self._status = JobStatus.ERROR
            self._exception = IBMQJobError(str(submit_info['error']))
        self._job_id = submit_info.get('id')
        self._status = JobStatus.QUEUED
        return submit_info

    def _wait_for_job(self, timeout=60, wait=5):
        """Wait until all online ran circuits of a qobj are 'COMPLETED'.

        Args:
            timeout (float or None): seconds to wait for job. If None, wait
                indefinitely.
            wait (float): seconds between queries

        Returns:
            Result: A result object.

        Raises:
            QISKitError: job didn't return status or reported error in status
        """
        # qobj = self._q_job.qobj
        job_id = self.job_id
        # logger.info('Running qobj: %s on remote backend %s with job id: %s',
        #             qobj["id"], qobj['config']['backend_name'],
        #             job_id)
        start_time = time.time()
        api_result = self._api.get_job(job_id)
        while not (self.done or self.cancelled or self.exception or
                   self._status == JobStatus.ERROR):
            elapsed_time = time.time() - start_time
            if timeout is not None and elapsed_time >= timeout:
                job_result = {'job_id': job_id, 'status': 'ERROR',
                              'result': 'QISkit Time Out'}
                return Result(job_result)
            time.sleep(wait)
            logger.info('status = %s (%d seconds)', api_result['status'],
                        elapsed_time)
            api_result = self._api.get_job(job_id)

            if 'status' not in api_result:
                self._exception = QISKitError("get_job didn't return status: %s" %
                                              (pprint.pformat(api_result)))
                raise QISKitError("get_job didn't return status: %s" %
                                  (pprint.pformat(api_result)))
            if (api_result['status'] == 'ERROR_CREATING_JOB' or
                    api_result['status'] == 'ERROR_RUNNING_JOB'):
                job_result = {'job_id': job_id, 'status': 'ERROR',
                              'result': api_result['status']}
                return Result(job_result)

        if self.cancelled:
            job_result = {'job_id': job_id, 'status': 'CANCELLED',
                          'result': 'job cancelled'}
            return Result(job_result)
        elif self.exception:
            job_result = {'job_id': job_id, 'status': 'ERROR',
                          'result': str(self.exception)}
            return Result(job_result)
        api_result = self._api.get_job(job_id)
        job_result_list = []
        for circuit_result in api_result['qasms']:
            this_result = {'data': circuit_result['data'],
                           'name': circuit_result.get('name'),
                           'compiled_circuit_qasm': circuit_result.get('qasm'),
                           'status': circuit_result['status']}
            if 'metadata' in circuit_result:
                this_result['metadata'] = circuit_result['metadata']
            job_result_list.append(this_result)
        job_result = {'job_id': job_id,
                      'status': api_result['status'],
                      'used_credits': api_result.get('usedCredits'),
                      'result': job_result_list}
        # logger.info('Got a result for qobj: %s from remote backend %s with job id: %s',
        #             qobj["id"], qobj['config']['backend_name'],
        #             job_id)
        job_result['backend_name'] = self.backend_name
        return Result(job_result)


class IBMQJobError(QISKitError):
    """class for IBM Q Job errors"""
    pass


def _reorder_bits(result):
    """temporary fix for ibmq backends.
    for every ran circuit, get reordering information from qobj
    and apply reordering on result"""
    for circuit_result in result._result['result']:
        if 'metadata' in circuit_result:
            circ = circuit_result['metadata'].get('compiled_circuit')
        else:
            raise QISKitError('result object missing metadata for reordering bits')
        # device_qubit -> device_clbit (how it should have been)
        measure_dict = {op['qubits'][0]: op['clbits'][0]
                        for op in circ['operations']
                        if op['name'] == 'measure'}
        counts_dict_new = {}
        for item in circuit_result['data']['counts'].items():
            # fix clbit ordering to what it should have been
            bits = list(item[0])
            bits.reverse()  # lsb in 0th position
            count = item[1]
            reordered_bits = list('x' * len(bits))
            for device_clbit, bit in enumerate(bits):
                if device_clbit in measure_dict:
                    correct_device_clbit = measure_dict[device_clbit]
                    reordered_bits[correct_device_clbit] = bit
            reordered_bits.reverse()

            # only keep the clbits specified by circuit, not everything on device
            num_clbits = circ['header']['number_of_clbits']
            compact_key = reordered_bits[-num_clbits:]
            compact_key = "".join([b if b != 'x' else '0'
                                   for b in compact_key])

            # insert spaces to signify different classical registers
            cregs = circ['header']['clbit_labels']
            if sum([creg[1] for creg in cregs]) != num_clbits:
                raise ResultError("creg sizes don't add up in result header.")
            creg_begin_pos = []
            creg_end_pos = []
            acc = 0
            for creg in reversed(cregs):
                creg_size = creg[1]
                creg_begin_pos.append(acc)
                creg_end_pos.append(acc + creg_size)
                acc += creg_size
            compact_key = " ".join([compact_key[creg_begin_pos[i]:creg_end_pos[i]]
                                    for i in range(len(cregs))])

            # marginalize over unwanted measured qubits
            if compact_key not in counts_dict_new:
                counts_dict_new[compact_key] = count
            else:
                counts_dict_new[compact_key] += count

        circuit_result['data']['counts'] = counts_dict_new


def _numpy_type_converter(obj):
    if isinstance(obj, numpy.integer):
        return int(obj)
    elif isinstance(obj, numpy.floating):  # pylint: disable=no-member
        return float(obj)
    elif isinstance(obj, numpy.ndarray):
        return obj.tolist()
    return obj
