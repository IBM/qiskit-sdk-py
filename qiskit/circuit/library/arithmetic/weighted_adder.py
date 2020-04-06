# -*- coding: utf-8 -*-

# This code is part of Qiskit.
#
# (C) Copyright IBM 2017, 2020.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Compute the weighted sum of qubit states."""

from typing import List, Optional
import numpy as np

from qiskit.circuit import QuantumCircuit, QuantumRegister


class WeightedAdder(QuantumCircuit):
    r"""A circuit to compute the weighted sum of qubit registers.

    Given :math:`n` qubits :math:`q_0, \ldots, q_{n-1}` and non-negative integer weights
    :math:`\lambda_0, \ldots, \lambda_{n-1}`, this circuit performs the operation

    .. math::

        |q_0 \ldots q_{n-1}\rangle |0\rangle_s
        \mapsto |q_0 \ldots q_{n-1}\rangle |\sum_{j=0}^{n-1} \lambda_j q_j\rangle_s

    where :math:`s` is the number of sum qubits required.
    This can be computed as

    .. math::

        s = 1 + \left\lfloor \log_2\left( \sum_{j=0}^{n-1} \lambda_j \right) \right\rfloor

    or :math:`s = 1` if the sum of the weights is 0 (then the expression in the logarithm is
    invalid).

    For qubits in a circuit diagram, the first weight applies to the upper-most qubit.
    For an example where the state of 4 qubits is added into a sum register, the circuit can
    be schematically drawn as

    .. parsed-literal::

                   ┌────────┐
          state_0: ┤0       ├ \ state_0 * weights[0]
                   │        │ |
          state_1: ┤1       ├ | + state_1 * weights[1]
                   │        │ |
          state_2: ┤2       ├ | + state_2 * weights[2]
                   │        │ |
          state_3: ┤3       ├ / + state_3 * weights[3]
                   │        │
            sum_0: ┤4       ├ \
                   │  Adder │ |
            sum_1: ┤5       ├ | = sum_0 * 2^0 + sum_1 * 2^1 + sum_2 * 2^2
                   │        │ |
            sum_2: ┤6       ├ /
                   │        │
          carry_0: ┤7       ├
                   │        │
          carry_1: ┤8       ├
                   │        │
        control_0: ┤9       ├
                   └────────┘
    """

    def __init__(self,
                 num_state_qubits: Optional[int] = None,
                 weights: Optional[List[int]] = None,
                 name: str = 'adder') -> None:
        """Computes the weighted sum controlled by state qubits.

        Args:
            num_state_qubits: The number of state qubits.
            weights: List of weights, one for each state qubit. If none are provided they
                default to 1 for every qubit.
            name: The name of the circuit.
        """
        super().__init__(name=name)

        self._weights = None
        self._num_state_qubits = None

        self.weights = weights
        self.num_state_qubits = num_state_qubits

    @property
    def num_sum_qubits(self) -> int:
        """The number of sum qubits in the circuit.

        Returns:
            The number of qubits needed to represent the weighted sum of the qubits.
        """
        if sum(self.weights) > 0:
            return int(np.floor(np.log2(sum(self.weights))) + 1)
        return 1

    @property
    def weights(self) -> List[int]:
        """The weights for the qubit states.

        Returns:
            The weight for the qubit states.
        """
        if self._weights:
            return self._weights
        if self.num_state_qubits:
            return [1] * self.num_state_qubits
        return None

    @weights.setter
    def weights(self, weights: List[int]) -> None:
        """Set the weights for summing the qubit states.

        Args:
            weights: The new weights.

        Raises:
            ValueError: If not all weights are close to an integer.
        """
        if weights:
            for i, weight in enumerate(weights):
                if not np.isclose(weight, np.round(weight)):
                    raise ValueError('Non-integer weights are not supported!')
                weights[i] = np.round(weight)

        self._weights = weights
        self._data = None
        self._reset_registers()

    @property
    def num_state_qubits(self) -> int:
        """The number of qubits to be summed.

        Returns:
            The number of state qubits.
        """
        return self._num_state_qubits

    @num_state_qubits.setter
    def num_state_qubits(self, num_state_qubits: int) -> None:
        """Set the number of state qubits.

        Args:
            num_state_qubits: The new number of state qubits.
        """
        if self._num_state_qubits is None or num_state_qubits != self._num_state_qubits:
            self._data = None
            self._num_state_qubits = num_state_qubits
            self._reset_registers()

    def _reset_registers(self):
        if self.num_state_qubits:
            qr_state = QuantumRegister(self.num_state_qubits, name='state')
            qr_sum = QuantumRegister(self.num_sum_qubits, name='sum')
            self.qregs = [qr_state, qr_sum]
            if self.num_carry_qubits > 0:
                qr_carry = QuantumRegister(self.num_carry_qubits, name='carry')
                self.qregs += [qr_carry]

            if self.num_control_qubits > 0:
                qr_control = QuantumRegister(self.num_control_qubits, name='control')
                self.qregs += [qr_control]
        else:
            self.qregs = []

    @property
    def num_carry_qubits(self) -> int:
        """The number of carry qubits required to compute the sum.

        Note that this is not necessarily equal to the number of ancilla qubits, these can
        be queried using ``num_ancilla_qubits``.

        Returns:
            The number of carry qubits required to compute the sum.
        """
        return self.num_sum_qubits - 1

    @property
    def num_control_qubits(self) -> int:
        """The number of additional control qubits required.

        Note that the total number of ancilla qubits can be obtained by calling the
        method ``num_ancilla_qubits``.

        Returns:
            The number of additional control qubits required (0 or 1).
        """
        return int(self.num_sum_qubits > 2)

    @property
    def num_ancilla_qubits(self) -> int:
        """The number of ancilla qubits required to implement the weighted sum.

        Returns:
            The number of ancilla qubits in the circuit.
        """
        return self.num_carry_qubits + self.num_control_qubits

    @property
    def data(self):
        if self._data is None:
            self._build()
        return super().data

    def _configuration_is_valid(self, raise_on_failure=True):
        valid = True
        if self._num_state_qubits is None:
            valid = False
            if raise_on_failure:
                raise AttributeError('The number of state qubits has not been set.')

        if self._num_state_qubits != len(self.weights):
            valid = False
            if raise_on_failure:
                raise ValueError('Mismatching number of state qubits and weights.')

        return valid

    def _build(self):
        if self._data:
            return

        _ = self._configuration_is_valid()

        self._data = []

        num_result_qubits = self.num_state_qubits + self.num_sum_qubits

        qr_state = self.qubits[:self.num_state_qubits]
        qr_sum = self.qubits[self.num_state_qubits:num_result_qubits]
        qr_carry = self.qubits[num_result_qubits:num_result_qubits + self.num_carry_qubits]
        qr_control = self.qubits[num_result_qubits + self.num_carry_qubits:]

        # loop over state qubits and corresponding weights
        for i, weight in enumerate(self.weights):
            # only act if non-trivial weight
            if np.isclose(weight, 0):
                continue

            # get state control qubit
            q_state = qr_state[i]

            # get bit representation of current weight
            weight_binary = '{0:b}'.format(int(weight)).rjust(self.num_sum_qubits, '0')[::-1]

            # loop over bits of current weight and add them to sum and carry registers
            for j, bit in enumerate(weight_binary):
                if bit == '1':
                    if self.num_sum_qubits == 1:
                        self.cx(q_state, qr_sum[j])
                    elif j == 0:
                        # compute (q_sum[0] + 1) into (q_sum[0], q_carry[0])
                        # - controlled by q_state[i]
                        self.ccx(q_state, qr_sum[j], qr_carry[j])
                        self.cx(q_state, qr_sum[j])
                    elif j == self.num_sum_qubits - 1:
                        # compute (q_sum[j] + q_carry[j-1] + 1) into (q_sum[j])
                        # - controlled by q_state[i] / last qubit,
                        # no carry needed by construction
                        self.cx(q_state, qr_sum[j])
                        self.ccx(q_state, qr_carry[j - 1], qr_sum[j])
                    else:
                        # compute (q_sum[j] + q_carry[j-1] + 1) into (q_sum[j], q_carry[j])
                        # - controlled by q_state[i]
                        self.x(qr_sum[j])
                        self.x(qr_carry[j - 1])
                        self.mct([q_state, qr_sum[j], qr_carry[j - 1]], qr_carry[j], qr_control)
                        self.cx(q_state, qr_carry[j])
                        self.x(qr_sum[j])
                        self.x(qr_carry[j - 1])
                        self.cx(q_state, qr_sum[j])
                        self.ccx(q_state, qr_carry[j - 1], qr_sum[j])
                else:
                    if self.num_sum_qubits == 1:
                        pass  # nothing to do, since nothing to add
                    elif j == 0:
                        pass  # nothing to do, since nothing to add
                    elif j == self.num_sum_qubits-1:
                        # compute (q_sum[j] + q_carry[j-1]) into (q_sum[j])
                        # - controlled by q_state[i] / last qubit,
                        # no carry needed by construction
                        self.ccx(q_state, qr_carry[j - 1], qr_sum[j])
                    else:
                        # compute (q_sum[j] + q_carry[j-1]) into (q_sum[j], q_carry[j])
                        # - controlled by q_state[i]
                        self.mct([q_state, qr_sum[j], qr_carry[j - 1]], qr_carry[j], qr_control)
                        self.ccx(q_state, qr_carry[j - 1], qr_sum[j])

            # uncompute carry qubits
            for j in reversed(range(len(weight_binary))):
                bit = weight_binary[j]
                if bit == '1':
                    if self.num_sum_qubits == 1:
                        pass
                    elif j == 0:
                        self.x(qr_sum[j])
                        self.ccx(q_state, qr_sum[j], qr_carry[j])
                        self.x(qr_sum[j])
                    elif j == self.num_sum_qubits - 1:
                        pass
                    else:
                        self.x(qr_carry[j - 1])
                        self.mct([q_state, qr_sum[j], qr_carry[j - 1]], qr_carry[j], qr_control)
                        self.cx(q_state, qr_carry[j])
                        self.x(qr_carry[j - 1])
                else:
                    if self.num_sum_qubits == 1:
                        pass
                    elif j == 0:
                        pass
                    elif j == self.num_sum_qubits - 1:
                        pass
                    else:
                        # compute (q_sum[j] + q_carry[j-1]) into (q_sum[j], q_carry[j])
                        # - controlled by q_state[i]
                        self.x(qr_sum[j])
                        self.mct([q_state, qr_sum[j], qr_carry[j - 1]], qr_carry[j], qr_control)
                        self.x(qr_sum[j])
