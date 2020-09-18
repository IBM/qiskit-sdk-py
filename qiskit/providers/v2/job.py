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

"""This module implements the abstract base class for backend jobs.

When creating a new backend module it is also necessary to implement this
job interface.
"""

from abc import ABC, abstractmethod
from typing import Callable, Optional
import time

from qiskit.providers.jobstatus import JobStatus, JOB_FINAL_STATES
from qiskit.providers.exceptions import JobTimeoutError
from qiskit.providers.v2.backend import Backend


class Job:
    pass


class JobV1(Job, ABC):
    """Class to handle jobs

    This first version of the Backend abstract class is written to be mostly
    backwards compatible with the v1 providers interface. This was done to ease
    the transition for users and provider maintainers from v1 to v2. Expect,
    future versions of this abstract class to change the data model and
    interface.
    """
    _async = True

    def __init__(self, backend: Backend, job_id: str, **kwargs) -> None:
        """Initializes the asynchronous job.

        Args:
            backend: the backend used to run the job.
            job_id: a unique id in the context of the backend used to run
                the job.
        """
        self._job_id = job_id
        self._backend = backend
        self.metadata = kwargs

    def job_id(self) -> str:
        """Return a unique id identifying the job."""
        return self._job_id

    def backend(self) -> Backend:
        """Return the backend where this job was executed."""
        return self._backend

    def done(self) -> bool:
        """Return whether the job has successfully run."""
        return self.status() == JobStatus.DONE

    def running(self) -> bool:
        """Return whether the job is actively running."""
        return self.status() == JobStatus.RUNNING

    def cancelled(self) -> bool:
        """Return whether the job has been cancelled."""
        return self.status() == JobStatus.CANCELLED

    def in_final_state(self) -> bool:
        """Return whether the job is in a final job state."""
        return self.status() in JOB_FINAL_STATES

    def wait_for_final_state(
            self,
            timeout: Optional[float] = None,
            wait: float = 5,
            callback: Optional[Callable] = None
    ) -> None:
        """Poll the job status until it progresses to a final state such as ``DONE`` or ``ERROR``.

        Args:
            timeout: Seconds to wait for the job. If ``None``, wait indefinitely.
            wait: Seconds between queries.
            callback: Callback function invoked after each query.
                The following positional arguments are provided to the callback function:

                * job_id: Job ID
                * job_status: Status of the job from the last query
                * job: This BaseJob instance

                Note: different subclass might provide different arguments to
                the callback function.

        Raises:
            JobTimeoutError: If the job does not reach a final state before the
                specified timeout.
        """
        if not self._async:
            return
        start_time = time.time()
        status = self.status()
        while status not in JOB_FINAL_STATES:
            elapsed_time = time.time() - start_time
            if timeout is not None and elapsed_time >= timeout:
                raise JobTimeoutError(
                    'Timeout while waiting for job {}.'.format(self.job_id()))
            if callback:
                callback(self.job_id(), status, self)
            time.sleep(wait)
            status = self.status()
        return

    @abstractmethod
    def submit(self):
        """Submit the job to the backend for execution."""
        pass

    @abstractmethod
    def result(self):
        """Return the results of the job."""
        pass

    def cancel(self):
        """Attempt to cancel the job."""
        raise NotImplementedError

    @abstractmethod
    def status(self):
        """Return the status of the job, among the values of ``JobStatus``."""
        pass
