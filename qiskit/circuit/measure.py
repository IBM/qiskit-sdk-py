# -*- coding: utf-8 -*-

# Copyright 2017, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""
Quantum measurement in the computational basis.
"""
from qiskit.circuit.decorators import _2q_gate
from .instruction import Instruction
from .quantumcircuit import QuantumCircuit


class Measure(Instruction):
    """Quantum measurement in the computational basis."""

    def __init__(self, qubit, bit, circuit=None):
        """Create new measurement instruction."""
        super().__init__("measure", [], [qubit], [bit], circuit)

    def qasm(self):
        """Return OPENQASM string."""
        qubit = self.qargs[0]
        bit = self.cargs[0]
        return self._qasmif("measure %s[%d] -> %s[%d];" % (qubit[0].name,
                                                           qubit[1],
                                                           bit[0].name,
                                                           bit[1]))

    def reapply(self, circuit):
        """Reapply this gate to corresponding qubits."""
        self._modifiers(circuit.measure(self.qargs[0], self.cargs[0]))


@_2q_gate(broadcastable=[True, False])
def measure(self, qubit, cbit):
    """Measure quantum bit into classical bit (tuples).

    Args:
        qubit (QuantumRegister|list|tuple): quantum register
        cbit (ClassicalRegister|list|tuple): classical register

    Returns:
        qiskit.Instruction: the attached measure instruction.

    Raises:
        QiskitError: if qubit is not in this circuit or bad format;
            if cbit is not in this circuit or not creg.
    """
    self._check_qubit(qubit)
    self._check_creg(cbit[0])
    cbit[0].check_range(cbit[1])
    return self._attach(Measure(qubit, cbit, self))


QuantumCircuit.measure = measure
