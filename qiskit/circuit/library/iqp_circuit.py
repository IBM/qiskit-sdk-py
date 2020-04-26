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

"""Instantaneous quantum polynomial circuit."""

from typing import Union, List

import numpy as np
from qiskit.circuit import QuantumCircuit
from qiskit.circuit.exceptions import CircuitError


class IQPCircuit(QuantumCircuit):
    """A quantum volume model circuit.

    The model circuits consists of a column of Hadamard gates,
    a column of powers of T gates,
    a sequence of powers of CS gates (up to (n**2-n)/2 of them),
    a final column of Hadamard gates, as introduced in [1].

    The powers of each T gate are given by the diagonal elements
    of the interactions matrix. The powers of the CS gates are
    given by the upper triangle of the interactions matrix.

    **References:**

    [1] M. J. Bremner et al. Average-case complexity versus approximate
    simulation of commuting quantum computations,
    Phys. Rev. Lett. 117, 080501 (2016).
    [`arXiv:1504.07999 <https://arxiv.org/abs/1504.07999>`_]
    """

    def __init__(self,
                 interactions: Union[List, np.array]) -> None:
        """Create IQP circuit.

         Args:
             interactions: input n-by-n symetric matrix.

        Raises:
            CircuitError: if the inputs is not as symetric matrix.

        The circuit prepares a IQP circuit with the given interaction
        matrix.

        Reference Circuit:
            .. jupyter-execute::
                :hide-code:

                from qiskit.circuit.library import IQPCircuit
                import qiskit.tools.jupyter
                A = [[6, 5, 3], [5, 4, 5], [3, 5, 1]]
                circuit = IQPCircuit(A)
                %circuit_library_info circuit.decompose()
        """
        num_qubits = len(interactions)
        inner = QuantumCircuit(num_qubits)
        interactions = np.array(interactions)
        if not np.allclose(interactions, interactions.transpose()):
            raise CircuitError("The interactions matrix is not symetric")

        a_str = np.array_str(interactions)
        a_str.replace('\n', ';')
        name = "iqp:" +  a_str.replace('\n', ';')
        super().__init__(num_qubits, name=name)

        inner.h(range(num_qubits))
        for i in range(num_qubits):
            for j in range(i+1, num_qubits):
                if interactions[i][j] % 4 != 0:
                    inner.cu1(interactions[i][j]*np.pi/2, i, j)

        for i in range(num_qubits):
            if interactions[i][i] % 8 != 0:
                inner.u1(interactions[i][i]*np.pi/8, i)

        inner.h(range(num_qubits))
        all_qubits = self.qubits # i dont like this line
        self.append(inner, all_qubits, label=name)
