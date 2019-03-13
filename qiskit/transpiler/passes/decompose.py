# -*- coding: utf-8 -*-

# Copyright 2018, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""Pass for one layer of decomposing the gates in a circuit."""

from qiskit.transpiler.basepasses import TransformationPass
from qiskit.dagcircuit import DAGCircuit


class Decompose(TransformationPass):
    """
    Expand a gate in a circuit using its decomposition rules.
    """

    def __init__(self, gate=None):
        """
        Args:
            gate (qiskit.circuit.gate.Gate): Gate to decompose.
        """
        super().__init__()
        self.gate = gate

    def run(self, dag):
        """Expand a given gate into its decomposition.

        Args:
            dag(DAGCircuit): input dag
        Returns:
            DAGCircuit: output dag where gate was expanded.
        """
        # Walk through the DAG and expand each non-basis node
        for node in dag.op_nodes(self.gate):
            # opaque or built-in gates are not decomposable
            if not current_node["op"].definition:
                continue
            # TODO: allow choosing among multiple decomposition rules
            rule = current_node["op"].definition
            # hacky way to build a dag on the same register as the rule is defined
            # TODO: need anonymous rules to address wires by index
            decomposition = DAGCircuit()
            decomposition.add_qreg(rule[0][1][0][0])
            for inst in rule:
                decomposition.apply_operation_back(*inst)
            dag.substitute_node_with_dag(node, decomposition)
        return dag
