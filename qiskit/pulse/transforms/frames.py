# This code is part of Qiskit.
#
# (C) Copyright IBM 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Basic rescheduling functions which take schedule or instructions and return new schedules."""


from typing import Dict

from qiskit.pulse.schedule import Schedule
from qiskit.pulse.transforms.resolved_frame import ResolvedFrame, ChannelTracker
from qiskit.pulse.library import Signal
from qiskit.pulse.exceptions import PulseError
from qiskit.pulse import channels as chans, instructions
from qiskit.pulse.frame import Frame



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
    sample_duration = None
    for frame_settings in frames_config.values():
        frame = ResolvedFrame(**frame_settings)
        frame.set_frame_instructions(schedule)
        resolved_frames[frame.index] = frame
        sample_duration = frame_settings['sample_duration']

    if sample_duration is None:
        raise PulseError('Frame configuration does not have a sample duration.')

    # Used to keep track of the frequency and phase of the channels
    channel_trackers = {}
    for ch in schedule.channels:
        if isinstance(ch, chans.PulseChannel):
            channel_trackers[ch] = ChannelTracker(ch, sample_duration)

    # Add the channels that the frames broadcast on.
    for frame in resolved_frames.values():
        for ch in frame.channels:
            if ch not in channel_trackers:
                channel_trackers[ch] = ChannelTracker(ch, sample_duration)

    sched = Schedule(name=schedule.name, metadata=schedule.metadata)

    for time, inst in schedule.instructions:
        if isinstance(inst, instructions.Play):
            chan = inst.channel

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
                # we set it now
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
        elif isinstance(inst, (instructions.SetFrequency, instructions.ShiftFrequency)):
            chan = inst.channel

            if issubclass(type(chan), chans.PulseChannel):
                sched.insert(time, type(inst)(inst.frequency, chan), inplace=True)

        elif isinstance(inst, (instructions.SetPhase, instructions.ShiftPhase)):
            chan = inst.channel

            if issubclass(type(chan), chans.PulseChannel):
                sched.insert(time, type(inst)(inst.phase, chan), inplace=True)

        if isinstance(inst, (instructions.Delay, instructions.Call,
                             instructions.Snapshot, instructions.Acquire,
                             instructions.Directive)):
            sched.insert(time, inst, inplace=True)

    return sched
