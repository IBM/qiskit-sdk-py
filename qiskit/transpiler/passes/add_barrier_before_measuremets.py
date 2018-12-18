# -*- coding: utf-8 -*-

# Copyright 2018, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.


"""
This pass adds a barrier before the measurements.
"""

from qiskit.extensions.standard.barrier import Barrier
from qiskit.transpiler import TransformationPass
from qiskit.dagcircuit import DAGCircuit


class AddBarrierBeforeMeasuremets(TransformationPass):
    """Adds a barrier before measurements."""

    def __init__(self):
        super().__init__()

    def run(self, dag):
        """Return a circuit with a barrier before last measurments."""
        last_measures = []
        for measure in dag.get_named_nodes('measure'):
            is_last_measurement = all([after_measure in dag.output_map.values() for after_measure in
                                       dag.multi_graph.successors(measure)])
            if is_last_measurement:
                last_measures.append(measure)

        if last_measures:
            # create a laywer with the barrier and the measurements in last_measures operation
            dag.add_basis_element('barrier', len(last_measures), 0, 0)
            barried_layer = DAGCircuit()
            last_measures_nodes = [dag.multi_graph.node[node]for node in last_measures]
            last_measures_qubits = [node['qargs'][0] for node in last_measures_nodes]

            # Add registers from the original dag.
            for qreg in dag.qregs.values():
                barried_layer.add_qreg(qreg)
            for creg in dag.cregs.values():
                barried_layer.add_creg(creg)

            # Add the barrier operation
            barried_layer.apply_operation_back(Barrier(qubits=last_measures_qubits))

            # Add the measurements to the behind the barrier
            for last_measures_node in last_measures_nodes:
                barried_layer.apply_operation_back(last_measures_node['op'])

            # Remove the measurments from the original dag
            for last_measure in last_measures:
                dag._remove_op_node(last_measure)

            # Extend the original dag with the barried layer
            dag.extend_back(barried_layer)
        return dag
