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
controlled-H gate.
"""
from qiskit.circuit import CompositeGate
from qiskit.circuit import Gate
from qiskit.circuit import QuantumCircuit
from qiskit.circuit import QuantumRegister
from qiskit.circuit.decorators import _op_expand, _to_bits
from qiskit.extensions.standard.x import XGate
from qiskit.extensions.standard.h import HGate
from qiskit.extensions.standard.cx import CnotGate
from qiskit.extensions.standard.t import TGate
from qiskit.extensions.standard.s import SGate
from qiskit.extensions.standard.s import SdgGate


class CHGate(Gate):
    """controlled-H gate."""

    def __init__(self):
        """Create new CH gate."""
        super().__init__("ch", 2, [])

    def _define(self):
        """
        gate ch a,b {
        h b;
        sdg b;
        cx a,b;
        h b;
        t b;
        cx a,b;
        t b;
        h b;
        s b;
        x b;
        s a;}
        """
        definition = []
        q = QuantumRegister(2, "q")
        rule = [
            (HGate(), [q[1]], []),
            (SdgGate(), [q[1]], []),
            (CnotGate(), [q[0], q[1]], []),
            (HGate(), [q[1]], []),
            (TGate(), [q[1]], []),
            (CnotGate(), [q[0], q[1]], []),
            (TGate(), [q[1]], []),
            (HGate(), [q[1]], []),
            (SGate(), [q[1]], []),
            (XGate(), [q[1]], []),
            (SGate(), [q[0]], [])
        ]
        for inst in rule:
            definition.append(inst)
        self.definition = definition

    def inverse(self):
        """Invert this gate."""
        return CHGate()  # self-inverse


@_to_bits(2)
@_op_expand(2)
def ch(self, ctl, tgt):
    """Apply CH from ctl to tgt."""
    return self.append(CHGate(), [ctl, tgt], [])


QuantumCircuit.ch = ch
CompositeGate.ch = ch
