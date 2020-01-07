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
Diagonal single qubit gate.
"""
import numpy
from qiskit.circuit import Gate
from qiskit.circuit import QuantumCircuit
from qiskit.circuit import QuantumRegister
from qiskit.extensions.standard.u3 import U3Gate


class U1Gate(Gate):
    """Diagonal single-qubit gate."""

    def __init__(self, theta, label=None):
        """Create new diagonal single-qubit gate."""
        super().__init__("u1", 1, [theta], label=label)

    def _define(self):
        definition = []
        q = QuantumRegister(1, "q")
        rule = [
            (U3Gate(0, 0, self.params[0]), [q[0]], [])
        ]
        for inst in rule:
            definition.append(inst)
        self.definition = definition

    def inverse(self):
        """Invert this gate."""
        return U1Gate(-self.params[0])

    def to_matrix(self):
        """Return a Numpy.array for the U3 gate."""
        lam = self.params[0]
        lam = float(lam)
        return numpy.array([[1, 0], [0, numpy.exp(1j * lam)]], dtype=complex)


def u1(self, theta, q):  # pylint: disable=invalid-name
    """Apply U1 gate with angle theta to a specified qubit (q).
    The U1 gate corresponds to a rotation of theta radians from |+> about
    the z-axis on the Bloch sphere.

    Examples:

        Construct a circuit with U1 gate.

        .. jupyter-execute::

            from qiskit import QuantumCircuit

            circuit = QuantumCircuit(1)
            theta = numpy.pi/2
            circuit.ry(numpy.pi/2,0) # This brings the quantum state from |0> to |+>
            circuit.u1(theta,0)
            circuit.draw()

        Resulting Statevector:
        [ 0.707+0j, 0+0.707j ]
    """
    return self.append(U1Gate(theta), [q], [])


QuantumCircuit.u1 = u1
