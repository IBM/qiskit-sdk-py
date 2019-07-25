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

# pylint: disable=invalid-name
"""
Two-pulse single-qubit gate.
"""
import numpy
from qiskit.circuit import Gate
from qiskit.circuit import QuantumCircuit
import qiskit.extensions.standard.cu3 as cu3
from qiskit.exceptions import QiskitError


class U3Gate(Gate):
    """Two-pulse single-qubit gate."""

    def __init__(self, theta, phi, lam, label=None):
        """Create new two-pulse single qubit gate."""
        super().__init__("u3", 1, [theta, phi, lam], label=label)

    def inverse(self):
        """Invert this gate.

        u3(theta, phi, lamb)^dagger = u3(-theta, -lam, -phi)
        """
        return U3Gate(-self.params[0], -self.params[2], -self.params[1])

    def to_matrix(self):
        """Return a Numpy.array for the U3 gate."""
        theta, phi, lam = self.params
        theta, phi, lam = float(theta), float(phi), float(lam)
        return numpy.array(
            [[
                numpy.cos(theta / 2),
                -numpy.exp(1j * lam) * numpy.sin(theta / 2)
            ],
             [
                 numpy.exp(1j * phi) * numpy.sin(theta / 2),
                 numpy.exp(1j * (phi + lam)) * numpy.cos(theta / 2)
             ]],
            dtype=complex)

    def q_if(self, num_ctrl_qubits=1, label=None):
        """Return controlled version of gate.

        Args:
            num_ctrl_qubits (int): number of control qubits to add. Default 1.
            label (str): optional label for returned gate.

        Raise:
            QiskitError: unallowed num_ctrl_qubits specified.
        """
        if num_ctrl_qubits == 1:
            return cu3.Cu3Gate(*self.params)
        elif isinstance(num_ctrl_qubits, int) and num_ctrl_qubits > 1:
            return ControlledGate('c{0:d}{1}'.format(num_ctrl_qubits, self.name),
                                  num_ctrl_qubits+1, self.params,
                                  num_ctrl_qubits=num_ctrl_qubits, label=label)
        else:
            raise QiskitError('Number of control qubits must be >=1')
        

def u3(self, theta, phi, lam, q):
    """Apply u3 to q."""
    return self.append(U3Gate(theta, phi, lam), [q], [])


QuantumCircuit.u3 = u3
