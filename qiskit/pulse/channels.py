# This code is part of Qiskit.
#
# (C) Copyright IBM 2017, 2019.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""This module defines Pulse Channels. Channels include:

  - transmit channels, which should subclass ``PulseChannel``
  - receive channels, such as ``AcquireChannel``
  - non-signal "channels" such as ``SnapshotChannel``, ``MemorySlot`` and ``RegisterChannel``.

Novel channel types can often utilize the ``ControlChannel``, but if this is not sufficient, new
channel types can be created. Then, they must be supported in the PulseQobj schema and the
assembler.
"""
from abc import ABCMeta
from typing import Any, Set, List, Union, Dict

import numpy as np

from qiskit.circuit import Parameter
from qiskit.circuit.parameterexpression import ParameterExpression, ParameterValueType
from qiskit.pulse.exceptions import PulseError


class Channel(metaclass=ABCMeta):
    """Base class of channels. Channels provide a Qiskit-side label for typical quantum control
    hardware signal channels. The final label -> physical channel mapping is the responsibility
    of the hardware backend. For instance, ``DriveChannel(0)`` holds instructions which the backend
    should map to the signal line driving gate operations on the qubit labeled (indexed) 0.

    When serialized channels are identified by their serialized name ``<prefix><index>``.
    The type of the channel is interpreted from the prefix,
    and the index often (but not always) maps to the qubit index.
    All concrete channel classes must have a ``prefix`` class attribute
    (and instances of that class have an index attribute). Base classes which have
    ``prefix`` set to ``None`` are prevented from being instantiated.

    To implement a new channel inherit from :class:`Channel` and provide a unique string identifier
    for the ``prefix`` class attribute.
    """

    prefix = None  # type: Optional[str]
    """A shorthand string prefix for characterizing the channel type."""

    # pylint: disable=unused-argument
    def __new__(cls, *args, **kwargs):
        if cls.prefix is None:
            raise NotImplementedError(
                "Cannot instantiate abstract channel. "
                "See Channel documentation for more information."
            )

        return super(Channel, cls).__new__(cls)

    def __init__(self, index: int):
        """Channel class.

        Args:
            index: Index of channel.
        """
        self._validate_index(index)
        self._index = index
        self._hash = None
        self._parameters = set()
        if isinstance(index, ParameterExpression):
            self._parameters = index.parameters

    @property
    def index(self) -> int:
        """Return the index of this channel. The index is a label for a control signal line
        typically mapped trivially to a qubit index. For instance, ``DriveChannel(0)`` labels
        the signal line driving the qubit labeled with index 0.
        """
        return self._index

    def _validate_index(self, index: Any) -> None:
        """Raise a PulseError if the channel index is invalid, namely, if it's not a positive
        integer.

        Raises:
            PulseError: If ``index`` is not a nonnegative integer.
        """
        if isinstance(index, ParameterExpression) and index.parameters:
            # Parameters are unbound
            return
        elif isinstance(index, ParameterExpression):
            index = float(index)
            if index.is_integer():
                index = int(index)

        if not isinstance(index, (int, np.integer)) and index < 0:
            raise PulseError('Channel index must be a nonnegative integer')

    @property
    def parameters(self) -> Set:
        """Parameters which determine the channel index."""
        return self._parameters

    def is_parameterized(self) -> bool:
        """Return True iff the channel is parameterized."""
        return bool(self.parameters)

    def assign(self, parameter: Parameter, value: ParameterValueType) -> 'Channel':
        """Return a new channel with the input Parameter assigned to value.

        Args:
            parameter: A parameter in this expression whose value will be updated.
            value: The new value to bind to.

        Returns:
            A new channel with updated parameters.

        Raises:
            PulseError: If the parameter is not present in the channel.
        """
        if parameter not in self.parameters:
            raise PulseError('Cannot bind parameters ({}) not present in the channel.'
                             ''.format(parameter))

        new_index = self.index.assign(parameter, value)
        if not new_index.parameters:
            self._validate_index(new_index)
            new_index = int(new_index)

        return type(self)(new_index)

    @property
    def name(self) -> str:
        """Return the shorthand alias for this channel, which is based on its type and index."""
        return '{}{}'.format(self.__class__.prefix, self._index)

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, self._index)

    def __eq__(self, other: 'Channel') -> bool:
        """Return True iff self and other are equal, specifically, iff they have the same type
        and the same index.

        Args:
            other: The channel to compare to this channel.

        Returns:
            True iff equal.
        """
        return type(self) is type(other) and self._index == other._index

    def __hash__(self):
        if self._hash is None:
            self._hash = hash((type(self), self._index))
        return self._hash


class PulseChannel(Channel, metaclass=ABCMeta):
    """Base class of transmit Channels. Pulses can be played on these channels."""
    pass


class DriveChannel(PulseChannel):
    """Drive channels transmit signals to qubits which enact gate operations."""
    prefix = 'd'


class MeasureChannel(PulseChannel):
    """Measure channels transmit measurement stimulus pulses for readout."""
    prefix = 'm'


class ControlChannel(PulseChannel):
    """Control channels provide supplementary control over the qubit to the drive channel.
    These are often associated with multi-qubit gate operations. They may not map trivially
    to a particular qubit index.
    """
    prefix = 'u'


class Frame(PulseChannel):
    """Channel to manage frames."""
    prefix = 'f'

    def __init__(self, index: Union[int, Parameter], channels: List[Channel]):
        """
        Args:
            index: The index of the frame.
            channels: List of channels tied together by this frame.

        Raises:
            PulseError: if any of the channels is a Frame.
        """
        super().__init__(index)

        for ch in channels:
            if isinstance(ch, Frame):
                raise PulseError('Cannot add Frame to Frame channels..')

        self._parameters = set()
        if isinstance(index, ParameterExpression):
            self._parameters.update(index.parameters)

        self._channels = set(channels)
        for ch in self._channels:
            self._parameters.update(ch.parameters)

    @property
    def channels(self):
        """Returns the channels tied together by this frame."""
        return self._channels

    def assign(self, parameter: Parameter, value: ParameterValueType) -> 'Channel':
        """
        Override the base class's assign method to handle any links between the
        parameter of the frame and the parameters of the sub-channels.

        Args:
            parameter:
            value:
        """
        return self.assign_parameters({parameter: value})

    def assign_parameters(self,
                          value_dict: Dict[ParameterExpression, ParameterValueType]) -> 'Frame':
        """
        Assign the value of the parameters.

        Args:
            value_dict: A mapping from Parameters to either numeric values or another
                Parameter expression.
        """
        assigned_sub_channels = self._assign_sub_channels(value_dict)

        new_index = None
        if isinstance(self.index, ParameterExpression):
            for param, value in value_dict.items():
                if param in self.index.parameters:
                    new_index = self.index.assign(param, value)
                    if not new_index.parameters:
                        self._validate_index(new_index)
                        new_index = int(new_index)

        if new_index is not None:
            return type(self)(new_index, assigned_sub_channels)

        return type(self)(self.index, assigned_sub_channels)

    def __repr__(self):
        sub_str = '['+', '.join([ch.__repr__() for ch in self._channels]) + ']'
        return f'{self.__class__.__name__}({self._index}, '+sub_str+')'

    def _assign_sub_channels(self, value_dict: Dict[ParameterExpression,
                                                    ParameterValueType]) -> List['Channel']:
        """
        Args:
            value_dict:

        Returns:
             Frame: A Frame in which the parameter has been assigned.
        """
        sub_channels = []
        for ch in self._channels:
            if isinstance(ch.index, ParameterExpression):
                for param, value in value_dict.items():
                    if param in ch.parameters:
                        ch = ch.assign(param, value)

            sub_channels.append(ch)

        return sub_channels


class AcquireChannel(Channel):
    """Acquire channels are used to collect data."""
    prefix = 'a'


class SnapshotChannel(Channel):
    """Snapshot channels are used to specify instructions for simulators."""
    prefix = 's'

    def __init__(self):
        """Create new snapshot channel."""
        super().__init__(0)


class MemorySlot(Channel):
    """Memory slot channels represent classical memory storage."""
    prefix = 'm'


class RegisterSlot(Channel):
    """Classical resister slot channels represent classical registers (low-latency classical
    memory).
    """
    prefix = 'c'
