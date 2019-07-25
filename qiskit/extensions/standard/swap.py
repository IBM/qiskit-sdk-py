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
SWAP gate.
"""

import numpy

from qiskit.circuit import Gate
from qiskit.circuit import QuantumCircuit
from qiskit.circuit import QuantumRegister
import qiskit.extensions.standard.cx as cx
import qiskit.extensions.standard.cswap as cswap


class SwapGate(Gate):
    """SWAP gate."""

    def __init__(self):
        """Create new SWAP gate."""
        super().__init__("swap", 2, [])

    def _define(self):
        """
        gate swap a,b { cx a,b; cx b,a; cx a,b; }
        """
        definition = []
        q = QuantumRegister(2, "q")
        rule = [
            (cx.CnotGate(), [q[0], q[1]], []),
            (cx.CnotGate(), [q[1], q[0]], []),
            (cx.CnotGate(), [q[0], q[1]], [])
        ]
        for inst in rule:
            definition.append(inst)
        self.definition = definition

    def inverse(self):
        """Invert this gate."""
        return SwapGate()  # self-inverse

    def to_matrix(self):
        """Return a Numpy.array for the Swap gate."""
        return numpy.array([[1, 0, 0, 0],
                            [0, 0, 1, 0],
                            [0, 1, 0, 0],
                            [0, 0, 0, 1]], dtype=complex)

    def q_if(self, num_ctrl_qubits=1, label=None):
        """Return controlled version of gate.

        Args:
            num_ctrl_qubits (int): number of control qubits to add. Default 1.
            label (str): optional label for returned gate.

        Returns:
            ControlledGate: controlled version of this gate.
        """
        if num_ctrl_qubits == 1:
            return cswap.FredkinGate()
        else:
            return super().q_if(num_ctrl_qubits=num_ctrl_qubits, label=label)

def swap(self, qubit1, qubit2):
    """Apply SWAP from qubit1 to qubit2."""
    return self.append(SwapGate(), [qubit1, qubit2], [])


QuantumCircuit.swap = swap
