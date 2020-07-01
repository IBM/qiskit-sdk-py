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

# pylint: disable=no-member

"""Phase estimation circuit."""

from typing import Optional

from qiskit.circuit import QuantumCircuit, QuantumRegister

from .basis_change import QFT


class PhaseEstimation(QuantumCircuit):
    r"""Phase Estimation circuit.

    In the Quantum Phase Estimation (QPE) algorithm [1, 2, 3], the Phase Estimation circuit is used
    to estimate the phase :math:`\phi` of an eigenvalue :math:`e^{i\phi}` of a unitary operator
    :math:`U`, provided with the corresponding eigenstate :math:`|psi\rangle`.
    That is

    .. math::

        U|\psi\rangle = e^{i\phi} |\psi\rangle

    This estimation (and thereby this circuit) is a central routine to several well-known
    algorithms, such as Shor's algorithm or Quantum Amplitude Estimation.

    **References:**

    [1]: Kitaev, A. Y. (1995). Quantum measurements and the Abelian Stabilizer Problem. 1–22.
        `quant-ph/9511026 <http://arxiv.org/abs/quant-ph/9511026>`_

    [2]: Michael A. Nielsen and Isaac L. Chuang. 2011.
         Quantum Computation and Quantum Information: 10th Anniversary Edition (10th ed.).
         Cambridge University Press, New York, NY, USA.

    [3]: Qiskit
        `textbook <https://qiskit.org/textbook/ch-algorithms/quantum-phase-estimation.html>`_

    """

    def __init__(self,
                 num_evaluation_qubits: int,
                 unitary: QuantumCircuit,
                 iqft: Optional[QuantumCircuit] = None,
                 name: str = 'QPE') -> None:
        """
        Args:
            num_evaluation_qubits: The number of evaluation qubits.
            unitary: The unitary operation :math:`U` which will be repeated and controlled.
            iqft: A inverse Quantum Fourier Transform, per default
                :class:`~qiskit.circuit.library.QFT` is used.
            name: The name of the circuit.

        Reference Circuit:
            .. jupyter-execute::
                :hide-code:

                from qiskit.circuit.library import PhaseEstimation
                import qiskit.tools.jupyter
                unitary = QuantumCircuit(2)
                unitary.x(0)
                unitary.y(1)
                circuit = PhaseEstimation(3, unitary)
                %circuit_library_info circuit
        """
        qr_eval = QuantumRegister(num_evaluation_qubits, 'eval')
        qr_state = QuantumRegister(unitary.num_qubits, 'q')
        super().__init__(qr_eval, qr_state, name=name)

        if iqft is None:
            iqft = QFT(num_evaluation_qubits, inverse=True)

        self.h(qr_eval)  # hadamards on evaluation qubits

        for j in range(num_evaluation_qubits):  # controlled powers
            self.append(unitary.repeat(2**j).control(), [j] + qr_state[:])

        self.append(iqft, qr_eval[:])  # final QFT
