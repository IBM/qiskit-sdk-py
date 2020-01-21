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
Controlled-ry gate.
"""
from qiskit.circuit import ControlledGate
from qiskit.circuit import QuantumCircuit
from qiskit.circuit import QuantumRegister
from qiskit.extensions.standard.u1 import U3Gate
from qiskit.extensions.standard.cx import CXGate
from qiskit.extensions.standard.ry import RYGate


class CRYMeta(type):
    """A metaclass to ensure that CryGate and CRYGate are of the same type.

    Can be removed when CryGate gets removed.
    """
    @classmethod
    def __instancecheck__(mcs, inst):
        return type(inst) in {CRYGate, CryGate}  # pylint: disable=unidiomatic-typecheck


class CRYGate(ControlledGate, metaclass=CRYMeta):
    """The controlled-ry gate."""

    def __init__(self, theta):
        """Create new cry gate."""
        super().__init__('cry', 2, [theta], num_ctrl_qubits=1)
        self.base_gate = RYGate
        self.base_gate_name = 'ry'

    def _define(self):
        """
        gate cry(lambda) a,b
        { u3(lambda/2,0,0) b; cx a,b;
          u3(-lambda/2,0,0) b; cx a,b;
        }

        """
        definition = []
        q = QuantumRegister(2, 'q')
        rule = [
            (U3Gate(self.params[0] / 2, 0, 0), [q[1]], []),
            (CXGate(), [q[0], q[1]], []),
            (U3Gate(-self.params[0] / 2, 0, 0), [q[1]], []),
            (CXGate(), [q[0], q[1]], [])
        ]
        for inst in rule:
            definition.append(inst)
        self.definition = definition

    def inverse(self):
        """Invert this gate."""
        return CRYGate(-self.params[0])


class CryGate(CRYGate, metaclass=CRYMeta):
    """The deprecated CRYGate class."""

    def __init__(self, theta):
        import warnings
        warnings.warn('The class CryGate is deprecated as of 0.11.2, and '
                      'will be removed no earlier than 3 months after that release date. '
                      'You should use the class CRYGate instead.',
                      DeprecationWarning, stacklevel=2)
        super().__init__(theta)


def cry(self, theta, ctl, tgt):
    """Apply cry from ctl to tgt with angle theta."""
    return self.append(CRYGate(theta), [ctl, tgt], [])


QuantumCircuit.cry = cry
