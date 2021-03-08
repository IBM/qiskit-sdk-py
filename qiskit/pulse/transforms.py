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

"""Basic rescheduling functions which take schedules or instructions
(and possibly some arguments) and return new schedules.
"""
import warnings
from collections import defaultdict
from copy import deepcopy
from typing import Callable
from typing import Dict, List, Optional, Iterable, Union

import numpy as np

from qiskit.pulse import channels as chans, exceptions, instructions
from qiskit.pulse.exceptions import PulseError
from qiskit.pulse.instruction_schedule_map import InstructionScheduleMap
from qiskit.pulse.instructions import directives
from qiskit.pulse.schedule import Schedule, ScheduleComponent
from qiskit.pulse.frame import Frame
from qiskit.pulse.resolved_frame import ResolvedFrame, ChannelTracker
from qiskit.pulse.library import Signal


def align_measures(schedules: Iterable[Union['Schedule', instructions.Instruction]],
                   inst_map: Optional[InstructionScheduleMap] = None,
                   cal_gate: str = 'u3',
                   max_calibration_duration: Optional[int] = None,
                   align_time: Optional[int] = None,
                   align_all: Optional[bool] = True,
                   ) -> List[Schedule]:
    """Return new schedules where measurements occur at the same physical time.

    This transformation will align the first :class:`qiskit.pulse.Acquire` on
    every channel to occur at the same time.

    Minimum measurement wait time (to allow for calibration pulses) is enforced
    and may be set with ``max_calibration_duration``.

    By default only instructions containing a :class:`~qiskit.pulse.AcquireChannel`
    or :class:`~qiskit.pulse.MeasureChannel` will be shifted. If you wish to keep
    the relative timing of all instructions in the schedule set ``align_all=True``.

    This method assumes that ``MeasureChannel(i)`` and ``AcquireChannel(i)``
    correspond to the same qubit and the acquire/play instructions
    should be shifted together on these channels.

    .. jupyter-kernel:: python3
        :id: align_measures

    .. jupyter-execute::

        from qiskit import pulse
        from qiskit.pulse import transforms

        with pulse.build() as sched:
            with pulse.align_sequential():
                pulse.play(pulse.Constant(10, 0.5), pulse.DriveChannel(0))
                pulse.play(pulse.Constant(10, 1.), pulse.MeasureChannel(0))
                pulse.acquire(20, pulse.AcquireChannel(0), pulse.MemorySlot(0))

        sched_shifted = sched << 20

        aligned_sched, aligned_sched_shifted = transforms.align_measures([sched, sched_shifted])

        assert aligned_sched == aligned_sched_shifted

    If it is desired to only shift acquisition and measurement stimulus instructions
    set the flag ``align_all=False``:

    .. jupyter-execute::

        aligned_sched, aligned_sched_shifted = transforms.align_measures(
            [sched, sched_shifted],
            align_all=False,
        )

        assert aligned_sched != aligned_sched_shifted


    Args:
        schedules: Collection of schedules to be aligned together
        inst_map: Mapping of circuit operations to pulse schedules
        cal_gate: The name of the gate to inspect for the calibration time
        max_calibration_duration: If provided, inst_map and cal_gate will be ignored
        align_time: If provided, this will be used as final align time.
        align_all: Shift all instructions in the schedule such that they maintain
            their relative alignment with the shifted acquisition instruction.
            If ``False`` only the acquisition and measurement pulse instructions
            will be shifted.
    Returns:
        The input list of schedules transformed to have their measurements aligned.

    Raises:
        PulseError: If the provided alignment time is negative.
    """
    def get_first_acquire_times(schedules):
        """Return a list of first acquire times for each schedule."""
        acquire_times = []
        for schedule in schedules:
            visited_channels = set()
            qubit_first_acquire_times = defaultdict(lambda: None)

            for time, inst in schedule.instructions:
                if (isinstance(inst, instructions.Acquire) and
                        inst.channel not in visited_channels):
                    visited_channels.add(inst.channel)
                    qubit_first_acquire_times[inst.channel.index] = time

            acquire_times.append(qubit_first_acquire_times)
        return acquire_times

    def get_max_calibration_duration(inst_map, cal_gate):
        """Return the time needed to allow for readout discrimination calibration pulses."""
        # TODO (qiskit-terra #5472): fix behavior of this.
        max_calibration_duration = 0
        for qubits in inst_map.qubits_with_instruction(cal_gate):
            cmd = inst_map.get(cal_gate, qubits, np.pi, 0, np.pi)
            max_calibration_duration = max(cmd.duration, max_calibration_duration)
        return max_calibration_duration

    if align_time is not None and align_time < 0:
        raise exceptions.PulseError("Align time cannot be negative.")

    first_acquire_times = get_first_acquire_times(schedules)
    # Extract the maximum acquire in every schedule across all acquires in the schedule.
    # If there are no acquires in the schedule default to 0.
    max_acquire_times = [max(0, *times.values()) for times in first_acquire_times]
    if align_time is None:
        if max_calibration_duration is None:
            if inst_map:
                max_calibration_duration = get_max_calibration_duration(inst_map, cal_gate)
            else:
                max_calibration_duration = 0
        align_time = max(max_calibration_duration, *max_acquire_times)

    # Shift acquires according to the new scheduled time
    new_schedules = []
    for sched_idx, schedule in enumerate(schedules):
        new_schedule = Schedule(name=schedule.name, metadata=schedule.metadata)
        stop_time = schedule.stop_time

        if align_all:
            if first_acquire_times[sched_idx]:
                shift = align_time - max_acquire_times[sched_idx]
            else:
                shift = align_time - stop_time
        else:
            shift = 0

        for time, inst in schedule.instructions:
            measurement_channels = {
                chan.index for chan in inst.channels if
                isinstance(chan, (chans.MeasureChannel, chans.AcquireChannel))
            }
            if measurement_channels:
                sched_first_acquire_times = first_acquire_times[sched_idx]
                max_start_time = max(sched_first_acquire_times[chan]
                                     for chan in measurement_channels if
                                     chan in sched_first_acquire_times)
                shift = align_time - max_start_time

            if shift < 0:
                warnings.warn(
                    "The provided alignment time is scheduling an acquire instruction "
                    "earlier than it was scheduled for in the original Schedule. "
                    "This may result in an instruction being scheduled before t=0 and "
                    "an error being raised."
                )
            new_schedule.insert(time+shift, inst, inplace=True)

        new_schedules.append(new_schedule)

    return new_schedules


def add_implicit_acquires(schedule: Union['Schedule', instructions.Instruction],
                          meas_map: List[List[int]]
                          ) -> Schedule:
    """Return a new schedule with implicit acquires from the measurement mapping replaced by
    explicit ones.

    .. warning:: Since new acquires are being added, Memory Slots will be set to match the
                 qubit index. This may overwrite your specification.

    Args:
        schedule: Schedule to be aligned.
        meas_map: List of lists of qubits that are measured together.

    Returns:
        A ``Schedule`` with the additional acquisition instructions.
    """
    new_schedule = Schedule(name=schedule.name, metadata=schedule.metadata)
    acquire_map = dict()

    for time, inst in schedule.instructions:
        if isinstance(inst, instructions.Acquire):
            if inst.mem_slot and inst.mem_slot.index != inst.channel.index:
                warnings.warn("One of your acquires was mapped to a memory slot which didn't match"
                              " the qubit index. I'm relabeling them to match.")

            # Get the label of all qubits that are measured with the qubit(s) in this instruction
            all_qubits = []
            for sublist in meas_map:
                if inst.channel.index in sublist:
                    all_qubits.extend(sublist)
            # Replace the old acquire instruction by a new one explicitly acquiring all qubits in
            # the measurement group.
            for i in all_qubits:
                explicit_inst = instructions.Acquire(inst.duration,
                                                     chans.AcquireChannel(i),
                                                     mem_slot=chans.MemorySlot(i),
                                                     kernel=inst.kernel,
                                                     discriminator=inst.discriminator)
                if time not in acquire_map:
                    new_schedule.insert(time, explicit_inst, inplace=True)
                    acquire_map = {time: {i}}
                elif i not in acquire_map[time]:
                    new_schedule.insert(time, explicit_inst, inplace=True)
                    acquire_map[time].add(i)
        else:
            new_schedule.insert(time, inst, inplace=True)

    return new_schedule


def pad(schedule: Schedule,
        channels: Optional[Iterable[chans.Channel]] = None,
        until: Optional[int] = None,
        inplace: bool = False
        ) -> Schedule:
    r"""Pad the input Schedule with ``Delay``\s on all unoccupied timeslots until
    ``schedule.duration`` or ``until`` if not ``None``.

    Args:
        schedule: Schedule to pad.
        channels: Channels to pad. Defaults to all channels in
            ``schedule`` if not provided. If the supplied channel is not a member
            of ``schedule`` it will be added.
        until: Time to pad until. Defaults to ``schedule.duration`` if not provided.
        inplace: Pad this schedule by mutating rather than returning a new schedule.

    Returns:
        The padded schedule.
    """
    until = until or schedule.duration
    channels = channels or schedule.channels

    for channel in channels:
        if channel not in schedule.channels:
            schedule |= instructions.Delay(until, channel)
            continue

        curr_time = 0
        # Use the copy of timeslots. When a delay is inserted before the current interval,
        # current timeslot is pointed twice and the program crashes with the wrong pointer index.
        timeslots = schedule.timeslots[channel].copy()
        # TODO: Replace with method of getting instructions on a channel
        for interval in timeslots:
            if curr_time >= until:
                break
            if interval[0] != curr_time:
                end_time = min(interval[0], until)
                schedule = schedule.insert(
                    curr_time,
                    instructions.Delay(end_time - curr_time, channel),
                    inplace=inplace)
            curr_time = interval[1]
        if curr_time < until:
            schedule = schedule.insert(
                curr_time,
                instructions.Delay(until - curr_time, channel),
                inplace=inplace)

    return schedule


def compress_pulses(schedules: List[Schedule]) -> List[Schedule]:
    """Optimization pass to replace identical pulses.

    Args:
        schedules: Schedules to compress.

    Returns:
        Compressed schedules.
    """

    existing_pulses = []
    new_schedules = []

    for schedule in schedules:
        new_schedule = Schedule(name=schedule.name, metadata=schedule.metadata)

        for time, inst in schedule.instructions:
            if isinstance(inst, instructions.Play):
                if inst.pulse in existing_pulses:
                    idx = existing_pulses.index(inst.pulse)
                    identical_pulse = existing_pulses[idx]
                    new_schedule.insert(time,
                                        instructions.Play(identical_pulse,
                                                          inst.channel,
                                                          inst.name),
                                        inplace=True)
                else:
                    existing_pulses.append(inst.pulse)
                    new_schedule.insert(time, inst, inplace=True)
            else:
                new_schedule.insert(time, inst, inplace=True)

        new_schedules.append(new_schedule)

    return new_schedules


def resolve_frames(schedule: Schedule, frames_config: Dict[int, Dict]) -> Schedule:
    """
    Parse the schedule and replace instructions on Frames by instructions on the
    appropriate channels.

    Args:
        schedule: The schedule for which to replace frames with the appropriate
            channels.
        frames_config: A dictionary with the frame index as key and the values are
            a dict which can be used to initialized a ResolvedFrame.

    Returns:
        new_schedule: A new schedule where frames have been replaced with
            their corresponding Drive, Control, and/or Measure channels.

    Raises:
        PulseError: if a frame is not configured.
    """
    if frames_config is None:
        return schedule

    resolved_frames = {}
    for frame_settings in frames_config.values():
        frame = ResolvedFrame(**frame_settings)
        frame.set_frame_instructions(schedule)
        resolved_frames[frame.index] = frame

    # Used to keep track of the frequency and phase of the channels
    channel_trackers = {}
    for ch in schedule.channels:
        if isinstance(ch, chans.PulseChannel):
            channel_trackers[ch] = ChannelTracker(ch)

    # Add the channels that the frames broadcast on.
    for frame in resolved_frames.values():
        for ch in frame.channels:
            if ch not in channel_trackers:
                channel_trackers[ch] = ChannelTracker(ch)

    sched = Schedule(name=schedule.name, metadata=schedule.metadata)

    for time, inst in schedule.instructions:
        chan = inst.channel

        if isinstance(inst, instructions.Play):
            if isinstance(inst.operands[0], Signal):
                frame_idx = inst.operands[0].frame.index

                if frame_idx not in resolved_frames:
                    raise PulseError(f'{Frame(frame.index)} is not configured and cannot '
                                     f'be resolved.')

                frame = resolved_frames[frame_idx]

                frame_freq = frame.frequency(time)
                frame_phase = frame.phase(time)

                # If the frequency and phase of the channel has already been set once in
                # The past we compute shifts.
                if channel_trackers[chan].is_initialized():
                    freq_diff = frame_freq - channel_trackers[chan].frequency(time)
                    phase_diff = frame_phase - channel_trackers[chan].phase(time)

                    if freq_diff != 0.0:
                        shift_freq = instructions.ShiftFrequency(freq_diff, chan)
                        sched.insert(time, shift_freq, inplace=True)

                    if phase_diff != 0.0:
                        sched.insert(time, instructions.ShiftPhase(phase_diff, chan), inplace=True)

                # If the channel's phase and frequency has not been set in the past
                # we set t now
                else:
                    sched.insert(time, instructions.SetFrequency(frame_freq, chan), inplace=True)
                    sched.insert(time, instructions.SetPhase(frame_phase, chan), inplace=True)

                # Update the frequency and phase of this channel.
                channel_trackers[chan].set_frequency(time, frame_freq)
                channel_trackers[chan].set_phase(time, frame_phase)

                play = instructions.Play(inst.operands[0].pulse, chan)
                sched.insert(time, play, inplace=True)
            else:
                sched.insert(time, instructions.Play(inst.pulse, chan), inplace=True)

        # Insert phase and frequency commands that are not applied to frames.
        elif isinstance(type(inst), (instructions.SetFrequency, instructions.ShiftFrequency)):
            if issubclass(chan, chans.PulseChannel):
                sched.insert(time, type(inst)(inst.frequency, chan))

        elif isinstance(type(inst), (instructions.SetPhase, instructions.ShiftPhase)):
            if issubclass(chan, chans.PulseChannel):
                sched.insert(time, type(inst)(inst.phase, chan))

        else:
            sched.insert(time, inst, inplace=True)

    return sched


def _push_left_append(this: Schedule,
                      other: Union['Schedule', instructions.Instruction],
                      ignore_frames: bool
                      ) -> Schedule:
    r"""Return ``this`` with ``other`` inserted at the maximum time over
    all channels shared between ```this`` and ``other``.

    Args:
        this: Input schedule to which ``other`` will be inserted.
        other: Other schedule to insert.
        ignore_frames: If true then frame instructions will be ignore. This
            should be set to true if the played Signals in this context
            do not share any frames.

    Returns:
        Push left appended schedule.
    """
    this_channels = set(this.channels)
    other_channels = set(other.channels)
    shared_channels = list(this_channels & other_channels)

    # Conservatively assume that a Frame instruction could impact all channels
    if not ignore_frames:
        for ch in this_channels | other_channels:
            if isinstance(ch, Frame):
                shared_channels = list(this_channels | other_channels)
                break

    ch_slacks = [this.stop_time - this.ch_stop_time(channel) + other.ch_start_time(channel)
                 for channel in shared_channels]

    if ch_slacks:
        slack_chan = shared_channels[np.argmin(ch_slacks)]
        shared_insert_time = this.ch_stop_time(slack_chan) - other.ch_start_time(slack_chan)
    else:
        shared_insert_time = 0

    # Handle case where channels not common to both might actually start
    # after ``this`` has finished.
    other_only_insert_time = other.ch_start_time(*(other_channels - this_channels))
    # Choose whichever is greatest.
    insert_time = max(shared_insert_time, other_only_insert_time)
    return this.insert(insert_time, other, inplace=True)


def align_left(schedule: Schedule, ignore_frames: bool = False) -> Schedule:
    """Align a list of pulse instructions on the left.

    Args:
        schedule: Input schedule of which top-level ``child`` nodes will be
            rescheduled.
        ignore_frames: If true then frame instructions will be ignore. This
            should be set to true if the played Signals in this context
            do not share any frames.

    Returns:
        New schedule with input `schedule`` child schedules and instructions
        left aligned.
    """
    aligned = Schedule()
    for _, child in schedule._children:
        _push_left_append(aligned, child, ignore_frames)
    return aligned


def _push_right_prepend(this: Union['Schedule', instructions.Instruction],
                        other: Union['Schedule', instructions.Instruction],
                        ignore_frames: bool
                        ) -> Schedule:
    r"""Return ``this`` with ``other`` inserted at the latest possible time
    such that ``other`` ends before it overlaps with any of ``this``.

    If required ``this`` is shifted  to start late enough so that there is room
    to insert ``other``.

    Args:
       this: Input schedule to which ``other`` will be inserted.
       other: Other schedule to insert.
       ignore_frames: If true then frame instructions will be ignore. This
            should be set to true if the played Signals in this context
            do not share any frames.

    Returns:
       Push right prepended schedule.
    """
    this_channels = set(this.channels)
    other_channels = set(other.channels)
    shared_channels = list(this_channels & other_channels)

    # Conservatively assume that a Frame instruction could impact all channels
    if not ignore_frames:
        for ch in this_channels | other_channels:
            if isinstance(ch, Frame):
                shared_channels = list(this_channels | other_channels)
                break

    ch_slacks = [this.ch_start_time(channel) - other.ch_stop_time(channel)
                 for channel in shared_channels]

    if ch_slacks:
        insert_time = min(ch_slacks) + other.start_time
    else:
        insert_time = this.stop_time - other.stop_time + other.start_time

    if insert_time < 0:
        this.shift(-insert_time, inplace=True)
        this.insert(0, other, inplace=True)
    else:
        this.insert(insert_time, other, inplace=True)

    return this


def align_right(schedule: Schedule, ignore_frames: bool = False) -> Schedule:
    """Align a list of pulse instructions on the right.

    Args:
        schedule: Input schedule of which top-level ``child`` nodes will be
            rescheduled.
        ignore_frames: If true then frame instructions will be ignore. This
            should be set to true if the played Signals in this context
            do not share any frames.

    Returns:
        New schedule with input `schedule`` child schedules and instructions
        right aligned.
    """
    aligned = Schedule()
    for _, child in reversed(schedule._children):
        aligned = _push_right_prepend(aligned, child, ignore_frames)
    return aligned


def align_sequential(schedule: Schedule) -> Schedule:
    """Schedule all top-level nodes in parallel.

    Args:
        schedule: Input schedule of which top-level ``child`` nodes will be
            rescheduled.

    Returns:
        New schedule with input `schedule`` child schedules and instructions
        applied sequentially across channels
    """
    aligned = Schedule()
    for _, child in schedule._children:
        aligned.insert(aligned.duration, child, inplace=True)
    return aligned


def align_equispaced(schedule: Schedule,
                     duration: int) -> Schedule:
    """Schedule a list of pulse instructions with equivalent interval.

    Args:
        schedule: Input schedule of which top-level ``child`` nodes will be
            rescheduled.
        duration: Duration of context. This should be larger than the schedule duration.

    Returns:
        New schedule with input `schedule`` child schedules and instructions
        aligned with equivalent interval.

    Notes:
        This context is convenient for writing PDD or Hahn echo sequence for example.
    """
    total_duration = sum([child.duration for _, child in schedule._children])
    if duration and duration < total_duration:
        return schedule

    total_delay = duration - total_duration

    if len(schedule._children) > 1:
        # Calculate the interval in between sub-schedules.
        # If the duration cannot be divided by the number of sub-schedules,
        # the modulo is appended and prepended to the input schedule.
        interval, mod = np.divmod(total_delay, len(schedule._children) - 1)
    else:
        interval = 0
        mod = total_delay

    # Calculate pre schedule delay
    delay, mod = np.divmod(mod, 2)

    aligned = Schedule()
    # Insert sub-schedules with interval
    _t0 = int(aligned.stop_time + delay + mod)
    for _, child in schedule._children:
        aligned.insert(_t0, child, inplace=True)
        _t0 = int(aligned.stop_time + interval)

    return pad(aligned, aligned.channels, until=duration, inplace=True)


def align_func(schedule: Schedule,
               duration: int,
               func: Callable[[int], float]) -> Schedule:
    """Schedule a list of pulse instructions with schedule position defined by the
    numerical expression.

    Args:
        schedule: Input schedule of which top-level ``child`` nodes will be
            rescheduled.
        duration: Duration of context. This should be larger than the schedule duration.
        func: A function that takes an index of sub-schedule and returns the
            fractional coordinate of of that sub-schedule.
            The returned value should be defined within [0, 1].
            The pulse index starts from 1.

    Returns:
        New schedule with input `schedule`` child schedules and instructions
        aligned with equivalent interval.

    Notes:
        This context is convenient for writing UDD sequence for example.
    """
    if duration < schedule.duration:
        return schedule

    aligned = Schedule()
    for ind, (_, child) in enumerate(schedule._children):
        _t_center = duration * func(ind + 1)
        _t0 = int(_t_center - 0.5 * child.duration)
        if _t0 < 0 or _t0 > duration:
            PulseError('Invalid schedule position t=%d is specified at index=%d' % (_t0, ind))
        aligned.insert(_t0, child, inplace=True)

    return pad(aligned, aligned.channels, until=duration, inplace=True)


def flatten(program: ScheduleComponent) -> ScheduleComponent:
    """Flatten (inline) any called nodes into a Schedule tree with no nested children."""
    if isinstance(program, instructions.Instruction):
        return program
    else:
        return Schedule(*program.instructions,
                        name=program.name,
                        metadata=program.metadata)


def inline_subroutines(program: Schedule) -> Schedule:
    """Recursively remove call instructions and inline the respective subroutine instructions.

    Assigned parameter values, which are stored in the parameter table, are also applied.
    The subroutine is copied before the parameter assignment to avoid mutation problem.

    Args:
        program: A program which may contain the subroutine, i.e. ``Call`` instruction.

    Returns:
        A schedule without subroutine.
    """
    schedule = Schedule(name=program.name, metadata=program.metadata)
    for t0, inst in program.instructions:
        if isinstance(inst, instructions.Call):
            # bind parameter
            if bool(inst.arguments):
                subroutine = deepcopy(inst.subroutine)
                subroutine.assign_parameters(value_dict=inst.arguments)
            else:
                subroutine = inst.subroutine
            # recursively inline the program
            inline_schedule = inline_subroutines(subroutine)
            schedule.insert(t0, inline_schedule, inplace=True)
        else:
            schedule.insert(t0, inst, inplace=True)
    return schedule


def remove_directives(schedule: Schedule) -> Schedule:
    """Remove directives."""
    return schedule.exclude(instruction_types=[directives.Directive])


def remove_trivial_barriers(schedule: Schedule) -> Schedule:
    """Remove trivial barriers with 0 or 1 channels."""
    def filter_func(inst):
        return (isinstance(inst[1], directives.RelativeBarrier) and
                len(inst[1].channels) < 2)

    return schedule.exclude(filter_func)
