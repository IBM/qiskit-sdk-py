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
Hadamard gate.
"""
import numpy

from qiskit.circuit import Gate
from qiskit.circuit import ControlledGate
from qiskit.circuit import QuantumCircuit
from qiskit.circuit import QuantumRegister
from qiskit.exceptions import QiskitError
from qiskit.qasm import pi
import qiskit.extensions.standard.u2 as u2
import qiskit.extensions.standard.ch as ch


class HGate(Gate):
    """Hadamard gate."""

    def __init__(self, label=None):
        """Create new Hadamard gate."""
        super().__init__("h", 1, [], label=label)

    def _define(self):
        """
        gate h a { u2(0,pi) a; }
        """
        definition = []
        q = QuantumRegister(1, "q")
        rule = [
            (u2.U2Gate(0, pi), [q[0]], [])
        ]
        for inst in rule:
            definition.append(inst)
        self.definition = definition

    def inverse(self):
        """Invert this gate."""
        return HGate()  # self-inverse

    def to_matrix(self):
        """Return a Numpy.array for the H gate."""
        return numpy.array([[1, 1],
                            [1, -1]], dtype=complex) / numpy.sqrt(2)

    def q_if(self, num_ctrl_qubits=1, label=None):
        """Return controlled version of gate.

        Args:
            num_ctrl_qubits (int): number of control qubits to add. Default 1.
            label (str): optional label for returned gate.

        Raise:
            QiskitError: unallowed num_ctrl_qubits specified.
        """
        if num_ctrl_qubits == 1:
            return ch.CHGate()
        elif isinstance(num_ctrl_qubits, int) and num_ctrl_qubits > 1:
            return ControlledGate('c{0:d}{1}'.format(num_ctrl_qubits, self.name),
                                  num_ctrl_qubits+1, self.params,
                                  num_ctrl_qubits=num_ctrl_qubits, label=label)
        else:
            raise QiskitError('Number of control qubits must be >=1')


def h(self, q):
    """Apply H to q."""
    return self.append(HGate(), [q], [])


QuantumCircuit.h = h
