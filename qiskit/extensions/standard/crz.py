# -*- coding: utf-8 -*-

# Copyright 2017, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""
controlled-rz gate.
"""
from qiskit.circuit import CompositeGate
from qiskit.circuit import Gate
from qiskit.circuit import QuantumCircuit
from qiskit.circuit import QuantumRegister
from qiskit.circuit.decorators import _op_expand
from qiskit.dagcircuit import DAGCircuit
from qiskit.extensions.standard.u1 import U1Gate
from qiskit.extensions.standard.cx import CnotGate


class CrzGate(Gate):
    """controlled-rz gate."""

    def __init__(self, theta, ctl, tgt, circ=None):
        """Create new crz gate."""
        super().__init__("crz", [theta], [ctl, tgt], circ)

    def _define_decompositions(self):
        """
        gate crz(lambda) a,b
        { u1(lambda/2) b; cx a,b;
          u1(-lambda/2) b; cx a,b;
        }
        """
        decomposition = DAGCircuit()
        q = QuantumRegister(2, "q")
        decomposition.add_qreg(q)
        rule = [
            U1Gate(self.params[0]/2, q[1]),
            CnotGate(q[0], q[1]),
            U1Gate(-self.params[0]/2, q[1]),
            CnotGate(q[0], q[1])
        ]
        for inst in rule:
            decomposition.apply_operation_back(inst)
        self._decompositions = [decomposition]

    def inverse(self):
        """Invert this gate."""
        self.params[0] = -self.params[0]
        self._decompositions = None
        return self

    def reapply(self, circ):
        """Reapply this gate to corresponding qubits in circ."""
        self._modifiers(circ.crz(self.params[0], self.qargs[0], self.qargs[1]))


@_op_expand(2)
def crz(self, theta, ctl, tgt):
    """Apply crz from ctl to tgt with angle theta."""
    return self._attach(CrzGate(theta, ctl, tgt, self))


QuantumCircuit.crz = crz
CompositeGate.crz = crz
