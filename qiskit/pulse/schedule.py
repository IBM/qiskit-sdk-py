# This code is part of Qiskit.
#
# (C) Copyright IBM 2019.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""The Schedule is one of the most fundamental objects to this pulse-level programming module.
A ``Schedule`` is a representation of a *program* in Pulse. Each schedule tracks the time of each
instruction occuring in parallel over multiple signal *channels*.
"""

import abc
import copy
import itertools
import multiprocessing as mp
import sys
from typing import List, Tuple, Iterable, Union, Dict, Callable, Set, Optional

from qiskit.util import is_main_process
from qiskit.pulse.channels import Channel
from qiskit.pulse.interfaces import ScheduleComponent
from qiskit.pulse.exceptions import PulseError

# pylint: disable=missing-return-doc

Interval = Tuple[int, int]
"""An interval type is a tuple of a start time (inclusive) and an end time (exclusive)."""


class Schedule(ScheduleComponent):
    """A quantum program *schedule* with exact time constraints for its instructions, operating
    over all input signal *channels* and supporting special syntaxes for building.
    """

    # Counter for the number of instances in this class.
    instances_counter = itertools.count()
    # Prefix to use for auto naming.
    prefix = 'sched'

    def __init__(self, *schedules: List[Union[ScheduleComponent, Tuple[int, ScheduleComponent]]],
                 name: Optional[str] = None):
        """Create an empty schedule.

        Args:
            *schedules: Child Schedules of this parent Schedule. May either be passed as
                        the list of schedules, or a list of ``(start_time, schedule)`` pairs.
            name: Name of this schedule. Defaults to an autogenerated string if not provided.
        """
        if name is None:
            name = self.prefix + str(next(self.instances_counter))
            if sys.platform != "win32" and not is_main_process():
                name += '-{}'.format(mp.current_process().pid)

        self._name = name
        self._duration = 0

        self._timeslots = {}
        self.__children = []

        for sched_pair in schedules:
            try:
                time, sched = sched_pair
            except TypeError:
                # recreate as sequence starting at 0.
                time, sched = 0, sched_pair
            self._mutable_insert(time, sched)

    @property
    def name(self) -> str:
        return self._name

    @property
    def timeslots(self) -> Dict[Channel, List[Interval]]:
        """Time keeping attribute."""
        return self._timeslots

    @property
    def duration(self) -> int:
        return self._duration

    @property
    def start_time(self) -> int:
        return self.ch_start_time(*self.channels)

    @property
    def stop_time(self) -> int:
        return self.duration

    @property
    def channels(self) -> Tuple[Channel]:
        """Returns channels that this schedule uses."""
        return tuple(self._timeslots.keys())

    @property
    def _children(self) -> Tuple[Tuple[int, ScheduleComponent], ...]:
        """Return the child``ScheduleComponent``s of this ``Schedule`` in the
        order they were added to the schedule.

        Returns:
            A tuple, where each element is a two-tuple containing the initial
            scheduled time of each ``ScheduleComponent`` and the component
            itself.
        """
        return tuple(self.__children)

    @property
    def instructions(self):
        """Get the time-ordered instructions from self.

        ReturnType:
            Tuple[Tuple[int, Instruction], ...]
        """

        def key(time_inst_pair):
            inst = time_inst_pair[1]
            return (time_inst_pair[0], inst.duration,
                    sorted(chan.name for chan in inst.channels))

        return tuple(sorted(self._instructions(), key=key))

    def ch_duration(self, *channels: List[Channel]) -> int:
        """Return the time of the end of the last instruction over the supplied channels.

        Args:
            *channels: Channels within ``self`` to include.
        """
        return self.ch_stop_time(*channels)

    def ch_start_time(self, *channels: List[Channel]) -> int:
        """Return the time of the start of the first instruction over the supplied channels.

        Args:
            *channels: Channels within ``self`` to include.
        """
        try:
            chan_intervals = (self._timeslots[chan] for chan in channels if chan in self._timeslots)
            return min(intervals[0][0] for intervals in chan_intervals)
        except ValueError:
            # If there are no instructions over channels
            return 0

    def ch_stop_time(self, *channels: List[Channel]) -> int:
        """Return maximum start time over supplied channels.

        Args:
            *channels: Channels within ``self`` to include.
        """
        try:
            chan_intervals = (self._timeslots[chan] for chan in channels if chan in self._timeslots)
            return max(intervals[-1][1] for intervals in chan_intervals)
        except ValueError:
            # If there are no instructions over channels
            return 0

    def _instructions(self, time: int = 0):
        """Iterable for flattening Schedule tree.

        Args:
            time: Shifted time due to parent.

        Yields:
            Iterable[Tuple[int, Instruction]]: Tuple containing the time each
                :class:`~qiskit.pulse.Instruction`
                starts at and the flattened :class:`~qiskit.pulse.Instruction` s.
        """
        for insert_time, child_sched in self._children:
            yield from child_sched._instructions(time + insert_time)

    # pylint: disable=arguments-differ
    def shift(self,
              time: int,
              name: Optional[str] = None,
              inplace: bool = False
              ) -> 'Schedule':
        """Return a schedule shifted forward by ``time``.

        Args:
            time: Time to shift by.
            name: Name of the new schedule. Defaults to the name of self.
            inplace: Perform operation inplace on this schedule. Otherwise
                return a new ``Schedule``.
        """
        if inplace:
            return self._mutable_shift(time)
        return self._immutable_shift(time, name=name)

    def _immutable_shift(self,
                         time: int,
                         name: Optional[str] = None
                         ) -> 'Schedule':
        """Return a new schedule shifted forward by `time`.

        Args:
            time: Time to shift by
            name: Name of the new schedule if call was mutable. Defaults to name of self
        """
        if name is None:
            name = self.name
        return Schedule((time, self), name=name)

    def _mutable_shift(self,
                       time: int
                       ) -> 'Schedule':
        """Return this schedule shifted forward by `time`.

        Args:
            time: Time to shift by

        Raises:
            PulseError: if ``time`` is not an integer.
        """
        if not isinstance(time, int):
            raise PulseError(
                "Schedule start time must be an integer.")

        timeslots = {}
        for chan, ch_timeslots in self._timeslots.items():
            timeslots[chan] = [(ts[0] + time, ts[1] + time) for
                               ts in ch_timeslots]

        _check_nonnegative_timeslot(timeslots)

        self._duration = self._duration + time
        self._timeslots = timeslots
        self.__children = [(orig_time + time, child) for
                           orig_time, child in self._children]
        return self

    # pylint: disable=arguments-differ
    def insert(self,
               start_time: int,
               schedule: ScheduleComponent,
               name: Optional[str] = None,
               inplace: bool = False
               ) -> 'Schedule':
        """Return a new schedule with ``schedule`` inserted into ``self`` at ``start_time``.

        Args:
            start_time: Time to insert the schedule.
            schedule: Schedule to insert.
            name: Name of the new schedule. Defaults to the name of self.
            inplace: Perform operation inplace on this schedule. Otherwise
                return a new ``Schedule``.
        """
        if inplace:
            return self._mutable_insert(start_time, schedule)
        return self._immutable_insert(start_time, schedule, name=name)

    def _mutable_insert(self,
                        start_time: int,
                        schedule: ScheduleComponent
                        ) -> 'Schedule':
        """Mutably insert `schedule` into `self` at `start_time`.

        Args:
            start_time: Time to insert the second schedule.
            schedule: Schedule to mutably insert.
        """
        self._add_timeslots(start_time, schedule)
        self.__children.append((start_time, schedule))
        return self

    def _immutable_insert(self,
                          start_time: int,
                          schedule: ScheduleComponent,
                          name: Optional[str] = None,
                          ) -> 'Schedule':
        """Return a new schedule with ``schedule`` inserted into ``self`` at ``start_time``.

        Args:
            start_time: Time to insert the schedule.
            schedule: Schedule to insert.
            name: Name of the new ``Schedule``. Defaults to name of ``self``.
        """
        if name is None:
            name = self.name
        new_sched = Schedule(name=name)
        new_sched._mutable_insert(0, self)
        new_sched._mutable_insert(start_time, schedule)
        return new_sched

    # pylint: disable=arguments-differ
    def append(self, schedule: ScheduleComponent,
               name: Optional[str] = None,
               inplace: bool = False) -> 'Schedule':
        r"""Return a new schedule with ``schedule`` inserted at the maximum time over
        all channels shared between ``self`` and ``schedule``.

        .. math::

            t = \textrm{max}(\texttt{x.stop_time} |\texttt{x} \in
                \texttt{self.channels} \cap \texttt{schedule.channels})

        Args:
            schedule: Schedule to be appended.
            name: Name of the new ``Schedule``. Defaults to name of ``self``.
            inplace: Perform operation inplace on this schedule. Otherwise
                return a new ``Schedule``.
        """
        common_channels = set(self.channels) & set(schedule.channels)
        time = self.ch_stop_time(*common_channels)
        return self.insert(time, schedule, name=name, inplace=inplace)

    def flatten(self) -> 'Schedule':
        """Return a new schedule which is the flattened schedule contained all ``instructions``."""
        return Schedule(*self.instructions, name=self.name)

    def filter(self, *filter_funcs: List[Callable],
               channels: Optional[Iterable[Channel]] = None,
               instruction_types=None,
               time_ranges: Optional[Iterable[Tuple[int, int]]] = None,
               intervals: Optional[Iterable[Interval]] = None) -> 'Schedule':
        """Return a new ``Schedule`` with only the instructions from this ``Schedule`` which pass
        though the provided filters; i.e. an instruction will be retained iff every function in
        ``filter_funcs`` returns ``True``, the instruction occurs on a channel type contained in
        ``channels``, the instruction type is contained in ``instruction_types``, and the period
        over which the instruction operates is *fully* contained in one specified in
        ``time_ranges`` or ``intervals``.

        If no arguments are provided, ``self`` is returned.

        Args:
            filter_funcs: A list of Callables which take a (int, ScheduleComponent) tuple and
                          return a bool.
            channels: For example, ``[DriveChannel(0), AcquireChannel(0)]``.
            instruction_types (Optional[Iterable[Type[qiskit.pulse.Instruction]]]): For example,
                ``[PulseInstruction, AcquireInstruction]``.
            time_ranges: For example, ``[(0, 5), (6, 10)]``.
            intervals: For example, ``[(0, 5), (6, 10)]``.
        """
        composed_filter = self._construct_filter(*filter_funcs,
                                                 channels=channels,
                                                 instruction_types=instruction_types,
                                                 time_ranges=time_ranges,
                                                 intervals=intervals)
        return self._apply_filter(composed_filter,
                                  new_sched_name="{name}".format(name=self.name))

    def exclude(self, *filter_funcs: List[Callable],
                channels: Optional[Iterable[Channel]] = None,
                instruction_types=None,
                time_ranges: Optional[Iterable[Tuple[int, int]]] = None,
                intervals: Optional[Iterable[Interval]] = None) -> 'Schedule':
        """Return a Schedule with only the instructions from this Schedule *failing* at least one
        of the provided filters. This method is the complement of ``self.filter``, so that::

            self.filter(args) | self.exclude(args) == self

        Args:
            filter_funcs: A list of Callables which take a (int, ScheduleComponent) tuple and
                          return a bool.
            channels: For example, ``[DriveChannel(0), AcquireChannel(0)]``.
            instruction_types (Optional[Iterable[Type[qiskit.pulse.Instruction]]]): For example,
                ``[PulseInstruction, AcquireInstruction]``.
            time_ranges: For example, ``[(0, 5), (6, 10)]``.
            intervals: For example, ``[(0, 5), (6, 10)]``.
        """
        composed_filter = self._construct_filter(*filter_funcs,
                                                 channels=channels,
                                                 instruction_types=instruction_types,
                                                 time_ranges=time_ranges,
                                                 intervals=intervals)
        return self._apply_filter(lambda x: not composed_filter(x),
                                  new_sched_name="{name}".format(name=self.name))

    def _apply_filter(self, filter_func: Callable, new_sched_name: str) -> 'Schedule':
        """Return a Schedule containing only the instructions from this Schedule for which
        ``filter_func`` returns ``True``.

        Args:
            filter_func: Function of the form (int, ScheduleComponent) -> bool.
            new_sched_name: Name of the returned ``Schedule``.
        """
        subschedules = self.flatten()._children
        valid_subschedules = [sched for sched in subschedules if filter_func(sched)]
        return Schedule(*valid_subschedules, name=new_sched_name)

    def _construct_filter(self, *filter_funcs: List[Callable],
                          channels: Optional[Iterable[Channel]] = None,
                          instruction_types=None,
                          time_ranges: Optional[Iterable[Tuple[int, int]]] = None,
                          intervals: Optional[Iterable[Interval]] = None) -> Callable:
        """Returns a boolean-valued function with input type ``(int, ScheduleComponent)`` that
        returns ``True`` iff the input satisfies all of the criteria specified by the arguments;
        i.e. iff every function in ``filter_funcs`` returns ``True``, the instruction occurs on a
        channel type contained in ``channels``, the instruction type is contained in
        ``instruction_types``, and the period over which the instruction operates is fully
        contained in one specified in ``time_ranges`` or ``intervals``.

        Args:
            filter_funcs: A list of Callables which take a (int, ScheduleComponent) tuple and
                          return a bool.
            channels: For example, ``[DriveChannel(0), AcquireChannel(0)]``.
            instruction_types (Optional[Iterable[Type[Instruction]]]): For example,
                ``[PulseInstruction, AcquireInstruction]``.
            time_ranges: For example, ``[(0, 5), (6, 10)]``.
            intervals: For example, ``[(0, 5), (6, 10)]``.
        """
        def only_channels(channels: Set[Channel]) -> Callable:
            def channel_filter(time_inst) -> bool:
                """Filter channel.

                Args:
                    time_inst (Tuple[int, Instruction]): Time
                """
                return any([chan in channels for chan in time_inst[1].channels])
            return channel_filter

        def only_instruction_types(types: Iterable[abc.ABCMeta]) -> Callable:
            def instruction_filter(time_inst) -> bool:
                """Filter instruction.

                Args:
                    time_inst (Tuple[int, Instruction]): Time
                """
                return isinstance(time_inst[1], tuple(types))
            return instruction_filter

        def only_intervals(ranges: Iterable[Interval]) -> Callable:
            def interval_filter(time_inst) -> bool:
                """Filter interval.

                Args:
                    time_inst (Tuple[int, Instruction]): Time
                """
                for i in ranges:
                    inst_start = time_inst[0]
                    inst_stop = inst_start + time_inst[1].duration
                    if i[0] <= inst_start and inst_stop <= i[1]:
                        return True
                return False
            return interval_filter

        filter_func_list = list(filter_funcs)
        if channels is not None:
            filter_func_list.append(only_channels(set(channels)))
        if instruction_types is not None:
            filter_func_list.append(only_instruction_types(instruction_types))
        if time_ranges is not None:
            filter_func_list.append(only_intervals(time_ranges))
        if intervals is not None:
            filter_func_list.append(only_intervals(intervals))

        # return function returning true iff all filters are passed
        return lambda x: all([filter_func(x) for filter_func in filter_func_list])

    def _add_timeslots(self, time: int, schedule: ScheduleComponent) -> None:
        """Update all time tracking within this schedule based on the given schedule.

        Args:
            time: The time to insert the schedule into self.
            schedule: The schedule to insert into self.

        Raises:
            PulseError: If timeslots overlap or an invalid start time is provided.
        """
        if not isinstance(time, int):
            raise PulseError("Schedule start time must be an integer.")

        self._duration = max(self._duration, time + schedule.duration)

        for channel in schedule.channels:

            if channel not in self._timeslots:
                if time == 0:
                    self._timeslots[channel] = copy.copy(schedule._timeslots[channel])
                else:
                    self._timeslots[channel] = [(i[0] + time, i[1] + time)
                                                for i in schedule._timeslots[channel]]
                continue

            for idx, interval in enumerate(schedule._timeslots[channel]):
                if interval[0] + time >= self._timeslots[channel][-1][1]:
                    # Can append the remaining intervals
                    self._timeslots[channel].extend(
                        [(i[0] + time, i[1] + time)
                         for i in schedule._timeslots[channel][idx:]])
                    break

                try:
                    interval = (interval[0] + time, interval[1] + time)
                    index = _find_insertion_index(self._timeslots[channel], interval)
                    self._timeslots[channel].insert(index, interval)
                except PulseError:
                    raise PulseError(
                        "Schedule(name='{new}') cannot be inserted into Schedule(name='{old}') at "
                        "time {time} because its instruction on channel {ch} scheduled from time "
                        "{t0} to {tf} overlaps with an existing instruction."
                        "".format(new=schedule.name or '', old=self.name or '', time=time,
                                  ch=channel, t0=interval[0], tf=interval[1]))

        _check_nonnegative_timeslot(self._timeslots)

    def _remove_timeslots(self, time: int, schedule: ScheduleComponent):
        """Delete the timeslots if present for the respective schedule component.

        Args:
            time: The time to remove the timeslots for the ``schedule`` component.
            schedule: The schedule to insert into self.

        Raises:
            PulseError: If timeslots overlap or an invalid start time is provided.
        """
        if not isinstance(time, int):
            raise PulseError("Schedule start time must be an integer.")

        for channel in schedule.channels:

            if channel not in self._timeslots:
                raise PulseError(
                    'The channel {} is not present in the schedule'.format(channel))

            channel_timeslots = self._timeslots[channel]
            for interval in schedule._timeslots[channel]:
                if channel_timeslots:
                    interval = (interval[0] + time, interval[1] + time)
                    index = _interval_index(channel_timeslots, interval)
                    if channel_timeslots[index] == interval:
                        channel_timeslots.pop(index)
                        continue

                raise PulseError(
                    "Cannot find interval ({t0}, {tf}) to remove from "
                    "channel {ch} in Schedule(name='{name}').".format(
                        ch=channel, t0=interval[0], tf=interval[1], name=schedule.name))

            if not channel_timeslots:
                self._timeslots.pop(channel)

    def _replace_timeslots(self,
                           time: int,
                           old: ScheduleComponent,
                           new: ScheduleComponent):
        """Replace the timeslots of ``old`` if present with the timeslots of ``new``.

        Args:
            time: The time to remove the timeslots for the ``schedule`` component.
            old: Instruction to replace.
            new: Instruction to replace with.
        """
        self._remove_timeslots(time, old)
        self._add_timeslots(time, new)

    def replace(self,
                old: ScheduleComponent,
                new: ScheduleComponent,
                inplace: bool = False,
                ) -> 'Schedule':
        """Return a schedule with the ``old`` instruction replaced with a ``new``
        instruction.

        The replacment matching is based on an instruction equality check.

        .. jupyter-kernel:: python3
          :id: replace

        .. jupyter-execute::

          from qiskit import pulse

          d0 = pulse.DriveChannel(0)

          sched = pulse.Schedule()

          old = pulse.Play(pulse.Constant(100, 1.0), d0)
          new = pulse.Play(pulse.Constant(100, 0.1), d0)

          sched += old

          sched = sched.replace(old, new)

          assert sched == pulse.Schedule(new)

        Only matches at the top-level of the schedule tree. If you wish to
        perform this replacement over all instructions in the schedule tree.
        Flatten the schedule prior to running::

        .. jupyter-execute::

          sched = pulse.Schedule()

          sched += pulse.Schedule(old)

          sched = sched.flatten()

          sched = sched.replace(old, new)

          assert sched == pulse.Schedule(new)

        Args:
          old: Instruction to replace.
          new: Instruction to replace with.
          inplace: Replace instruction by mutably modifying this ``Schedule``.

        Returns:
          The modified schedule with ``old`` replaced by ``new``.

        Raises:
            PulseError: If the ``Schedule`` after replacements will has a timing overlap.
        """
        new_children = []
        for time, child in self._children:
            if child == old:
                new_children.append((time, new))
                if inplace:
                    self._replace_timeslots(time, old, new)
            else:
                new_children.append((time, child))

        if inplace:
            self.__children = new_children
            return self
        else:
            try:
                return Schedule(*new_children)
            except PulseError as err:
                raise PulseError(
                    'Replacement of {old} with {new} results in '
                    'overlapping instructions.'.format(
                        old=old, new=new)) from err

    def draw(self, dt: float = 1, style=None,
             filename: Optional[str] = None, interp_method: Optional[Callable] = None,
             scale: Optional[float] = None,
             channel_scales: Optional[Dict[Channel, float]] = None,
             plot_all: bool = False, plot_range: Optional[Tuple[float]] = None,
             interactive: bool = False, table: bool = False, label: bool = False,
             framechange: bool = True,
             channels: Optional[List[Channel]] = None,
             show_framechange_channels: bool = True):
        r"""Plot the schedule.

        Args:
            dt: Time interval of samples.
            style (Optional[SchedStyle]): A style sheet to configure plot appearance.
            filename: Name required to save pulse image.
            interp_method: A function for interpolation.
            scale: Relative visual scaling of waveform amplitudes, see Additional Information.
            channel_scales: Channel independent scaling as a dictionary of ``Channel`` object.
            plot_all: Plot empty channels.
            plot_range: A tuple of time range to plot.
            interactive: When set true show the circuit in a new window
                         (this depends on the matplotlib backend being used supporting this).
            table: Draw event table for supported commands.
            label: Label individual instructions.
            framechange: Add framechange indicators.
            channels: A list of channel names to plot.
            show_framechange_channels: Plot channels with only framechanges.

        Additional Information:
            If you want to manually rescale the waveform amplitude of channels one by one,
            you can set ``channel_scales`` argument instead of ``scale``.
            The ``channel_scales`` should be given as a python dictionary::

                channel_scales = {pulse.DriveChannels(0): 10.0,
                                  pulse.MeasureChannels(0): 5.0}

            When the channel to plot is not included in the ``channel_scales`` dictionary,
            scaling factor of that channel is overwritten by the value of ``scale`` argument.
            In default, waveform amplitude is normalized by the maximum amplitude of the channel.
            The scaling factor is displayed under the channel name alias.

        Returns:
            matplotlib.Figure: A matplotlib figure object of the pulse schedule.
        """
        # pylint: disable=invalid-name, cyclic-import
        from qiskit import visualization

        return visualization.pulse_drawer(self, dt=dt, style=style,
                                          filename=filename, interp_method=interp_method,
                                          scale=scale, channel_scales=channel_scales,
                                          plot_all=plot_all, plot_range=plot_range,
                                          interactive=interactive, table=table, label=label,
                                          framechange=framechange, channels=channels,
                                          show_framechange_channels=show_framechange_channels)

    def __eq__(self, other: ScheduleComponent) -> bool:
        """Test if two ScheduleComponents are equal.

        Equality is checked by verifying there is an equal instruction at every time
        in ``other`` for every instruction in this ``Schedule``.

        .. warning::

            This does not check for logical equivalency. Ie.,

            ```python
            >>> (Delay(10)(DriveChannel(0)) + Delay(10)(DriveChannel(0)) ==
                 Delay(20)(DriveChannel(0)))
            False
            ```
        """
        channels = set(self.channels)
        other_channels = set(other.channels)

        # first check channels are the same
        if channels != other_channels:
            return False

        # then verify same number of instructions in each
        instructions = self.instructions
        other_instructions = other.instructions
        if len(instructions) != len(other_instructions):
            return False

        # finally check each instruction in `other` is in this schedule
        for idx, inst in enumerate(other_instructions):
            # check assumes `Schedule.instructions` is sorted consistently
            if instructions[idx] != inst:
                return False

        return True

    def __add__(self, other: ScheduleComponent) -> 'Schedule':
        """Return a new schedule with ``other`` inserted within ``self`` at ``start_time``."""
        return self.append(other)

    def __or__(self, other: ScheduleComponent) -> 'Schedule':
        """Return a new schedule which is the union of `self` and `other`."""
        return self.insert(0, other)

    def __lshift__(self, time: int) -> 'Schedule':
        """Return a new schedule which is shifted forward by ``time``."""
        return self.shift(time)

    def __len__(self) -> int:
        """Return number of instructions in the schedule."""
        return len(self.instructions)

    def __repr__(self):
        name = format(self._name) if self._name else ""
        instructions = ", ".join([repr(instr) for instr in self.instructions[:50]])
        if len(self.instructions) > 25:
            instructions += ", ..."
        return 'Schedule({}, name="{}")'.format(instructions, name)


class ParameterizedSchedule:
    """Temporary parameterized schedule class.

    This should not be returned to users as it is currently only a helper class.

    This class is takes an input command definition that accepts
    a set of parameters. Calling ``bind`` on the class will return a ``Schedule``.

    # TODO: In the near future this will be replaced with proper incorporation of parameters
            into the ``Schedule`` class.
    """

    def __init__(self, *schedules, parameters: Optional[Dict[str, Union[float, complex]]] = None,
                 name: Optional[str] = None):
        full_schedules = []
        parameterized = []
        parameters = parameters or []
        self.name = name or ''
        # partition schedules into callable and schedules
        for schedule in schedules:
            if isinstance(schedule, ParameterizedSchedule):
                parameterized.append(schedule)
                parameters += schedule.parameters
            elif callable(schedule):
                parameterized.append(schedule)
            elif isinstance(schedule, Schedule):
                full_schedules.append(schedule)
            else:
                raise PulseError('Input type: {} not supported'.format(type(schedule)))

        self._parameterized = tuple(parameterized)
        self._schedules = tuple(full_schedules)
        self._parameters = tuple(sorted(set(parameters)))

    @property
    def parameters(self) -> Tuple[str]:
        """Schedule parameters."""
        return self._parameters

    def bind_parameters(self, *args: List[Union[float, complex]],
                        **kwargs: Dict[str, Union[float, complex]]) -> Schedule:
        """Generate the Schedule from params to evaluate command expressions"""
        bound_schedule = Schedule(name=self.name)
        schedules = list(self._schedules)

        named_parameters = {}
        if args:
            for key, val in zip(self.parameters, args):
                named_parameters[key] = val
        if kwargs:
            for key, val in kwargs.items():
                if key in self.parameters:
                    if key not in named_parameters.keys():
                        named_parameters[key] = val
                    else:
                        raise PulseError("%s got multiple values for argument '%s'"
                                         % (self.__class__.__name__, key))
                else:
                    raise PulseError("%s got an unexpected keyword argument '%s'"
                                     % (self.__class__.__name__, key))

        for param_sched in self._parameterized:
            # recursively call until based callable is reached
            if isinstance(param_sched, type(self)):
                predefined = param_sched.parameters
            else:
                # assuming no other parametrized instructions
                predefined = self.parameters
            sub_params = {k: v for k, v in named_parameters.items() if k in predefined}
            schedules.append(param_sched(**sub_params))

        # construct evaluated schedules
        for sched in schedules:
            if isinstance(sched, tuple):
                bound_schedule.insert(sched[0], sched[1])
            else:
                bound_schedule |= sched

        return bound_schedule

    def __call__(self, *args: List[Union[float, complex]],
                 **kwargs: Dict[str, Union[float, complex]]) -> Schedule:
        return self.bind_parameters(*args, **kwargs)


def _interval_index(intervals: List[Interval], interval: Interval) -> int:
    """Find the index of an interval.

    Args:
        intervals: A sorted list of non-overlapping Intervals.
        interval: The interval for which the index into intervals will be found.

    Returns:
        The index of the interval.

    Raises:
        PulseError: If the interval does not exist.
    """
    index = _locate_interval_index(intervals, interval)
    found_interval = intervals[index]
    if found_interval != interval:
        raise PulseError('The interval: {} does not exist in intervals: {}'.format(
            interval, intervals
        ))
    return index


def _locate_interval_index(intervals: List[Interval],
                           interval: Interval,
                           index: int = 0) -> int:
    """Using binary search on start times, find an interval.

    Args:
        intervals: A sorted list of non-overlapping Intervals.
        interval: The interval for which the index into intervals will be found.
        index: A running tally of the index, for recursion. The user should not pass a value.

    Returns:
        The index into intervals that new_interval would be inserted to maintain
        a sorted list of intervals.
    """
    if not intervals or len(intervals) == 1:
        return index

    mid_idx = len(intervals) // 2
    mid = intervals[mid_idx]
    if interval[1] <= mid[0] and (interval != mid):
        return _locate_interval_index(intervals[:mid_idx], interval, index=index)
    else:
        return _locate_interval_index(intervals[mid_idx:], interval, index=index + mid_idx)


def _find_insertion_index(intervals: List[Interval], new_interval: Interval) -> int:
    """Using binary search on start times, return the index into `intervals` where the new interval
    belongs, or raise an error if the new interval overlaps with any existing ones.

    Args:
        intervals: A sorted list of non-overlapping Intervals.
        new_interval: The interval for which the index into intervals will be found.

    Returns:
        The index into intervals that new_interval should be inserted to maintain a sorted list
        of intervals.

    Raises:
        PulseError: If new_interval overlaps with the given intervals.
    """
    index = _locate_interval_index(intervals, new_interval)
    if index < len(intervals):
        if _overlaps(intervals[index], new_interval):
            raise PulseError("New interval overlaps with existing.")
        return index if new_interval[1] <= intervals[index][0] else index + 1
    return index


def _overlaps(first: Interval, second: Interval) -> bool:
    """Return True iff first and second overlap.

    Note: first.stop may equal second.start, since Interval stop times are exclusive.
    """
    if first[0] == second[0] == second[1]:
        # They fail to overlap if one of the intervals has duration 0
        return False
    if first[0] > second[0]:
        first, second = second, first
    return second[0] < first[1]


def _check_nonnegative_timeslot(timeslots):
    """Test that a channel has no negative timeslots.

    Raises:
        PulseError: If a channel timeslot is negative.
    """
    for chan, chan_timeslots in timeslots.items():
        if chan_timeslots:
            if chan_timeslots[0][0] < 0:
                raise PulseError(
                    "An instruction on {} has a negative "
                    " starting time.".format(chan))
