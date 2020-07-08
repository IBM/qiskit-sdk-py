# -*- coding: utf-8 -*-

# This code is part of Qiskit.
#
# (C) Copyright IBM 2017, 2019.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Collect sequences of uninterrupted gates acting on 2 qubits."""

from qiskit.transpiler.basepasses import AnalysisPass
from qiskit.circuit import Gate


class CollectMultiQBlocks(AnalysisPass):
    """Collect sequences of uninterrupted gates acting on 2 qubits.

    Traverse the DAG and find blocks of gates that act consecutively on
    groups of qubits. Write the blocks to propert_set as a list of blocks
    of the form:
        [[g0, g1, g2], [g4, g5]]

    """

    def __init__(self, max_block_size=2):
        super().__init__()
        self.parent = {} # parent array for the union
        self.bit_groups = {} # current groups of bits stored at top of trees
        self.gate_groups = {} # current gate lists for the groups
        self.max_block_size = max_block_size

    def find_set(self, index):
        """ DSU function for finding root of set of items
        If my parent is myself, I am the root. Otherwise we recursively
        find the root for my parent. After that, we assign my parent to be
        my root, saving recursion in the future.
        """

        if index not in self.parent:
            self.parent[index] = index
            self.bit_groups[index] = [index]
            self.gate_groups[index] = []
        if self.parent[index] == index:
            return index
        self.parent[index] = self.find_set(self.parent[index])
        return self.parent[index]

    def union_set(self, set1, set2):
        """ DSU function for unioning two sets together
        Find the roots of each set. Then assign one to have the other
        as its parent, thus liking the sets.
        Merges smaller set into larger set in order to have better runtime
        """

        set1 = self.find_set(set1)
        set2 = self.find_set(set2)
        if set1 == set2:
            return
        if len(self.gate_groups[set1]) < len(self.gate_groups[set2]):
            set1, set2 = set2, set1
        self.parent[set2] = set1
        self.gate_groups[set1].extend(self.gate_groups[set2])
        self.bit_groups[set1].extend(self.bit_groups[set2])
        self.gate_groups[set2].clear()
        self.bit_groups[set2].clear()

    def run(self, dag):
        """Run the Collect2qBlocks pass on `dag`.

        The blocks contain "op" nodes in topological sort order
        such that all gates in a block act on the same pair of
        qubits and are adjacent in the circuit. the blocks are built
        by examining predecessors and successors of "cx" gates in
        the circuit. u1, u2, u3, cx, id gates will be included.

        After the execution, ``property_set['block_list']`` is set to
        a list of tuples of "op"a node labels.
        """

        self.parent = {} #reset all variables on run
        self.bit_groups = {}
        self.gate_groups = {}

        block_list = []

        def collect_key(x):
            """ special key function for topological ordering
            heuristic for this is to push all gates involving measurement
            or barriers, etc. as far back as possible (because they force
            blocks to end). After that, we process gates in order of lowest
            number of qubits acted on to largest number of qubits acted on
            because these have less chance of increasing the size of blocks
            """
            if x.type != "op":
                return "c"
            if isinstance(x.op, Gate):
                if x.op.is_parameterized():
                    return "b"
                return "a" + chr(ord('a') + len(x.qargs))
            return "c"

        op_nodes = dag.topological_op_nodes(key=collect_key)

        for nd in op_nodes:
            can_process = True
            makes_too_big = False

            # check if the node is a gate and if it is parameterized
            if nd.condition is not None:
                can_process = False
            if nd.op.is_parameterized():
                can_process = False
            if not isinstance(nd.op, Gate):
                can_process = False

            cur_qubits = {bit.index for bit in nd.qargs}

            if can_process:
                # if the gate is valid, check if grouping up the bits
                # in the gate would fit within our desired max size
                c_tops = set()
                for bit in cur_qubits:
                    c_tops.add(self.find_set(bit))
                tot_size = 0
                for group in c_tops:
                    tot_size += len(self.bit_groups[group])
                if tot_size > self.max_block_size:
                    makes_too_big = True

            if not can_process:
                # resolve the case where we cannot process this node
                for bit in cur_qubits:
                    # create a gate out of me
                    bit = self.find_set(bit)
                    if len(self.gate_groups[bit]) == 0:
                        continue
                    block_list.append(self.gate_groups[bit][:])
                    cur_set = set(self.bit_groups[bit])
                    for v in cur_set:
                        # reset this bit
                        self.parent[v] = v
                        self.bit_groups[v] = [v]
                        self.gate_groups[v] = []

            if makes_too_big:
                # adding in all of the new qubits would make the group too big
                # we must block off sub portions of the groups until the new
                # group would no longer be too big
                savings = {}
                groups_seen = set()
                tot_size = 0
                for bit in cur_qubits:
                    top = self.find_set(bit)
                    if top in groups_seen:
                        savings[top] = savings[top] - 1
                    else:
                        groups_seen.add(top)
                        savings[top] = len(self.bit_groups[top]) - 1
                        tot_size += len(self.bit_groups[top])
                slist = []
                for item in groups_seen:
                    slist.append((savings[item], item))
                slist.sort(reverse=True)
                savings_need = tot_size - self.max_block_size
                for item in slist:
                    # remove groups until the size created would be acceptable
                    # start with blocking out the group that would decrease
                    # the new size the most
                    if savings_need > 0:
                        savings_need = savings_need - item[0]
                        if len(self.gate_groups[item[1]]) >= 1:
                            block_list.append(self.gate_groups[item[1]][:])
                        cur_set = set(self.bit_groups[item[1]])
                        for v in cur_set:
                            self.parent[v] = v
                            self.bit_groups[v] = [v]
                            self.gate_groups[v] = []

            if can_process:
                # if the operation is a gate, either skip it if it is too large
                # or group up all of the qubits involved in the gate
                if len(cur_qubits) > self.max_block_size:
                    continue # unable to be part of a group
                prev = -1
                for bit in cur_qubits:
                    if prev != -1:
                        self.union_set(prev, bit)
                    prev = bit
                self.gate_groups[self.find_set(prev)].append(nd)
        # need to add in all groups that exist at the end!!!!
        for index in self.parent:
            if self.parent[index] == index and len(self.gate_groups[index]) != 0:
                block_list.append(self.gate_groups[index][:])

        self.property_set['block_list'] = block_list

        return dag
