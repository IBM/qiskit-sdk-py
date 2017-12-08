# -*- coding: utf-8 -*-

# Copyright 2017 IBM RESEARCH. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =============================================================================
"""Processor for running Quantum Jobs in the different backends."""


from concurrent import futures
import logging
import pprint
from threading import Lock

import qiskit.backends
from qiskit.backends import (local_backends, remote_backends)
from qiskit._result import Result

from qiskit import QISKitError
from qiskit import _openquantumcompiler as openquantumcompiler


logger = logging.getLogger(__name__)


def run_backend(q_job, launch_callback=None):
    """Run a program of compiled quantum circuits on a backend.

    Args:
        q_job (QuantumJob): job object
        launch_callback (fn(string)): Function called at job launch. It will
                                      be passed the ID string of job, which
                                      will match the job_id in the result.

    Returns:
        Result: Result object.
    """
    backend_name = q_job.backend
    qobj = q_job.qobj
    if backend_name in local_backends():  # remove condition when api gets qobj
        for circuit in qobj['circuits']:
            if circuit['compiled_circuit'] is None:
                compiled_circuit = openquantumcompiler.compile(circuit['circuit'],
                                                               format='json')
                circuit['compiled_circuit'] = compiled_circuit
    backend = qiskit.backends.get_backend_instance(backend_name)
    return backend.run(q_job, launch_callback)


class JobProcessor():
    """
    Process a series of jobs and collect the results
    """
    def __init__(self, q_jobs, callback, max_workers=1, launch_callback=None):
        """
        Args:
            q_jobs (list(QuantumJob)): List of QuantumJob objects.
            callback (fn(results)): The function that will be called when all
                jobs finish. The signature of the function must be:
                fn(results)
                results: A list of Result objects.
            max_workers (int): The maximum number of workers to use.
            launch_callback (fn(string)): Function to be called at job launch.
                It will be passed the ID string of job, which will match the
                job_id in the result.

        Raises:
            QISKitError: if any of the job backends could not be found.
        """
        self.q_jobs = q_jobs
        self.max_workers = max_workers
        # check whether any jobs are remote
        self.online = any(qj.backend not in local_backends() for qj in q_jobs)
        self.futures = {}
        self.lock = Lock()
        # Set a default dummy callback just in case the user doesn't want
        # to pass any callback.
        self.callback = (lambda rs: ()) if callback is None else callback
        self.launch_callback = None
        self.num_jobs = len(self.q_jobs)
        self.jobs_results = []
        if self.online:
            # verify backends across all jobs
            for q_job in q_jobs:
                if q_job.backend not in remote_backends() + local_backends():
                    raise QISKitError("Backend %s not found!" % q_job.backend)
        if self.online:
            # I/O intensive -> use ThreadedPoolExecutor
            self.executor_class = futures.ThreadPoolExecutor
        else:
            # CPU intensive -> use ProcessPoolExecutor
            self.executor_class = futures.ProcessPoolExecutor

    def _job_done_callback(self, future):
        try:
            result = future.result()
        except Exception as ex:  # pylint: disable=broad-except
            result = Result({'job_id': '0', 'status': 'ERROR',
                             'result': ex},
                            future.qobj)
        with self.lock:
            self.futures[future]['result'] = result
            self.jobs_results.append(result)
            if self.num_jobs != 0:
                self.num_jobs -= 1
        # Call the callback when all jobs have finished
        if self.num_jobs == 0:
            logger.info(pprint.pformat(result))
            self.callback(self.jobs_results)

    def submit(self):
        """Process/submit jobs"""
        executor = self.executor_class(max_workers=self.max_workers)
        for q_job in self.q_jobs:
            future = executor.submit(run_backend, q_job, self.launch_callback)
            future.qobj = q_job.qobj
            self.futures[future] = q_job.qobj
            future.add_done_callback(self._job_done_callback)
