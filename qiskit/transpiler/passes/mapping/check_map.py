# -*- coding: utf-8 -*-

# Copyright 2018, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""
This pass checks if a DAG is mapped to a coupling map.

It checks that all 2-qubit interactions are laid out to be physically close.
"""

from qiskit.transpiler._basepasses import AnalysisPass
from qiskit.mapper import Layout
from qiskit.extensions.standard.swap import SwapGate


class CheckMap(AnalysisPass):
    """
    Checks if a DAGCircuit is mapped to `coupling_map` setting `requires_swap` in
    the property set as False if mapped. True otherwise.
    """

    def __init__(self, coupling_map, initial_layout=None):
        """
        Checks if a DAGCircuit is mapped to `coupling_map`.
        Args:
            coupling_map (CouplingMap): Directed graph represented a coupling map.
            initial_layout (Layout): The initial layout of the DAG to analyze.
        """
        super().__init__()
        self.layout = initial_layout
        self.coupling_map = coupling_map

    def run(self, dag):
        """
        If `dag` is mapped to `coupling_map`, the property
        `requires_swap` is set to False (or to True otherwise).

        Args:
            dag (DAGCircuit): DAG to map.
        """
        if self.layout is None:
            if self.property_set["layout"]:
                self.layout = self.property_set["layout"]
            else:
                self.layout = Layout.generate_trivial_layout(*dag.qregs.values())

        self.property_set['requires_swap'] = False

        for gate in dag.get_2q_nodes():
            physical_q0 = self.layout[gate['qargs'][0]]
            physical_q1 = self.layout[gate['qargs'][1]]

            if self.coupling_map.distance(physical_q0, physical_q1) != 1:
                self.property_set['requires_swap'] = True
                return
