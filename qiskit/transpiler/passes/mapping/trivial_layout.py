# -*- coding: utf-8 -*-

# This code is part of Qiskit.
#
# (C) Copyright IBM 2017, 2018.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""A pass for choosing a Layout of a circuit onto a Coupling graph, using a simple
round-robin order.

This pass associates a physical qubit (int) to each virtual qubit
of the circuit (Qubit) in increasing order.
"""

from qiskit.transpiler.layout import Layout
from qiskit.transpiler.basepasses import TransformationPass
from qiskit.transpiler.exceptions import TranspilerError


class TrivialLayout(TransformationPass):
    """
    Chooses a Layout by assigning n circuit qubits to device qubits 0, .., n-1.

    Does not assume any ancilla.
    """

    def __init__(self, coupling_map):
        """
        Choose a TrivialLayout.

        Args:
            coupling_map (Coupling): directed graph representing a coupling map.

        Raises:
            TranspilerError: if invalid options
        """
        super().__init__()
        self.coupling_map = coupling_map

    def run(self, dag):
        """
        Pick a layout by assigning n circuit qubits to device qubits 0, .., n-1.

        Args:
            dag (DAGCircuit): DAG to find layout for.

        Raises:
            TranspilerError: if dag wider than self.coupling_map

        Returns:
            DAGCircuit: DAG with the layout.
        """
        num_dag_qubits = sum([qreg.size for qreg in dag.qregs.values()])
        if num_dag_qubits > self.coupling_map.size():
            raise TranspilerError('Number of qubits greater than device.')
        dag.layout = Layout.generate_trivial_layout(*dag.qregs.values())
        return dag
