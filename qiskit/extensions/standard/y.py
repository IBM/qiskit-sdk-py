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
Pauli Y (bit-phase-flip) gate.
"""
import numpy
from qiskit.circuit import Gate
from qiskit.circuit import QuantumRegister
from qiskit.circuit import QuantumCircuit
from qiskit.qasm import pi
from qiskit.extensions.standard.u3 import U3Gate


class YGate(Gate):
    """Pauli Y (bit-phase-flip) gate."""

    def __init__(self, label=None):
        """Create new Y gate."""
        super().__init__("y", 1, [], label=label)

    def _define(self):
        definition = []
        q = QuantumRegister(1, "q")
        rule = [
            (U3Gate(pi, pi/2, pi/2), [q[0]], [])
        ]
        for inst in rule:
            definition.append(inst)
        self.definition = definition

    def inverse(self):
        """Invert this gate."""
        return YGate()  # self-inverse

    def to_matrix(self):
        """Return a Numpy.array for the Y gate."""
        return numpy.array([[0, -1j],
                            [1j, 0]], dtype=complex)


def y(self, q):
    """Apply Y gate to a specified qubit (q).
    A Y-gate implements a pi rotation of the qubit state vector about the
    y-axis of the Bloch sphere.
    It is also equivalent to the combined effect of X gate and Z gate.
    This gate is canonically used to rotate the qubit state from |0⟩ to i|1⟩, or vise versa.

    Examples:

        Circuit Representation:

        .. jupyter-execute::

            from qiskit import QuantumCircuit

            circuit = QuantumCircuit(1)
            circuit.y(0)
            circuit.draw()

        Matrix Representation:

        .. jupyter-execute::

            from qiskit.extensions.standard.y import YGate
            YGate().to_matrix()
    """
    return self.append(YGate(), [q], [])


QuantumCircuit.y = y
