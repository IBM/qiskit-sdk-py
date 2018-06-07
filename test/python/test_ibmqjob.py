# -*- coding: utf-8 -*-

# Copyright (c) 2017, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

# pylint: disable=invalid-name,missing-docstring,broad-except

"""IBMQJob Test."""

import unittest
import time
from concurrent import futures
import numpy
from scipy.stats import chi2_contingency

from qiskit import (ClassicalRegister, QuantumCircuit, QuantumRegister,
                    QuantumJob)
import qiskit._compiler
from qiskit.backends.ibmq import IBMQProvider
from qiskit.backends.ibmq.ibmqjob import IBMQJob, IBMQJobError
from qiskit.backends.basejob import JobStatus
from .common import requires_qe_access, QiskitTestCase, slow_test


def lowest_pending_jobs(backends):
    """Returns the backend with lowest pending jobs."""
    backends = filter(lambda x: x.status.get('available', False), backends)
    by_pending_jobs = sorted(backends,
                             key=lambda x: x.status['pending_jobs'])
    return by_pending_jobs[0]


class TestIBMQJob(QiskitTestCase):
    """
    Test ibmqjob module.
    """

    @classmethod
    @requires_qe_access
    def setUpClass(cls, QE_TOKEN, QE_URL, hub=None, group=None, project=None):
        # pylint: disable=arguments-differ
        super().setUpClass()
        # create QuantumCircuit
        qr = QuantumRegister(2, 'q')
        cr = ClassicalRegister(2, 'c')
        qc = QuantumCircuit(qr, cr)
        qc.h(qr[0])
        qc.cx(qr[0], qr[1])
        qc.measure(qr, cr)
        cls._qc = qc
        cls._provider = IBMQProvider(QE_TOKEN, QE_URL, hub, group, project)
        cls._using_hub = bool(hub and group and project)

    def test_run_simulator(self):
        backend = self._provider.get_backend('ibmq_qasm_simulator')
        qobj = qiskit._compiler.compile(self._qc, backend)
        shots = qobj['config']['shots']
        quantum_job = QuantumJob(qobj, backend, preformatted=True)
        job = backend.run(quantum_job)
        result = job.result()
        counts_qx = result.get_counts(result.get_names()[0])
        counts_ex = {'00': shots/2, '11': shots/2}
        states = counts_qx.keys() | counts_ex.keys()
        # contingency table
        ctable = numpy.array([[counts_qx.get(key, 0) for key in states],
                              [counts_ex.get(key, 0) for key in states]])
        self.log.info('states: %s', str(states))
        self.log.info('ctable: %s', str(ctable))
        contingency = chi2_contingency(ctable)
        self.log.info('chi2_contingency: %s', str(contingency))
        self.assertGreater(contingency[1], 0.01)

    @slow_test
    def test_run_device(self):
        backends = self._provider.available_backends({'simulator': False})
        self.log.info('devices: %s', [b.name for b in backends])
        backend = lowest_pending_jobs(backends)
        self.log.info('using backend: %s', backend.name)
        qobj = qiskit._compiler.compile(self._qc, backend)
        shots = qobj['config']['shots']
        quantum_job = QuantumJob(qobj, backend, preformatted=True)
        job = backend.run(quantum_job)
        while not (job.done or job.exception):
            self.log.info(job.status)
            time.sleep(4)
        if job.exception:
            raise job.exception
        self.log.info(job.status)
        result = job.result()
        counts_qx = result.get_counts(result.get_names()[0])
        counts_ex = {'00': shots/2, '11': shots/2}
        states = counts_qx.keys() | counts_ex.keys()
        # contingency table
        ctable = numpy.array([[counts_qx.get(key, 0) for key in states],
                              [counts_ex.get(key, 0) for key in states]])
        self.log.info('states: %s', str(states))
        self.log.info('ctable: %s', str(ctable))
        contingency = chi2_contingency(ctable)
        self.log.info('chi2_contingency: %s', str(contingency))
        self.assertDictAlmostEqual(counts_qx, counts_ex, shots*0.1)

    @slow_test
    def test_run_async_simulator(self):
        IBMQJob._executor = futures.ThreadPoolExecutor(max_workers=2)
        backend = self._provider.get_backend('ibmq_qasm_simulator')
        self.log.info('submitting to backend %s', backend.name)
        num_qubits = 16
        qr = QuantumRegister(num_qubits, 'qr')
        cr = ClassicalRegister(num_qubits, 'cr')
        qc = QuantumCircuit(qr, cr)
        for i in range(num_qubits-1):
            qc.cx(qr[i], qr[i+1])
        qc.measure(qr, cr)
        qobj = qiskit._compiler.compile([qc]*10, backend)
        quantum_job = QuantumJob(qobj, backend, preformatted=True)
        num_jobs = 5
        job_array = [backend.run(quantum_job) for _ in range(num_jobs)]
        found_async_jobs = False
        timeout = 30
        start_time = time.time()
        while not found_async_jobs:
            check = sum([job.running for job in job_array])
            if check >= 2:
                self.log.info('found %d simultaneous jobs', check)
                break
            if all([job.done for job in job_array]):
                # done too soon? don't generate error
                self.log.warning('all jobs completed before simultaneous jobs '
                                 'could be detected')
                break
            for job in job_array:
                self.log.info('%s %s %s %s', job.status['status'], job.running,
                              check, job.job_id)
            self.log.info('-'*20 + ' ' + str(time.time()-start_time))
            if time.time() - start_time > timeout:
                raise TimeoutError('failed to see multiple running jobs after '
                                   '{0} s'.format(timeout))
            time.sleep(0.2)

        result_array = [job.result() for job in job_array]
        self.log.info('got back all job results')
        # Ensure all jobs have finished.
        self.assertTrue(all([job.done for job in job_array]))
        self.assertTrue(all([result.get_status() == 'COMPLETED' for result in result_array]))

        # Ensure job ids are unique.
        job_ids = [job.job_id for job in job_array]
        self.assertEqual(sorted(job_ids), sorted(list(set(job_ids))))

    @slow_test
    def test_run_async_device(self):
        backends = self._provider.available_backends({'simulator': False})
        backend = lowest_pending_jobs(backends)
        self.log.info('submitting to backend %s', backend.name)
        num_qubits = 5
        qr = QuantumRegister(num_qubits, 'qr')
        cr = ClassicalRegister(num_qubits, 'cr')
        qc = QuantumCircuit(qr, cr)
        for i in range(num_qubits-1):
            qc.cx(qr[i], qr[i+1])
        qc.measure(qr, cr)
        qobj = qiskit._compiler.compile(qc, backend)
        quantum_job = QuantumJob(qobj, backend, preformatted=True)
        num_jobs = 3
        job_array = [backend.run(quantum_job) for _ in range(num_jobs)]
        time.sleep(3)  # give time for jobs to start (better way?)
        job_status = [job.status['status'] for job in job_array]
        num_init = sum([status == JobStatus.INITIALIZING for status in job_status])
        num_queued = sum([status == JobStatus.QUEUED for status in job_status])
        num_running = sum([status == JobStatus.RUNNING for status in job_status])
        num_done = sum([status == JobStatus.DONE for status in job_status])
        num_error = sum([status == JobStatus.ERROR for status in job_status])
        self.log.info('number of currently initializing jobs: %d/%d',
                      num_init, num_jobs)
        self.log.info('number of currently queued jobs: %d/%d',
                      num_queued, num_jobs)
        self.log.info('number of currently running jobs: %d/%d',
                      num_running, num_jobs)
        self.log.info('number of currently done jobs: %d/%d',
                      num_done, num_jobs)
        self.log.info('number of errored jobs: %d/%d',
                      num_error, num_jobs)
        self.assertTrue(num_jobs - num_error - num_done > 0)

        # Wait for all the results.
        result_array = [job.result() for job in job_array]

        # Ensure all jobs have finished.
        self.assertTrue(all([job.done for job in job_array]))
        self.assertTrue(all([result.get_status() == 'COMPLETED' for result in result_array]))

        # Ensure job ids are unique.
        job_ids = [job.job_id for job in job_array]
        self.assertEqual(sorted(job_ids), sorted(list(set(job_ids))))

    def test_cancel(self):
        if not self._using_hub:
            self.skipTest('job cancellation currently only available on hubs')
        backends = self._provider.available_backends({'simulator': False})
        self.log.info('devices: %s', [b.name for b in backends])
        backend = backends[0]
        self.log.info('using backend: %s', backend.name)
        num_qubits = 5
        qr = QuantumRegister(num_qubits, 'qr')
        cr = ClassicalRegister(num_qubits, 'cr')
        qc = QuantumCircuit(qr, cr)
        for i in range(num_qubits-1):
            qc.cx(qr[i], qr[i+1])
        qc.measure(qr, cr)
        qobj = qiskit._compiler.compile(qc, backend)
        quantum_job = QuantumJob(qobj, backend, preformatted=True)
        num_jobs = 3
        job_array = [backend.run(quantum_job) for _ in range(num_jobs)]
        success = False
        self.log.info('jobs submitted: %s', num_jobs)
        while any([job.status['status'] == JobStatus.INITIALIZING for job in job_array]):
            self.log.info('jobs initializing')
            time.sleep(1)
        for job in job_array:
            job.cancel()
        while not success:
            job_status = [job.status for job in job_array]
            for status in job_status:
                self.log.info(status)
            if any([status['status'] == JobStatus.CANCELLED for status in job_status]):
                success = True
            if all([status['status'] == JobStatus.DONE for status in job_status]):
                raise IBMQJobError('all jobs completed before any could be cancelled')
            self.log.info('-' * 20)
            time.sleep(2)
        self.assertTrue(success)

    def test_job_id(self):
        backend = self._provider.get_backend('ibmq_qasm_simulator')
        qobj = qiskit._compiler.compile(self._qc, backend)
        quantum_job = QuantumJob(qobj, backend, preformatted=True)
        job = backend.run(quantum_job)
        while job.status['status'] == JobStatus.INITIALIZING:
            time.sleep(0.1)
        self.log.info('job_id: %s', job.job_id)
        self.assertTrue(job.job_id is not None)

    def test_get_backend_name(self):
        backend_name = 'ibmq_qasm_simulator'
        backend = self._provider.get_backend(backend_name)
        qobj = qiskit._compiler.compile(self._qc, backend)
        quantum_job = QuantumJob(qobj, backend, preformatted=True)
        job = backend.run(quantum_job)
        self.assertTrue(job.backend_name == backend_name)


if __name__ == '__main__':
    unittest.main(verbosity=2)
