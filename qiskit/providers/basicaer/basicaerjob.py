# This code is part of Qiskit.
#
# (C) Copyright IBM 2017.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

# pylint: disable=abstract-method


"""This module implements the job class used by Basic Aer Provider."""

from qiskit.providers import JobStatus
from qiskit.providers.job import JobV1


class BasicAerJob(JobV1):
    """BasicAerJob class.

    Attributes:
        _executor (futures.Executor): executor to handle asynchronous jobs
    """

    _async = False

    def __init__(self, backend, job_id, result):
        super().__init__(backend, job_id)
        self._result = result

    def submit(self):
        """Submit the job to the backend for execution.

        Raises:
            JobError: if trying to re-submit the job.
        """
        return

    def result(self):
        # pylint: disable=arguments-differ
        """Get job result .

        Returns:
            qiskit.Result: Result object

        Raises:
            concurrent.futures.TimeoutError: if timeout occurred.
            concurrent.futures.CancelledError: if job cancelled before completed.
        """
        return self._result

    def status(self):
        """Gets the status of the job by querying the Python's future

        Returns:
            qiskit.providers.JobStatus: The current JobStatus
        """
        return JobStatus.DONE

    def backend(self):
        """Return the instance of the backend used for this job."""
        return self._backend
