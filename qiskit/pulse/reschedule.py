# -*- coding: utf-8 -*-

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

"""
Basic rescheduling functions which take schedules or instructions
(and possibly some arguments) and return new schedules.
"""
import warnings

from typing import List, Optional, Iterable, Union

import numpy as np

from qiskit.pulse import (Acquire, AcquireInstruction, Delay,
                          InstructionScheduleMap, ScheduleComponent, Schedule,
                          Instruction)
from .channels import Channel, AcquireChannel, MeasureChannel, MemorySlot
from .exceptions import PulseError


def align_measures(schedules: Iterable[ScheduleComponent],
                   inst_map: Optional[InstructionScheduleMap] = None,
                   cal_gate: str = 'u3',
                   max_calibration_duration: Optional[int] = None,
                   align_time: Optional[int] = None) -> List[Schedule]:
    """Return new schedules where measurements occur at the same physical time. Minimum measurement
    wait time (to allow for calibration pulses) is enforced.

    This is only defined for schedules that are acquire-less or acquire-final per channel: a
    schedule with pulses or acquires occurring on a channel which has already had a measurement will
    throw an error.

    Args:
        schedules: Collection of schedules to be aligned together
        inst_map: Mapping of circuit operations to pulse schedules
        cal_gate: The name of the gate to inspect for the calibration time
        max_calibration_duration: If provided, inst_map and cal_gate will be ignored
        align_time: If provided, this will be used as final align time.

    Raises:
        PulseError: if an acquire or pulse is encountered on a channel that has already been part
                    of an acquire, or if align_time is negative
    """
    def calculate_align_time():
        """Return the the max between the duration of the calibration time and the absolute time
        of the latest scheduled acquire.
        """
        nonlocal max_calibration_duration
        if max_calibration_duration is None:
            max_calibration_duration = get_max_calibration_duration()
        align_time = max_calibration_duration
        for schedule in schedules:
            last_acquire = 0
            acquire_times = [time for time, inst in schedule.instructions
                             if isinstance(inst, (Acquire, AcquireInstruction))]
            if acquire_times:
                last_acquire = max(acquire_times)
            align_time = max(align_time, last_acquire)
        return align_time

    def get_max_calibration_duration():
        """Return the time needed to allow for readout discrimination calibration pulses."""
        max_calibration_duration = 0
        for qubits in inst_map.qubits_with_instruction(cal_gate):
            cmd = inst_map.get(cal_gate, qubits, np.pi, 0, np.pi)
            max_calibration_duration = max(cmd.duration, max_calibration_duration)
        return max_calibration_duration

    if align_time is None and max_calibration_duration is None and inst_map is None:
        raise PulseError("Must provide a inst_map, an alignment time, or a calibration duration.")
    if align_time is not None and align_time < 0:
        raise PulseError("Align time cannot be negative.")
    if align_time is None:
        align_time = calculate_align_time()

    # Shift acquires according to the new scheduled time
    new_schedules = []
    for schedule in schedules:
        new_schedule = Schedule(name=schedule.name)
        acquired_channels = set()
        measured_channels = set()

        for time, inst in schedule.instructions:
            for chan in inst.channels:
                if isinstance(chan, MeasureChannel):
                    if chan.index in measured_channels:
                        raise PulseError("Multiple measurements are not supported by this "
                                         "rescheduling pass.")
                elif chan.index in acquired_channels:
                    raise PulseError("Pulse encountered on channel {0} after acquire on "
                                     "same channel.".format(chan.index))

            if isinstance(inst, (Acquire, AcquireInstruction)):
                if time > align_time:
                    warnings.warn("You provided an align_time which is scheduling an acquire "
                                  "sooner than it was scheduled for in the original Schedule.")
                new_schedule |= inst << align_time
                acquired_channels.update({a.index for a in inst.acquires})
            elif isinstance(inst.channels[0], MeasureChannel):
                new_schedule |= inst << align_time
                measured_channels.update({a.index for a in inst.channels})
            else:
                new_schedule |= inst << time

        new_schedules.append(new_schedule)

    return new_schedules


def add_implicit_acquires(schedule: ScheduleComponent, meas_map: List[List[int]]) -> Schedule:
    """Return a new schedule with implicit acquires from the measurement mapping replaced by
    explicit ones.

    .. warning:: Since new acquires are being added, Memory Slots will be set to match the
                 qubit index. This may overwrite your specification.

    Args:
        schedule: Schedule to be aligned.
        meas_map: List of lists of qubits that are measured together.

    Returns:
        A ``Schedule`` with the additional acquisition commands.
    """
    new_schedule = Schedule(name=schedule.name)
    acquire_map = dict()

    for time, inst in schedule.instructions:
        if isinstance(inst, (Acquire, AcquireInstruction)):
            if any([acq.index != mem.index for acq, mem in zip(inst.acquires, inst.mem_slots)]):
                warnings.warn("One of your acquires was mapped to a memory slot which didn't match"
                              " the qubit index. I'm relabeling them to match.")

            # Get the label of all qubits that are measured with the qubit(s) in this instruction
            existing_qubits = {chan.index for chan in inst.acquires}
            all_qubits = []
            for sublist in meas_map:
                if existing_qubits.intersection(set(sublist)):
                    all_qubits.extend(sublist)
            # Replace the old acquire instruction by a new one explicitly acquiring all qubits in
            # the measurement group.
            for i in all_qubits:
                explicit_inst = Acquire(inst.duration, AcquireChannel(i),
                                        mem_slot=MemorySlot(i),
                                        kernel=inst.kernel,
                                        discriminator=inst.discriminator) << time
                if time not in acquire_map:
                    new_schedule |= explicit_inst
                    acquire_map = {time: {i}}
                elif i not in acquire_map[time]:
                    new_schedule |= explicit_inst
                    acquire_map[time].add(i)
        else:
            new_schedule |= inst << time

    return new_schedule


def pad(
    schedule: Schedule,
    channels: Optional[Iterable[Channel]] = None,
    until: Optional[int] = None,
    mutate: bool = False
) -> Schedule:
    """Pad the input Schedule with ``Delay``s on all unoccupied timeslots until
    ``schedule.duration`` or ``until`` if not ``None``.

    Args:
        schedule: Schedule to pad.
        channels: Channels to pad. Defaults to all channels in
            ``schedule`` if not provided. If the supplied channel is not a member
            of ``schedule`` it will be added.
        until: Time to pad until. Defaults to ``schedule.duration`` if not provided.
        mutate: Pad this schedule by mutating rather than returning a new schedule.
    Returns:
        The padded schedule.
    """
    until = until or schedule.duration

    channels = channels or schedule.channels
    occupied_channels = schedule.channels

    unoccupied_channels = set(channels) - set(occupied_channels)

    empty_timeslot_collection = schedule.timeslots.complement(until)

    for channel in channels:
        for timeslot in empty_timeslot_collection.ch_timeslots(channel):
            schedule = schedule.insert(timeslot.start,
                                       Delay(timeslot.duration)(timeslot.channel),
                                       mutate=mutate)

    for channel in unoccupied_channels:
        schedule = schedule.insert(0, Delay(until)(channel), mutate=mutate)

    return schedule


def push_append(
    this: List[ScheduleComponent],
    other: List[ScheduleComponent]
) -> Schedule:
        r"""Return a new schedule with `schedule` inserted at the maximum time over
        all channels shared between `self` and `schedule`.

       $t = \textrm{max}({x.stop\_time |x \in self.channels \cap schedule.channels})$

        Args:
            schedule: schedule to be appended
            buffer: Whether to obey buffer when appending
        """
        channels = list(set(this.channels) & set(other.channels))

        ch_slacks = [this.stop_time - this.ch_stop_time(channel) + other.ch_start_time(channel)
                     for channel in channels]

        if ch_slacks:
            slack_chan = channels[np.argmin(ch_slacks)]
            insert_time = this.ch_stop_time(slack_chan) - other.ch_start_time(slack_chan)
        else:
            insert_time = 0
        return this.insert(insert_time, other)


def left_align(
    *instructions: List[Union[Instruction, Schedule]]
) -> Schedule:
    """Align a list of pulse instructions on the left.

    Args:
        instructions: List of pulse instructions to align.

    Returns:
        pulse.Schedule
    """
    aligned = Schedule()
    for instruction in instructions:
        aligned = push_append(aligned, instruction)

    return aligned


def right_align(
    *instructions: List[ScheduleComponent]
) -> Schedule:
    """Align a list of pulse instructions on the right.

    Args:
        instructions: List of pulse instructions to align.

    Returns:
        pulse.Schedule
    """
    left_aligned = left_align(*instructions)
    max_duration = 0

    channel_durations = {}
    for channel in left_aligned.channels:
        channel_sched = left_aligned.filter(channels=[channel])
        channel_duration = channel_sched.duration-channel_sched.start_time
        channel_durations[channel] = channel_sched.duration
        max_duration = max(max_duration, channel_duration)

    aligned = Schedule()
    for instr_time, instruction in left_aligned.instructions:
        instr_max_dur = max(channel_durations[channel] for channel in
                            instruction.channels)
        instr_delayed_time = max_duration - instr_max_dur + instr_time
        aligned.insert(instr_delayed_time, instruction, mutate=True)

    return aligned


def align_in_sequence(
    *instructions: List[ScheduleComponent]
) -> Schedule:
    """Align a list of pulse instructions sequentially in time.
    Args:
        instructions: List of pulse instructions to align.
    Returns:
        A new pulse schedule with instructions`
    """
    aligned = Schedule()
    for instruction in instructions:
        aligned.insert(aligned.duration, instruction, mutate=True)
    return aligned


def left_barrier(
    *instructions: List[ScheduleComponent], channels=None
) -> Schedule:
    """Align on the left and create a barrier so that pulses cannot be inserted
        within this pulse interval.

    Args:
        instructions: List of pulse instructions to align.

    Returns:
        pulse.Schedule
    """
    aligned = left_align(*instructions)
    return pad(aligned, channels=channels)


def right_barrier(
    *instructions: List[ScheduleComponent], channels=None
) -> Schedule:
    """Align on the right and create a barrier so that pulses cannot be
        inserted within this pulse interval.

    Args:
        instructions: List of pulse instructions to align.

    Returns:
        pulse.Schedule
    """
    aligned = right_align(*instructions)
    return pad(aligned, channels=channels)
