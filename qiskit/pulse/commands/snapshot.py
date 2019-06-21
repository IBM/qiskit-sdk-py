# -*- coding: utf-8 -*-

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

"""
Snapshot.
"""
from qiskit.pulse.channels import SnapshotChannel
from .instruction import Instruction
from .command import Command


class Snapshot(Command, Instruction):
    """Snapshot."""

    prefix = 'snap'

    def __init__(self, label: str, snapshot_type: str = 'statevector', name: str = None):
        """Create new snapshot command.

        Args:
            label (str): Snapshot label which is used to identify the snapshot in the output.
            snapshot_type (str): Type of snapshot, e.g., “state”: take snapshot of quantum state.
                The types of snapshots offered are defined in a separate specification
                document for simulators.
            name (str): Snapshot name which defaults to label, but can be different than label.
        """
        self._type = snapshot_type
        self._channel = SnapshotChannel()
        Command.__init__(self, duration=0)
        self._label = Snapshot.create_name(label)

        if name is not None:
            self._name = Snapshot.create_name(name)
        else:
            self._name = self._label

        Instruction.__init__(self, self, self._channel, name=self.name)
        self._buffer = 0

    @property
    def label(self) -> str:
        """Label of snapshot."""
        return self._label

    @property
    def type(self) -> str:
        """Type of snapshot."""
        return self._type

    def __eq__(self, other):
        """Two Snapshots are the same if they are of the same type
        and have the same label, type, and name.

        Args:
            other (Snapshot): other Snapshot,

        Returns:
            bool: are self and other equal.
        """
        if (type(self) is type(other) and
                self.label == other.label and
                self.type == other.type and
                self.name == other.name):
            return True
        return False

    # pylint: disable=arguments-differ
    def to_instruction(self):
        return self
    # pylint: enable=arguments-differ

    def __repr__(self):
        if self.label == self.name:
            return '%s(%s, %s) -> %s' % (self.__class__.__name__, self.label,
                                         self.type, self.channels)
        else:
            return '%s(%s, %s, %s) -> %s' % (self.__class__.__name__, self.label,
                                             self.type, self.name, self.channels)
