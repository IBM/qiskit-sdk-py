# -*- coding: utf-8 -*-

# This code is part of Qiskit.
#
# (C) Copyright IBM 2020.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""
Set channel frequency.
"""
from typing import Optional

from ..channels import PulseChannel
from .instruction import Instruction


class SetFrequency(Instruction):
    """
    Set the channel frequency. This command operates on PulseChannels.
    A PulseChannel creates pulses of the form Re[exp(i 2pi f jdt + phase) d_j].
    F is the frequency of the channel. The command SetFrequency allows
    the user to set the value of f. All pulses that are played on a channel
    after SetFrequency has been called will have the corresponding frequency.

    The duration of SetFrequency is 0.
    """

    prefix = 'sf'

    def __init__(self, frequency: float,
                 channel: Optional[PulseChannel] = None,
                 name: Optional[str] = None):
        """Creates a new set channel frequency pulse.

        Args:
            frequency: New frequency of the channel in Hz.
            channel: The channel this instruction operates on.
            name: Name of this set channel frequency command.
        """
        self._frequency = float(frequency)
        super().__init__(0, channel, name=name)
        self._channel = channel

    @property
    def frequency(self):
        """New frequency."""
        return self._frequency

    @property
    def channel(self):
        """Return the :py:class:`~qiskit.pulse.channels.Channel` that this instruction is
        scheduled on"""
        return self._channel

    def __eq__(self, other: 'SetFrequency'):
        """
        Two set frequency instructions are the same if they have the same type and frequency.

        Args:
            other: Other SetFrequency.

        Returns:
            bool: Are self and other equal.
        """
        return super().__eq__(other) and (self.frequency == other.frequency)

    def __hash__(self):
        return hash((super().__hash__(), self.frequency))

    def __repr__(self):
        return '%s(%s, frequency=%.3f)' % (self.__class__.__name__, self.name, self.frequency)
