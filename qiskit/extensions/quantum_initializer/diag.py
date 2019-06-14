# -*- coding: utf-8 -*-

# Copyright 2019, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

# The structure of the code is based on Emanuel Malvetti's semester thesis at ETH in 2018,
# which was supervised by Raban Iten and Prof. Renato Renner.

"""
Decomposes a diagonal matrix into elementary gates using the method described in Theorem 7 in
"Synthesis of Quantum Logic Circuits" by Shende et al. (https://arxiv.org/pdf/quant-ph/0406176.pdf).
"""
import cmath
import math

import numpy as np

from qiskit.circuit import Gate
from qiskit.circuit.quantumcircuit import QuantumCircuit, QuantumRegister
from qiskit.exceptions import QiskitError

_EPS = 1e-10  # global variable used to chop very small numbers to zero


class DiagGate(Gate):
    """
    diag =  list of the 2^k diagonal entries (for a diagonal gate on k qubits). Must contain at
    least two entries.
    """

    def __init__(self, diag):
        """Check types"""
        # Check if diag has type "list"
        if not type(diag) == list:
            raise QiskitError("The diagonal entries are not provided in a list.")

        """Check input form"""
        # Check if the right number of diagonal entries is provided and if the diagonal entries
        # have absolute value one.
        num_action_qubits = math.log2(len(diag))
        if num_action_qubits < 1 or not num_action_qubits.is_integer():
            raise QiskitError("The number of diagonal entries is not a positive power of 2.")
        for z in diag:
            try:
                complex(z)
            except TypeError:
                raise QiskitError("Not all of the diagonal entries can be converted to "
                                  "complex numbers.")
            if not np.abs(z) - 1 < _EPS:
                raise QiskitError("A diagonal entry has not absolute value one.")

        # Create new gate.
        super().__init__("diag", int(num_action_qubits), diag)

    def _define(self):
        diag_circuit = self._dec_diag()
        gate = diag_circuit.to_instruction()
        q = QuantumRegister(self.num_qubits)
        diag_circuit = QuantumCircuit(q)
        diag_circuit.append(gate, q[:])
        self.definition = diag_circuit.data

    def _dec_diag(self):
        """
        Call to create a circuit implementing the diagonal gate.
        """
        q = QuantumRegister(self.num_qubits)
        circuit = QuantumCircuit(q)
        # Since the diagonal is a unitary, all its entries have absolute value one and the diagonal
        # is fully specified by the phases of its entries
        diag_phases = [cmath.phase(z) for z in self.params]
        n = len(self.params)
        while n >= 2:
            angles_rz = []
            for i in range(0, n, 2):
                diag_phases[i // 2], rz_angle = _extract_rz(diag_phases[i], diag_phases[i + 1])
                angles_rz.append(rz_angle)
            num_act_qubits = int(np.log2(n))
            contr_qubits = q[self.num_qubits - num_act_qubits + 1:self.num_qubits]
            target_qubit = q[self.num_qubits - num_act_qubits]
            circuit.ucz(angles_rz, contr_qubits, target_qubit)
            n //= 2
        return circuit


# extract a Rz rotation (angle given by first output) such that exp(j*phase)*Rz(z_angle)
# is equal to the diagonal matrix with entires exp(1j*ph1) and exp(1j*ph2)
def _extract_rz(phi1, phi2):
    phase = (phi1 + phi2) / 2.0
    z_angle = phi2 - phi1
    return phase, z_angle


"""
Attach a diagonal gate to a circuit. The decomposition is based on Theorem 7 given in
"Synthesis of Quantum Logic Circuits" by Shende et al. (https://arxiv.org/pdf/quant-ph/0406176.pdf).

    Args:
        diag (list[number]): list of the 2^k diagonal entries (for a diagonal gate on k qubits).
            Must contain at least two entries.
        q (QautnumRegister|list[(QuantumRegister,int)]): list of k qubits the diagonal is acting on
            (the order of the qubits specifies the computational basis in which the diagonal gate is
             provided: the first element in diag acts on the state where all the qubits in q are in
             the state 0, the second entry acts on the state where all the qubits q[1],...,q[k-1]
             are in the state zero and q[0] is in the state 1, and so on.

    Returns:
        QuantumCircuit: the diagonal gate is attached to the circuit.

    Raises:
        QiskitError: if the list of the diagonal entries or the qubit list is in bad format;
            if the number of diagonal entries is not 2^k, where k denotes the number of qubits
"""


def diag(self, diag, q):
    if isinstance(q, QuantumRegister):
        q = q[:]
    # Check if q has type "list"
    if not type(q) == list:
        raise QiskitError("The qubits must be provided as a list "
                          "(also if there is only one qubit).")
    # Check if diag has type "list"
    if not type(diag) == list:
        raise QiskitError("The diagonal entries are not provided in a list.")
    num_action_qubits = math.log2(len(diag))
    if not len(q) == num_action_qubits:
        raise QiskitError("The number of diagonal entries does not correspond to"
                          " the number of qubits.")
    return self.append(DiagGate(diag), q)


QuantumCircuit.diag = diag
