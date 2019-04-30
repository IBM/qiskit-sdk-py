# -*- coding: utf-8 -*-

# Copyright 2019, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

# pylint: disable=missing-return-doc,cyclic-import

"""
Schedule.
"""
import itertools
import logging
from typing import List, Tuple, Iterable, Union, Callable

from qiskit.pulse import ops
from .channels import Channel
from .interfaces import ScheduleComponent
from .timeslots import TimeslotCollection
from .exceptions import PulseError

logger = logging.getLogger(__name__)


class Schedule(ScheduleComponent):
    """Schedule of `ScheduleComponent`s. The composite node of a schedule tree."""
    # pylint: disable=missing-type-doc
    def __init__(self, *schedules: List[Union[ScheduleComponent, Tuple[int, ScheduleComponent]]],
                 name: str = None):
        """Create empty schedule.

        Args:
            *schedules: Child Schedules of this parent Schedule. May either be passed as
                the list of schedules, or a list of (start_time, schedule) pairs
            name: Name of this schedule

        Raises:
            PulseError: If timeslots intercept.
        """
        self._name = name
        try:
            timeslots = []
            children = []
            for sched_pair in schedules:
                # recreate as sequence starting at 0.
                if not isinstance(sched_pair, (list, tuple)):
                    sched_pair = (0, sched_pair)
                # convert to tuple
                sched_pair = tuple(sched_pair)
                insert_time, sched = sched_pair
                sched_timeslots = sched.timeslots
                if insert_time:
                    sched_timeslots = sched_timeslots.shift(insert_time)
                timeslots.append(sched_timeslots.timeslots)
                children.append(sched_pair)

            self._timeslots = TimeslotCollection(*itertools.chain(*timeslots))
            self._children = tuple(children)

        except PulseError as ts_err:
            raise PulseError('Child schedules {0} overlap.'.format(schedules)) from ts_err

    # pylint: enable=missing-type-doc

    @property
    def name(self) -> str:
        return self._name

    @property
    def timeslots(self) -> TimeslotCollection:
        return self._timeslots

    @property
    def duration(self) -> int:
        return self.timeslots.duration

    @property
    def start_time(self) -> int:
        return self.timeslots.start_time

    @property
    def stop_time(self) -> int:
        return self.timeslots.stop_time

    @property
    def channels(self) -> Tuple[Channel]:
        """Returns channels that this schedule uses."""
        return self.timeslots.channels

    @property
    def children(self) -> Tuple[ScheduleComponent]:
        return self._children

    @property
    def instructions(self) -> Tuple[Tuple[int, 'Instruction']]:
        """Iterable for getting instructions from Schedule tree."""
        return tuple(self._instructions())

    def ch_duration(self, *channels: List[Channel]) -> int:
        """Return duration of supplied channels.

        Args:
            *channels: Supplied channels
        """
        return self.timeslots.ch_duration(*channels)

    def ch_start_time(self, *channels: List[Channel]) -> int:
        """Return minimum start time for supplied channels.

        Args:
            *channels: Supplied channels
        """
        return self.timeslots.ch_start_time(*channels)

    def ch_stop_time(self, *channels: List[Channel]) -> int:
        """Return maximum start time for supplied channels.

        Args:
            *channels: Supplied channels
        """
        return self.timeslots.ch_stop_time(*channels)

    def _instructions(self, time: int = 0) -> Iterable[Tuple[int, 'Instruction']]:
        """Iterable for flattening Schedule tree.

        Args:
            time: Shifted time due to parent

        Yields:
            Tuple[int, ScheduleComponent]: Tuple containing time `ScheduleComponent` starts
                at and the flattened `ScheduleComponent`.
        """
        for insert_time, child_sched in self.children:
            yield from child_sched._instructions(time + insert_time)

    def union(self, *schedules: List[ScheduleComponent]) -> 'Schedule':
        """Return a new schedule which is the union of `self` and `schedule`.

        Args:
            *schedules: Schedules to be take the union with the parent `Schedule`.
        """
        return ops.union(self, *schedules)

    def shift(self: ScheduleComponent, time: int) -> 'Schedule':
        """Return a new schedule shifted forward by `time`.

        Args:
            time: Time to shift by
        """
        return ops.shift(self, time)

    def insert(self, start_time: int, schedule: ScheduleComponent) -> 'Schedule':
        """Return a new schedule with `schedule` inserted within `self` at `start_time`.

        Args:
            start_time: time to be inserted
            schedule: schedule to be inserted
        """
        return ops.insert(self, start_time, schedule)

    def append(self, schedule: ScheduleComponent) -> 'Schedule':
        """Return a new schedule with `schedule` inserted at the maximum time over
        all channels shared between `self` and `schedule`.

        Args:
            schedule: schedule to be appended
        """
        return ops.append(self, schedule)

    def flatten(self) -> 'ScheduleComponent':
        """Return a new schedule which is the flattened schedule contained all `instructions`."""
        return ops.flatten(self)

    def draw(self, dt: float = 1, style=None,
             filename: str = None, interp_method: Callable = None, scaling: float = None,
             channels_to_plot: List[Channel] = None, plot_all: bool = False,
             plot_range: Tuple[float] = None, interactive: bool = False,
             table: bool = True, label: bool = False,
             framechange: bool = True):
        """Plot the schedule.

        Args:
            dt: Time interval of samples.
            style (OPStyleSched): A style sheet to configure plot appearance.
            filename: Name required to save pulse image.
            interp_method: A function for interpolation.
            scaling: scaling of waveform amplitude.
            channels_to_plot: A list of channel names to plot.
            plot_all: Plot empty channels.
            plot_range: A tuple of time range to plot.
            interactive: When set true show the circuit in a new window
                (this depends on the matplotlib backend being used supporting this).
            table: Draw event table for supported commands
            label: Label individual instructions
            framechange: Add framechange indicators

        Returns:
            matplotlib.figure: A matplotlib figure object of the pulse schedule.
        """
        # pylint: disable=invalid-name, cyclic-import

        from qiskit.tools import visualization

        return visualization.pulse_drawer(self, dt=dt, style=style,
                                          filename=filename, interp_method=interp_method,
                                          scaling=scaling, channels_to_plot=channels_to_plot,
                                          plot_all=plot_all, plot_range=plot_range,
                                          interactive=interactive, table=table,
                                          label=label, framechange=framechange)

    def __add__(self, schedule: ScheduleComponent) -> 'Schedule':
        """Return a new schedule with `schedule` inserted within `self` at `start_time`."""
        return self.append(schedule)

    def __or__(self, schedule: ScheduleComponent) -> 'Schedule':
        """Return a new schedule which is the union of `self` and `schedule`."""
        return self.union(schedule)

    def __lshift__(self, time: int) -> 'Schedule':
        """Return a new schedule which is shifted forward by `time`."""
        return self.shift(time)

    def __repr__(self):
        res = 'Schedule("name=%s", ' % self._name if self._name else 'Schedule('
        res += '%d, ' % self.start_time
        instructions = [repr(instr) for instr in self.instructions]
        res += ', '.join([str(i) for i in instructions[:50]])
        if len(instructions) > 50:
            return res + ', ...)'
        return res + ')'
