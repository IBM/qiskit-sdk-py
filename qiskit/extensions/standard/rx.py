# -*- coding: utf-8 -*-

# Copyright 2017, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

# pylint: disable=invalid-name

"""
Rotation around the x-axis.
"""
from qiskit import Gate
from qiskit import InstructionSet
from qiskit import QuantumCircuit
from qiskit import QuantumRegister
from qiskit.extensions.standard import header  # pylint: disable=unused-import


class RXGate(Gate):
    """rotation around the x-axis."""

    def __init__(self, theta, qubit, circ=None):
        """Create new rx single qubit gate."""
        super().__init__("rx", [theta], [qubit], circ)

    def inverse(self):
        """Invert this gate.

        rx(theta)^dagger = rx(-theta)
        """
        self.param[0] = -self.param[0]
        return self

    def reapply(self, circ):
        """Reapply this gate to corresponding qubits in circ."""
        self._modifiers(circ.rx(self.param[0], self.arg[0]))


def rx(self, theta, q):
    """Apply Rx to q."""
    if isinstance(q, QuantumRegister):
        instructions = InstructionSet()
        for j in range(q.size):
            instructions.add(self.rx(theta, (q, j)))
        return instructions

    self._check_qubit(q)
    return self._attach(RXGate(theta, q, self))


QuantumCircuit.rx = rx
