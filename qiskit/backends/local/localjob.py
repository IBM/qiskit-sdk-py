# -*- coding: utf-8 -*-

# Copyright 2017, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""This module implements the job class used for LocalBackend objects."""

from concurrent import futures
import logging
import sys
import functools

from qiskit.backends import BaseJob, JobStatus, JobError

logger = logging.getLogger(__name__)


def requires_submit(func):
    """
    Decorator to ensure that a submit has been performed before
    calling the method.

    Args:
        func (callable): test function to be decorated.

    Returns:
        callable: the decorated function.
    """
    @functools.wraps(func)
    def _(self, *args, **kwargs):
        if self._future is None:
            raise JobError("Job not submitted yet!. You have to .submit() first!")
        return func(self, *args, **kwargs)
    return _


class LocalJob(BaseJob):
    """Local QISKit SDK Job class.

    Attributes:
        _executor (futures.Executor): executor to handle asynchronous jobs
    """

    if sys.platform in ['darwin', 'win32']:
        _executor = futures.ThreadPoolExecutor()
    else:
        _executor = futures.ProcessPoolExecutor()

    def __init__(self, fn, qobj):
        super().__init__()
        self._fn = fn
        self._qobj = qobj
        self._backend_name = qobj.header.backend_name
        self._future = None

    def submit(self):
        """ Submit the job to the backend for running """
        if self._future is not None:
            raise JobError("We have already submitted the job!")

        self._future = self._executor.submit(self._fn, self._qobj)

    @requires_submit
    def result(self, timeout=None):
        # pylint: disable=arguments-differ
        """
        Get job result. The behavior is the same as the underlying
        concurrent Future objects,

        https://docs.python.org/3/library/concurrent.futures.html#future-objects

        Args:
            timeout (float): number of seconds to wait for results.

        Returns:
            Result: Result object

        Raises:
            concurrent.futures.TimeoutError: if timeout occured.
            concurrent.futures.CancelledError: if job cancelled before completed.
        """
        return self._future.result(timeout=timeout)

    @requires_submit
    def cancel(self):
        return self._future.cancel()

    @property
    def status(self):
        _status_msg = None
        # order is important here
        if self.running:
            _status = JobStatus.RUNNING
        elif not self.done:
            _status = JobStatus.QUEUED
        elif self.cancelled:
            _status = JobStatus.CANCELLED
        elif self.done:
            _status = JobStatus.DONE
        else:
            raise JobError('Unexpected behavior of {0}'.format(
                self.__class__.__name__))
        return {'status': _status,
                'status_msg': _status_msg}

    @property
    @requires_submit
    def running(self):
        return self._future.running()

    @property
    @requires_submit
    def done(self):
        """
        Returns True if job successfully finished running.

        Note behavior is slightly different than Future objects which would
        also return true if successfully cancelled.
        """
        return self._future.done() and not self._future.cancelled()

    @property
    @requires_submit
    def cancelled(self):
        return self._future.cancelled()

    @property
    def backend_name(self):
        """
        Return backend name used for this job
        """
        return self._backend_name
