# -*- coding: utf-8 -*-

# Copyright 2018, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""Pass for merging/canceling phase-shift gates like u1(theta), T-gates, S-gates and Z-gates
"""
import numpy as np
import qiskit
from qiskit import QuantumCircuit, ClassicalRegister, QuantumRegister
from qiskit.transpiler.basepasses import TransformationPass
import copy
import sys
np.set_printoptions(threshold=sys.maxsize)
import warnings
warnings.filterwarnings('ignore')

class OptimizePhaseShiftGates(TransformationPass):
    """merge/cancel phase-shift gates in dag."""

    def run(self, dag):
        """
        Run one pass of phase-shift gate optimization and cx cancellation
        on the circuit. The function looks for the circuit configuration
        with the lowest number of gates and circuit depth

        Args:
            dag (DAGCircuit): the directed acyclic graph to run on.
        Returns:
            DAGCircuit: Transformed DAG.
        """

        n = dag.width()  # number of qubits in the circuit
        T_counter = {}  # Counts the cumulative phase of T-gates and other z-rotation gates
        T_position_counter = {}  # Keeps track of the locations of T-gates and other z-rot. gates
        state_tracker = np.zeros((dag.width(), dag.size())).astype('int')
        for i in range(dag.width()):
            state_tracker[i][i] = 1 # initial state
        k = dag.width()  # number of initial variables
        for e in dag.topological_nodes():
            if e.data_dict['type'] == 'op':
                if e.data_dict['name'] == 'cx':
                    state_tracker[e.data_dict['qargs'][1][1]] ^= state_tracker[e.data_dict['qargs'][0][1]]
                elif e.data_dict['name'] in ['t', 'tdg', 's', 'sdg', 'z']:
                    phase_T_gate_equivalent = {'t': 1, 'tdg': 7, 's': 2, 'sdg': 6, 'z': 4}[e.data_dict['name']]
                    if str(state_tracker[e.data_dict['qargs'][0][1]]) in T_counter:
                        T_counter[str(state_tracker[e.data_dict['qargs'][0][1]])] += phase_T_gate_equivalent
                        T_position_counter[str(state_tracker[e.data_dict['qargs'][0][1]])].append(e._node_id)
                    else:
                        T_counter[str(state_tracker[e.data_dict['qargs'][0][1]])] = phase_T_gate_equivalent
                        T_position_counter[str(state_tracker[e.data_dict['qargs'][0][1]])] = [e._node_id]
                elif e.data_dict['name'] == 'u1':
                    if str(state_tracker[e.data_dict['qargs'][0][1]]) in T_counter:
                        T_counter[str(state_tracker[e.data_dict['qargs'][0][1]])] += e.data_dict['op'].params[0] * 4/np.pi
                        T_position_counter[str(state_tracker[e.data_dict['qargs'][0][1]])].append(e._node_id)
                    else:
                        T_counter[str(state_tracker[e.data_dict['qargs'][0][1]])] = e.data_dict['op'].params[0] * 4/np.pi
                        T_position_counter[str(state_tracker[e.data_dict['qargs'][0][1]])] = [e._node_id]
                else:
                    state_tracker[e.data_dict['qargs'][0][1]] = np.zeros(dag.size())
                    state_tracker[e.data_dict['qargs'][0][1]][k] = 1
                    k += 1
        circuit_length_min = len(dag.multi_graph.nodes) + 1
        circuit_depth_min = dag.depth() + 1
        for key in T_counter:
            if T_counter[key] % 8 == 0:
                for i in T_position_counter[key]:
                    dag.remove_op_node(i)  # Remove all the nodes that cancelled out
            else:
                original_dag = copy.deepcopy(dag)
                for final_gate_position in range(len(T_position_counter[key])):
                    dag = copy.deepcopy(original_dag)
                    k = 0
                    for i in T_position_counter[key]:
                        if k == final_gate_position:
                            p = QuantumRegister(1, 'p')
                            repl = QuantumCircuit(p)
                            if T_counter[key] % 8 == 1:
                                repl.t(p[0])
                            elif T_counter[key] % 8 == 2:
                                repl.s(p[0])
                            elif T_counter[key] % 8 == 4:
                                repl.z(p[0])
                            elif T_counter[key] % 8 == 6:
                                repl.sdg(p[0])
                            elif T_counter[key] % 8 == 7:
                                repl.tdg(p[0])
                            else:
                                repl.u1((T_counter[key] % 8) * np.pi / 4, p[0])
                            dag_repl = qiskit.converters.circuit_to_dag(repl)
                            dag.substitute_node_with_dag(dag._id_to_node[i], dag_repl)
                        else:
                            dag.remove_op_node(i)
                        k += 1
                    circuit_length = len(dag.multi_graph.nodes)
                    circuit_depth = dag.depth()
                    dag = qiskit.transpiler.passes.cx_cancellation.CXCancellation.run(dag, dag)
                    if (circuit_length < circuit_length_min) or (circuit_length == circuit_length_min and circuit_depth < circuit_depth_min):
                        circuit_length_min = circuit_length
                        circuit_depth_min = circuit_depth
                        optimal_dag = copy.deepcopy(dag)
                dag = optimal_dag
        return dag
