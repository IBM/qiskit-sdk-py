# -*- coding: utf-8 -*-

# This code is part of Qiskit.
#
# (C) Copyright IBM 2017.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""
Controlled unitary gate.
"""

from qiskit.exceptions import QiskitError
from .instruction import Instruction
from .gate import Gate


class ControlledGate(Gate):
    """Controlled unitary gate."""

    def __init__(self,  name, num_qubits, params, label=None, num_ctrl_qubits=1,
                 definition=None):
        """Create a new gate.

        Args:
            name (str or None): if None, use 'c'+gate.name, otherwise use "name".
            label (str or None): if None, use gate label, otherwise use "label".
        """
        super().__init__(name, num_qubits, params, label=label)
        if num_ctrl_qubits < num_qubits:
            self.num_ctrl_qubits = num_ctrl_qubits
        else:
            raise QiskitError('number of control qubits must be less than the number of qubits')
        if definition:
            self.definition = definition

    def __eq__(self, other):
        if not isinstance(other, ControlledGate):
            return False
        else:
            try:
                return (other.num_ctrl_qubits == self.num_ctrl_qubits and
                        super().__eq__(other))
            except Exception as err:
                import ipdb;ipdb.set_trace()

    def add_control_qubit(self):
        """Add control qubit"""
        self.num_ctl_qubits += 1
        self.num_qubits += 1
        # self.name = 'c' + self.name
        
