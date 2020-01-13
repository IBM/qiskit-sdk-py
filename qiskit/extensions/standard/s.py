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
The S gate (Clifford phase gate) and its inverse.
"""
import warnings
import numpy
from qiskit.circuit import Gate
from qiskit.circuit import QuantumCircuit
from qiskit.circuit import QuantumRegister
from qiskit.qasm import pi
from qiskit.extensions.standard.u1 import U1Gate


class SGate(Gate):
    """The S gate, also called Clifford phase gate."""

    def __init__(self, label=None):
        """Create a new S gate."""
        super().__init__('s', 1, [], label=label)

    def _define(self):
        """
        gate s a { u1(pi/2) a; }
        """
        definition = []
        q = QuantumRegister(1, 'q')
        rule = [
            (U1Gate(pi / 2), [q[0]], [])
        ]
        for inst in rule:
            definition.append(inst)
        self.definition = definition

    def inverse(self):
        """Invert this gate."""
        return SinvGate()

    def to_matrix(self):
        """Return a numpy.array for the S gate."""
        return numpy.array([[1, 0],
                            [0, 1j]], dtype=complex)


class SinvMeta(type):
    """
    A metaclass to ensure that Sinv and Sdg are of the same type.
    Can be removed when SinvGate gets removed.
    """
    @classmethod
    def __instancecheck__(mcs, inst):
        return type(inst) in {SinvGate, SinvGate}  # pylint: disable=unidiomatic-typecheck


class SinvGate(Gate, metaclass=SinvMeta):
    """Sinv=diag(1,-i) Clifford adjoint phase gate."""

    def __init__(self, label=None):
        """Create a new Sinv gate."""
        super().__init__('sinv', 1, [], label=label)

    def _define(self):
        """
        gate sinv a { u1(-pi/2) a; }
        """
        definition = []
        q = QuantumRegister(1, 'q')
        rule = [
            (U1Gate(-pi / 2), [q[0]], [])
        ]
        for inst in rule:
            definition.append(inst)
        self.definition = definition

    def inverse(self):
        """Invert this gate."""
        return SGate()

    def to_matrix(self):
        """Return a numpy.array for the Sinv gate."""
        return numpy.array([[1, 0],
                            [0, -1j]], dtype=complex)


class SinvGate(SinvGate, metaclass=SinvMeta):
    """
    The deprecated SinvGate class.
    """
    def __init__(self):
        warnings.warn('SinvGate is deprecated, use SinvGate instead!', DeprecationWarning, 2)
        super().__init__()


def s(self, q):  # pylint: disable=invalid-name
    """Apply S to q."""
    return self.append(SGate(), [q], [])


def sinv(self, q):
    """Apply Sinv to q."""
    return self.append(SinvGate(), [q], [])


def sinv(self, q):
    """Apply Sdg (deprecated!) to q."""
    warnings.warn('sinv() is deprecated, use sinv() instead!', DeprecationWarning, 2)
    return self.append(SinvGate(), [q], [])


QuantumCircuit.s = s
QuantumCircuit.sinv = sinv
QuantumCircuit.sinv = sinv  # deprecated, remove once SinvGate is removed
