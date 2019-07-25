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
controlled-Phase gate.
"""
import numpy

from qiskit.circuit import ControlledGate
from qiskit.circuit import QuantumCircuit
from qiskit.circuit import QuantumRegister
import qiskit.extensions.standard.h as h
import qiskit.extensions.standard.cx as cx


class CzGate(ControlledGate):
    """controlled-Z gate."""

    def __init__(self, label=None):
        """Create new CZ gate."""
        super().__init__("cz", 2, [], label=label, num_ctrl_qubits=1)

    def _define(self):
        """
        gate cz a,b { h b; cx a,b; h b; }
        """
        definition = []
        q = QuantumRegister(2, "q")
        rule = [
            (h.HGate(), [q[1]], []),
            (cx.CnotGate(), [q[0], q[1]], []),
            (h.HGate(), [q[1]], [])
        ]
        for inst in rule:
            definition.append(inst)
        self.definition = definition

    def inverse(self):
        """Invert this gate."""
        return CzGate()  # self-inverse

    def to_matrix(self):
        """Return a Numpy.array for the Cz gate."""
        return numpy.array([[1, 0, 0, 0],
                            [0, 1, 0, 0],
                            [0, 0, 1, 0],
                            [0, 0, 0, -1]], dtype=complex)


def cz(self, ctl, tgt):
    """Apply CZ to circuit."""
    return self.append(CzGate(), [ctl, tgt], [])


QuantumCircuit.cz = cz
