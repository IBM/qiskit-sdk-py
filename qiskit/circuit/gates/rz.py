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

"""Rotation around the z-axis."""

from ..gate import Gate
from ..controlledgate import ControlledGate
from ..quantumregister import QuantumRegister


class RZGate(Gate):
    """The rotation around the z-axis."""

    def __init__(self, phi):
        """Create new RZ single qubit gate."""
        super().__init__('rz', 1, [phi])

    def _define(self):
        """
        gate rz(phi) a { u1(phi) a; }
        """
        from .u1 import U1Gate
        definition = []
        q = QuantumRegister(1, 'q')
        rule = [
            (U1Gate(self.params[0]), [q[0]], [])
        ]
        for inst in rule:
            definition.append(inst)
        self.definition = definition

    def control(self, num_ctrl_qubits=1, label=None, ctrl_state=None):
        """Controlled version of this gate.

        Args:
            num_ctrl_qubits (int): number of control qubits.
            label (str or None): An optional label for the gate [Default: None]
            ctrl_state (int or str or None): control state expressed as integer,
                string (e.g. '110'), or None. If None, use all 1s.

        Returns:
            ControlledGate: controlled version of this gate.
        """
        if ctrl_state is None:
            if num_ctrl_qubits == 1:
                return CRZGate(self.params[0])
        return super().control(num_ctrl_qubits=num_ctrl_qubits, label=label,
                               ctrl_state=ctrl_state)

    def inverse(self):
        """Invert this gate.

        rz(phi)^dagger = rz(-phi)
        """
        return RZGate(-self.params[0])


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
        self.base_gate = RZGate(theta)

    def _define(self):
        """
        gate crz(lambda) a,b
        { u1(lambda/2) b; cx a,b;
          u1(-lambda/2) b; cx a,b;
        }
        """
        from .u1 import U1Gate
        from .x import CXGate
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
        warnings.warn('The class CrzGate is deprecated as of 0.14.0, and '
                      'will be removed no earlier than 3 months after that release date. '
                      'You should use the class CRZGate instead.',
                      DeprecationWarning, stacklevel=2)
        super().__init__(theta)
