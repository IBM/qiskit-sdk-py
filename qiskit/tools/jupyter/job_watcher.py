# -*- coding: utf-8 -*-

# This code is part of Qiskit.
#
# (C) Copyright IBM 2017, 2018.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""A module for the job watcher"""

from qiskit.tools.events.pubsub import Subscriber
from .job_widgets import (build_job_viewer, make_clear_button,
                          make_labels, create_job_widget)
from .watcher_monitor import _job_monitor


class JobWatcher(Subscriber):
    """An abstract progress bar with some shared functionality.
    """
    def __init__(self):
        super().__init__()
        self.jobs = []
        self._init_subscriber()
        self.job_viewer = build_job_viewer()
        self._clear_button = make_clear_button(self)
        self._labels = make_labels()
        self.refresh_viewer()

    def refresh_viewer(self):
        """Refreshes the job viewer.
        """
        if self.job_viewer is not None:
            self.job_viewer.children[0].children = [self._clear_button,
                                                    self._labels] + list(reversed(self.jobs))

    def stop_viewer(self):
        """Stops the job viewer.
        """
        self.job_viewer.close()
        self.job_viewer = None

    def start_viewer(self):
        """Starts the job viewer
        """
        self.job_viewer = build_job_viewer()
        self.refresh_viewer()

    def update_single_job(self, update_info):
        """Update a single job instance

        Args:
            update_info (tuple): Updated job info.
        """
        job_id = update_info[0]
        found_job = False
        ind = None
        for idx, job in enumerate(self.jobs):
            if job.job_id == job_id:
                found_job = True
                ind = idx
                break
        if found_job:
            job_wid = self.jobs[ind]
            # update status
            if update_info[1] == 'DONE':
                stat = "<font style='color:#34BC6E'>{}</font>".format(update_info[1])
            elif update_info[1] == 'ERROR':
                stat = "<font style='color:#DC267F'>{}</font>".format(update_info[1])
            elif update_info[1] == 'CANCELLED':
                stat = "<font style='color:#FFB000'>{}</font>".format(update_info[1])
            else:
                stat = update_info[1]
            job_wid.children[3].value = stat
            # update queue
            if update_info[2] == 0:
                queue = '-'
            else:
                queue = str(update_info[2])
            job_wid.children[4].value = queue
            # update msg
            job_wid.children[5].value = update_info[3]

    def remove_job(self, job_id):
        """Removes a job from the watcher

        Args:
            job_id (str): Job id to remove.

        Raises:
            Exception: Job id not found.
        """
        do_pop = False
        ind = None
        for idx, job in enumerate(self.jobs):
            if job.job_id == job_id:
                do_pop = True
                ind = idx
                break
        if not do_pop:
            raise Exception('job_id not found')
        self.jobs.pop(ind)
        self.refresh_viewer()

    def clear_done(self):
        """Clears the done jobs from the list.
        """
        _temp_jobs = []
        do_refresh = False
        for job in self.jobs:
            job_str = job.children[3].value
            if not (('DONE' in job_str) or ('CANCELLED' in job_str) or ('ERROR' in job_str)):
                _temp_jobs.append(job)
            else:
                do_refresh = True
        if do_refresh:
            self.jobs = _temp_jobs
            self.refresh_viewer()

    def _init_subscriber(self):

        def _add_job(job):
            status = job.status()
            job_widget = create_job_widget(self, job.job_id(),
                                           job.backend(),
                                           status.name,
                                           job.queue_position(),
                                           status.value)
            self.jobs.append(job_widget)
            self.refresh_viewer()
            _job_monitor(job, status, self)

        self.subscribe("ibmq.job.start", _add_job)
