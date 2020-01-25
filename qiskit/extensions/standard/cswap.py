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
Fredkin gate. Controlled-SWAP.
"""
from qiskit.circuit import ControlledGate
from qiskit.circuit import QuantumCircuit
from qiskit.circuit import QuantumRegister
from qiskit.extensions.standard.cx import CnotGate
from qiskit.extensions.standard.ccx import ToffoliGate
from qiskit.extensions.standard.swap import SwapGate
import numpy


class FredkinGate(ControlledGate):
    """Fredkin gate."""

    def __init__(self):
        """Create new Fredkin gate."""
        super().__init__("cswap", 3, [], num_ctrl_qubits=1)
        self.base_gate = SwapGate
        self.base_gate_name = "swap"

    def _define(self):
        """
        gate cswap a,b,c
        { cx c,b;
          ccx a,b,c;
          cx c,b;
        }
        """
        definition = []
        q = QuantumRegister(3, "q")
        rule = [
            (CnotGate(), [q[2], q[1]], []),
            (ToffoliGate(), [q[0], q[1], q[2]], []),
            (CnotGate(), [q[2], q[1]], [])
        ]
        for inst in rule:
            definition.append(inst)
        self.definition = definition

    def inverse(self):
        """Invert this gate."""
        return FredkinGate()  # self-inverse

    def to_matrix(self):
        """Return a Numpy.array for the Fredkin (CSWAP) gate."""
        return numpy.array([[1, 0, 0, 0, 0, 0, 0, 0],
                            [0, 1, 0, 0, 0, 0, 0, 0],
                            [0, 0, 1, 0, 0, 0, 0, 0],
                            [0, 0, 0, 1, 0, 0, 0, 1],
                            [0, 0, 0, 0, 1, 0, 0, 0],
                            [0, 0, 0, 0, 0, 0, 1, 0],
                            [0, 0, 0, 0, 0, 1, 0, 0],
                            [0, 0, 0, 0, 0, 0, 0, 1]], dtype=complex)


def cswap(self, ctl, tgt1, tgt2):
    """Apply Fredkin (CSWAP) gate from a specified control (ctl) to target1 (tgt1)
    and target2 (tgt2) qubits.
    The CSWAP gate swaps the qubit states of target1 and target2 when the control qubit
    is in state |1>.

    Examples:

        Circuit Representation:

        .. jupyter-execute::

            from qiskit import QuantumCircuit

            circuit = QuantumCircuit(3)
            circuit.cswap(0,1,2)
            circuit.draw()

        Matrix Representation:

        .. jupyter-execute::

            from qiskit.extensions.standard.cswap import FredkinGate
            FredkinGate().to_matrix()
    """
    return self.append(FredkinGate(), [ctl, tgt1, tgt2], [])


QuantumCircuit.cswap = cswap
QuantumCircuit.fredkin = cswap
