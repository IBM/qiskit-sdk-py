# -*- coding: utf-8 -*-

# Copyright 2018 IBM RESEARCH. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =============================================================================

"""Pass for peep-hole cancellation of consecutive CX gates.
"""
from qiskit.transpiler._basepass import BasePass
from qiskit._dagcircuit import DAGCircuit


class CXCancellation(BasePass):
    """Cancel back-to-back 'cx' gates in dag."""

    def run(self, dag):
        """
        run one pass of cx cancellation on the circuit

        Args:
            dag (DAGCircuit): the directed acyclic graph to run on

        Returns:
            DAGCircuit: the directed acyclic graph after transformation
        """
        cx_runs = dag.collect_runs(["cx"])
        for cx_run in cx_runs:
            # Partition the cx_run into chunks with equal gate arguments
            partition = []
            chunk = []
            for i in range(len(cx_run) - 1):
                chunk.append(cx_run[i])
                qargs0 = dag.multi_graph.node[cx_run[i]]["qargs"]
                qargs1 = dag.multi_graph.node[cx_run[i + 1]]["qargs"]
                if qargs0 != qargs1:
                    partition.append(chunk)
                    chunk = []
            chunk.append(cx_run[-1])
            partition.append(chunk)
            # Simplify each chunk in the partition
            for chunk in partition:
                if len(chunk) % 2 == 0:
                    for n in chunk:
                        dag._remove_op_node(n)
                else:
                    for n in chunk[1:]:
                        dag._remove_op_node(n)
        return dag
