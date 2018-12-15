""" Pass for constructing commutativity aware DAGCircuit from basic DAGCircuit. The generated DAGCircuit is not ready for simple scheduling.
"""

from qiskit.transpiler._basepasses import TransformationPass
from qiskit.transpiler.passes.commutation_analysis import CommutationAnalysis
from qiskit.transpiler import AnalysisPass
import numpy as np
import networkx as nx

class CommutationTransformation(TransformationPass):
    def __init__(self):
        super().__init__()
        self.requires.append(CommutationAnalysis())
        self.preserves.append(CommutationAnalysis())
        self.qreg_op = {}
        self.node_order = {}

    def run(self, dag):

        """
        Construct a new DAG that is commutativity aware. The new DAG is:
        - not friendly to simple scheduling(conflicts might arise), but leave more room for optimization. 
        - The depth() method will not be accurate before the final scheduling anymore.
        - Preserves the gate count but not edge count in the MultiDiGraph

        Args:
            dag (DAGCircuit): the directed acyclic graph
        Return: 
            DAGCircuit: Transformed DAG.
        """
        
        for wire in dag.wires:
            wire_name = "{0}[{1}]".format(str(wire[0].name), str(wire[1]))

            for c_set_ind, c_set in enumerate(self.property_set['commutation_set'][wire_name]):

                if dag.multi_graph.node[c_set[0]]['type'] == 'out':
                    continue
                
                for node1 in c_set:
                    for node2 in c_set:
                        if node1 != node2:
                            wire_to_save = ''
                            for edge in dag.multi_graph.edges([node1], data = True):
                                if edge[2]['name'] != wire_name and edge[1] == node2:
                                    wire_to_save = edge[2]['name']

                            while dag.multi_graph.has_edge(node1, node2):
                                dag.multi_graph.remove_edge(node1, node2)
                            
                            if wire_to_save != '':
                                dag.multi_graph.add_edge(node1, node2, name = wire_to_save)
                        
                    for next_node in self.property_set['commutation_set'][wire_name][c_set_ind + 1]:

                        nd = dag.multi_graph.node[node1]
                        next_nd = dag.multi_graph.node[next_node]

                        edge_on_wire = False 
                        for temp_edge in dag.multi_graph.edges([node1], data = True):
                            if temp_edge[1] == next_node and temp_edge[2]['name'] == wire_name:
                                edge_on_wire = True

                        if not edge_on_wire:
                            dag.multi_graph.add_edge(node1, next_node, name = wire_name)

        return dag 
