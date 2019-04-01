# -*- coding: utf-8 -*-

# Copyright 2018, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.


"""
This pass adds a barrier before the set of final measurements. Measurements
are considered final if they are followed by no other operations (aside from
other measurements or barriers.)

"""

from qiskit.extensions.standard.barrier import Barrier
from qiskit.transpiler.basepasses import TransformationPass
from qiskit.dagcircuit import DAGCircuit
from qiskit.transpiler.passes import MergeAdjacentBarriers


class BarrierBeforeFinalMeasurements(TransformationPass):
    """Adds a barrier before final measurements."""

    def run(self, dag):
        """Return a circuit with a barrier before last measurements."""

        # Collect DAG nodes which are followed only by barriers or other measures.
        final_op_types = ['measure', 'barrier']
        final_ops = []
        for candidate_node in dag.named_nodes(*final_op_types):
            is_final_op = True

            for _, child_successors in dag.bfs_successors(candidate_node):

                if any(suc.type == 'op' and suc.name not in final_op_types
                       for suc in child_successors):
                    is_final_op = False
                    break

            if is_final_op:
                final_ops.append(candidate_node)

        if not final_ops:
            return dag

        # Create a layer with the barrier and add registers from the original dag.
        barrier_layer = DAGCircuit()
        for qreg in dag.qregs.values():
            barrier_layer.add_qreg(qreg)
        for creg in dag.cregs.values():
            barrier_layer.add_creg(creg)

        final_qubits = set(final_op.qargs[0]
                           for final_op in final_ops)

        barrier_layer.apply_operation_back(Barrier(qubits=final_qubits))

        # Preserve order of final ops collected earlier from the original DAG.
        ordered_final_nodes = [node for node in dag.nodes_in_topological_order()
                               if node in set(final_ops)]

        # Move final ops to the new layer and append the new layer to the DAG.
        for final_node in ordered_final_nodes:
            barrier_layer.apply_operation_back(final_node.op)

        for final_op in final_ops:
            dag._remove_op_node(final_op)

        dag.extend_back(barrier_layer)

        # Merge the new barrier into any other barriers
        adjacent_pass = MergeAdjacentBarriers()
        return adjacent_pass.run(dag)
