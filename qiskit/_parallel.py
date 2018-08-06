# -*- coding: utf-8 -*-

# Copyright 2018, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

# This file is part of QuTiP: Quantum Toolbox in Python.
#
#    Copyright (c) 2011 and later, Paul D. Nation and Robert J. Johansson.
#    All rights reserved.
#
#    Redistribution and use in source and binary forms, with or without
#    modification, are permitted provided that the following conditions are
#    met:
#
#    1. Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#
#    2. Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
#    3. Neither the name of the QuTiP: Quantum Toolbox in Python nor the names
#       of its contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.
#
#    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#    "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#    LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
#    PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
#    HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#    SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
#    LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#    DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#    THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#    (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#    OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
###############################################################################

"""Routines for running Python functions in parallel using process pools
from the multiprocessing library.
"""

import os
from multiprocessing import Pool, cpu_count
from qiskit.wrapper.receiver import receiver as rec
from qiskit.wrapper.progressbar import BaseProgressBar


def serial_map(task, values, task_args=tuple(), task_kwargs={},  # pylint: disable=W0102
               num_processes=1):                                 # pylint: disable=W0613
    """
    Serial mapping function with the same call signature as parallel_map, for
    easy switching between serial and parallel execution. This is functionally
    equivalent to:

        result = [task(value, *task_args, **task_kwargs) for value in values]

    This function work as a drop-in replacement for `parallel_map`.

    Parameters:
        task (func): The function that is to be called for each value in `task_vec`.
        values (array_like): The list or array of values for which the `task` function is
                            to be evaluated.
        task_args (list): Optional additional argument to the `task` function.
        task_kwargs (dict): Optional additional keyword argument to the `task` function.
        num_processes (int): Number of processes to spawn. (IGNORED FOR SERIAL MAP)

    Returns:
        result: The result list contains the value of `task(value, *task_args, **task_kwargs)`
            for each value in `values`.

    Raises:
        QISKitError: Invalid progress bar instance.
    """
    # Get last element of the receiver channels
    if any(rec.channels):
        last_idx = next(reversed(rec.channels))

        if rec.channels[last_idx].type == 'progressbar' and not rec.channels[last_idx].touched:
            progress_bar = rec.channels[last_idx]
        else:
            progress_bar = BaseProgressBar()
    else:
        progress_bar = BaseProgressBar()

    progress_bar.start(len(values))
    results = []
    for n, value in enumerate(values):
        progress_bar.update(n)
        result = task(value, *task_args, **task_kwargs)
        results.append(result)
    progress_bar.finished()

    return results


def parallel_map(task, values, task_args=tuple(), task_kwargs={},  # pylint: disable=W0102
                 num_processes=cpu_count()):
    """
    Parallel execution of a mapping of `values` to the function `task`. This
    is functionally equivalent to::
        result = [task(value, *task_args, **task_kwargs) for value in values]

    Parameters:
        task (func): Function that is to be called for each value in ``task_vec``.
        values (array_like): List or array of values for which the ``task``
                            function is to be evaluated.
        task_args (list): Optional additional arguments to the ``task`` function.
        task_kwargs (dict): Optional additional keyword argument to the ``task`` function.
        num_processes (int): Number of processes to spawn.

    Returns:
        result: The result list contains the value of
                ``task(value, *task_args, **task_kwargs)`` for
                    each value in ``values``.

    Raises:
        QISKitError: Invalid progress bar instance.

        KeyboardInterrupt: If user interupts via keyboard.
    """
    # Get last element of the receiver channels
    if any(rec.channels):
        last_idx = next(reversed(rec.channels))

        if rec.channels[last_idx].type == 'progressbar' and not rec.channels[last_idx].touched:
            progress_bar = rec.channels[last_idx]
        else:
            progress_bar = BaseProgressBar()
    else:
        progress_bar = BaseProgressBar()

    os.environ['QISKIT_IN_PARALLEL'] = 'TRUE'

    progress_bar.start(len(values))
    nfinished = [0]

    def _update_progress_bar(xvar):  # pylint: disable=W0613
        nfinished[0] += 1
        progress_bar.update(nfinished[0])

    try:
        pool = Pool(processes=num_processes)

        async_res = [pool.apply_async(task, (value,) + task_args, task_kwargs,
                                      _update_progress_bar) for value in values]

        while not all([item.ready() for item in async_res]):
            for item in async_res:
                item.wait(timeout=0.1)

        pool.terminate()
        pool.join()

    except KeyboardInterrupt as exept:
        os.environ['QISKIT_IN_PARALLEL'] = 'FALSE'
        pool.terminate()
        pool.join()
        raise exept

    progress_bar.finished()
    os.environ['QISKIT_IN_PARALLEL'] = 'FALSE'

    return [ar.get() for ar in async_res]
