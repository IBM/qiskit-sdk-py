# -*- coding: utf-8 -*-

# This code is part of Qiskit.
#
# (C) Copyright IBM 2020.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

# pylint: disable=no-member

"""Implementations of boolean logic quantum circuits."""

from typing import List, Optional

import numpy as np
from qiskit.circuit import QuantumRegister, QuantumCircuit
from qiskit.circuit.exceptions import CircuitError
from qiskit.extensions.standard import MCXGate


class Permutation(QuantumCircuit):
    """An n_qubit circuit that permutes qubits."""

    def __init__(self,
                 num_qubits: int,
                 pattern: Optional[List[int]] = None,
                 seed: Optional[int] = None,
                 ) -> QuantumCircuit:
        """Return an n_qubit permutation circuit implemented using SWAPs.

        Args:
            num_qubits: circuit width.
            pattern: permutation pattern. If None, permute randomly.
            seed: random seed in case a random permutation is requested.

        Returns:
            A permutation circuit.

        Raises:
            CircuitError: if permutation pattern is malformed.

        Reference Circuit:
            .. jupyter-execute::
                :hide-code:

                from qiskit.circuit.library import Permutation
                import qiskit.tools.jupyter
                circuit = Permutation(5, seed=42)
                %circuit_library_info circuit

        """
        super().__init__(num_qubits, name="permutation")

        if pattern is not None:
            if sorted(pattern) != list(range(num_qubits)):
                raise CircuitError("Permutation pattern must be some "
                                   "ordering of 0..num_qubits-1 in a list.")
            pattern = np.array(pattern)
        else:
            rng = np.random.RandomState(seed)
            pattern = np.arange(num_qubits)
            rng.shuffle(pattern)

        for i in range(num_qubits):
            if (pattern[i] != -1) and (pattern[i] != i):
                self.swap(i, int(pattern[i]))
                pattern[pattern[i]] = -1


class XOR(QuantumCircuit):
    """An n_qubit circuit for bitwise xor-ing the input with some integer ``amount``.

    The ``amount`` is xor-ed in bitstring form with the input.

    This circuit can also represent addition by ``amount`` over the finite field GF(2).
    """

    def __init__(self,
                 num_qubits: int,
                 amount: Optional[int] = None,
                 seed: Optional[int] = None,
                 ) -> QuantumCircuit:
        """Return a circuit implementing bitwise xor.

        Args:
            num_qubits: the width of circuit.
            amount: the xor amount in decimal form.
            seed: random seed in case a random xor is requested.

        Returns:
            A circuit for bitwise XOR.

        Raises:
            CircuitError: if the xor bitstring exceeds available qubits.

        Reference Circuit:
            .. jupyter-execute::
                :hide-code:

                from qiskit.circuit.library import XOR
                import qiskit.tools.jupyter
                circuit = XOR(5, seed=42)
                %circuit_library_info circuit
        """
        super().__init__(num_qubits, name="xor")

        if amount is not None:
            if len(bin(amount)[2:]) > num_qubits:
                raise CircuitError("Bits in 'amount' exceed circuit width")
        else:
            rng = np.random.RandomState(seed)
            amount = rng.randint(0, 2**num_qubits)

        for i in range(num_qubits):
            bit = amount & 1
            amount = amount >> 1
            if bit == 1:
                self.x(i)


class InnerProduct(QuantumCircuit):
    """An n_qubit circuit that computes the inner product of two registers."""

    def __init__(self, num_qubits: int) -> QuantumCircuit:
        """Return a circuit to compute the inner product of 2 n-qubit registers.

        This implementation uses CZ gates.

        Args:
            num_qubits: width of top and bottom registers (half total circuit width)

        Returns:
            A circuit computing inner product of two registers.

        Reference Circuit:
            .. jupyter-execute::
                :hide-code:

                from qiskit.circuit.library import InnerProduct
                import qiskit.tools.jupyter
                circuit = InnerProduct(5)
                %circuit_library_info circuit
        """
        qr_a = QuantumRegister(num_qubits)
        qr_b = QuantumRegister(num_qubits)
        super().__init__(qr_a, qr_b, name="inner_product")

        for i in range(num_qubits):
            self.cz(qr_a[i], qr_b[i])


class OR(QuantumCircuit):
    """A circuit implementing the logical OR operation on a number of qubits."""

    def __init__(self, num_variable_qubits: int, flags: Optional[List[int]] = None,
                 mcx_mode: str = 'noancilla') -> None:
        """Create a new logical OR circuit.

        Args:
            num_variable_qubits: The qubits of which the OR is computed. The result will be written
                into an additional result qubit.
            flags: A list of +1/0/-1 marking negations or omisiions of qubits.
            mcx_mode: The mode to be used to implement the multi-controlled X gate.
        """
        qr_variable = QuantumRegister(num_variable_qubits, name='variable')
        qr_result = QuantumRegister(1, name='result')

        super().__init__(qr_variable, qr_result, name='or')

        # determine the control qubits: all that have a nonzero flag
        flags = flags or [1] * num_variable_qubits
        control_qubits = [q for q, flag in zip(qr_variable, flags) if flag != 0]

        # determine the qubits that need to be flipped (if a flag is > 0)
        flip_qubits = [q for q, flag in zip(qr_variable, flags) if flag > 0]

        # determine the number of ancillas
        num_ancillas = MCXGate.get_num_ancilla_qubits(len(control_qubits), mode=mcx_mode)
        if num_ancillas > 0:
            qr_ancilla = QuantumRegister(num_ancillas, 'ancilla')
            self.add_register(qr_ancilla)
        else:
            qr_ancilla = []

        self.x(qr_result)
        if len(flip_qubits) > 0:
            self.x(flip_qubits)
        self.mcx(control_qubits, qr_result[:], qr_ancilla[:], mode=mcx_mode)
        if len(flip_qubits) > 0:
            self.x(flip_qubits)


class AND(QuantumCircuit):
    """A circuit implementing the logical OR operation on a number of qubits."""

    def __init__(self, num_variable_qubits: int, flags: Optional[List[int]] = None,
                 mcx_mode: str = 'noancilla') -> None:
        """Create a new logical OR circuit.

        Args:
            num_variable_qubits: The qubits of which the OR is computed. The result will be written
                into an additional result qubit.
            flags: A list of +1/0/-1 marking negations or omisiions of qubits.
            mcx_mode: The mode to be used to implement the multi-controlled X gate.
        """
        qr_variable = QuantumRegister(num_variable_qubits, name='variable')
        qr_result = QuantumRegister(1, name='result')

        super().__init__(qr_variable, qr_result, name='or')

        # determine the control qubits: all that have a nonzero flag
        flags = flags or [1] * num_variable_qubits
        control_qubits = [q for q, flag in zip(qr_variable, flags) if flag != 0]

        # determine the qubits that need to be flipped (if a flag is < 0)
        flip_qubits = [q for q, flag in zip(qr_variable, flags) if flag < 0]

        # determine the number of ancillas
        num_ancillas = MCXGate.get_num_ancilla_qubits(len(control_qubits), mode=mcx_mode)
        if num_ancillas > 0:
            qr_ancilla = QuantumRegister(num_ancillas, 'ancilla')
            self.add_register(qr_ancilla)
        else:
            qr_ancilla = []

        if len(flip_qubits) > 0:
            self.x(flip_qubits)
        self.mcx(control_qubits, qr_result[:], qr_ancilla[:], mode=mcx_mode)
        if len(flip_qubits) > 0:
            self.x(flip_qubits)
