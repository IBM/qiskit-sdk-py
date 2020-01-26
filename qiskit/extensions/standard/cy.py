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
controlled-Y gate.
"""
from qiskit.circuit import ControlledGate
from qiskit.circuit import QuantumCircuit
from qiskit.circuit import QuantumRegister
from qiskit.extensions.standard.y import YGate
from qiskit.extensions.standard.s import SGate
from qiskit.extensions.standard.s import SdgGate
from qiskit.extensions.standard.cx import CnotGate


class CyGate(ControlledGate):
    """controlled-Y gate."""

    def __init__(self):
        """Create new CY gate."""
        super().__init__("cy", 2, [], num_ctrl_qubits=1)
        self.base_gate = YGate
        self.base_gate_name = "y"

    def _define(self):
        """
        gate cy a,b { sdg b; cx a,b; s b; }
        """
        definition = []
        q = QuantumRegister(2, "q")
        rule = [
            (SdgGate(), [q[1]], []),
            (CnotGate(), [q[0], q[1]], []),
            (SGate(), [q[1]], [])
        ]
        for inst in rule:
            definition.append(inst)
        self.definition = definition

    def inverse(self):
        """Invert this gate."""
        return CyGate()  # self-inverse


def cy(self, ctl, tgt):  # pylint: disable=invalid-name
    """Apply cY gate from a specified control (ctl) to target (tgt) qubit.
    A cY gate implements a pi rotation of the qubit state vector about the y axis
    of the Bloch sphere when the control qubit is in state |1>.
    This gate is canonically used to implement a bit flip and phase flip on the qubit state
    from |0⟩ to i|1⟩, or from |1> to -i|0> when the control qubit is in state |1>.

    Examples:

        Circuit Representation:

        .. jupyter-execute::

            from qiskit import QuantumCircuit

            circuit = QuantumCircuit(2)
            circuit.cy(0,1)
            circuit.draw()
    """
    return self.append(CyGate(), [ctl, tgt], [])


QuantumCircuit.cy = cy
