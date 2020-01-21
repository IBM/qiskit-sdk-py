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
Controlled-rz gate.
"""
from qiskit.circuit import ControlledGate
from qiskit.circuit import QuantumCircuit
from qiskit.circuit import QuantumRegister
from qiskit.extensions.standard.u1 import U1Gate
from qiskit.extensions.standard.cx import CXGate
from qiskit.extensions.standard.rz import RZGate


class CRZMeta(type):
    """A metaclass to ensure that CrzGate and CRZGate are of the same type.

    Can be removed when CrzGate gets removed.
    """
    @classmethod
    def __instancecheck__(mcs, inst):
        return type(inst) in {CRZGate, CrzGate}  # pylint: disable=unidiomatic-typecheck


class CRZGate(ControlledGate, metaclass=CRZMeta):
    """The controlled-rz gate."""

    def __init__(self, theta):
        """Create new crz gate."""
        super().__init__('crz', 2, [theta], num_ctrl_qubits=1)
        self.base_gate = RZGate
        self.base_gate_name = 'rz'

    def _define(self):
        """
        gate crz(lambda) a,b
        { u1(lambda/2) b; cx a,b;
          u1(-lambda/2) b; cx a,b;
        }
        """
        definition = []
        q = QuantumRegister(2, 'q')
        rule = [
            (U1Gate(self.params[0] / 2), [q[1]], []),
            (CXGate(), [q[0], q[1]], []),
            (U1Gate(-self.params[0] / 2), [q[1]], []),
            (CXGate(), [q[0], q[1]], [])
        ]
        for inst in rule:
            definition.append(inst)
        self.definition = definition

    def inverse(self):
        """Invert this gate."""
        return CRZGate(-self.params[0])


class CrzGate(CRZGate, metaclass=CRZMeta):
    """The deprecated CRZGate class."""

    def __init__(self, theta):
        import warnings
        warnings.warn('The class CrzGate is deprecated as of 0.11.2, and '
                      'will be removed no earlier than 3 months after that release date. '
                      'You should use the class CRZGate instead.',
                      DeprecationWarning, stacklevel=2)
        super().__init__(theta)


def crz(self, theta, ctl, tgt):
    """Apply crz from ctl to tgt with angle theta."""
    return self.append(CRZGate(theta), [ctl, tgt], [])


QuantumCircuit.crz = crz
