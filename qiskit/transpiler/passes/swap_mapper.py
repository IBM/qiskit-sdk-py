# -*- coding: utf-8 -*-

# Copyright 2018, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

from qiskit import QuantumRegister
from qiskit.transpiler._basepasses import TransformationPass
from qiskit.dagcircuit import DAGCircuit

class SwapMapper(TransformationPass):

    def __init__(self, coupling_map, swap_basis_element='swap'):
        super().__init__()
        self.coupling_map = coupling_map
        self.swap_basis_element = swap_basis_element

    def run(self, dag):
        new_dag = DAGCircuit()
        for layer in dag.serial_layers():
            subdag = layer['graph']
            cxs = subdag.get_cnot_nodes()
            if not cxs:
                # Trivial layer, there is no entanglement in this layer, just leave it like this.
                new_dag.add_dag_at_the_end(subdag)
                continue
            for cx in subdag.get_cnot_nodes():
                qubit0 = cx['qargs'][0]
                qubit1 = cx['qargs'][1]
                if self.coupling_map.distance(qubit0,qubit1) == 1:
                    # The CXs are already together, no need to change anything.
                    new_dag.add_dag_at_the_end(subdag)
                    continue
                else:
                    path = self.coupling_map.shortest_path(qubit0,qubit1)
                    new_dag.add_basis_element(self.swap_basis_element, 2)
                    closest_qubit = path[1]['name']
                    farest_qubit = path[-1]['name']
                    dag.apply_operation_back(self.swap_basis_element, [closest_qubit, farest_qubit)

        return new_dag