# -*- coding: utf-8 -*-

# Copyright 2018, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

# pylint: disable=unused-import, invalid-name

"""Test Qiskit's inverse gate operation."""

import os
import tempfile
import unittest
import numpy as np
from qiskit import QuantumRegister, ClassicalRegister, QuantumCircuit
from qiskit.test import QiskitTestCase


class TestCircuitProperties(QiskitTestCase):
    """QuantumCircuit properties tests."""

    def test_circuit_depth_empty(self):
        """Test depth of empty circuity
        """
        q = QuantumRegister(5, 'q')
        qc = QuantumCircuit(q)
        self.assertEqual(qc.depth(), 0)

    def test_circuit_depth_meas_only(self):
        """Test depth of measurement only
        """
        q = QuantumRegister(1, 'q')
        c = ClassicalRegister(1, 'c')
        qc = QuantumCircuit(q, c)
        qc.measure(q, c)
        self.assertEqual(qc.depth(), 1)

    def test_circuit_depth_barrier(self):
        """Make sure barriers do not add to depth
        """
        q = QuantumRegister(5, 'q')
        c = ClassicalRegister(5, 'c')
        qc = QuantumCircuit(q, c)
        qc.h(q[0])
        qc.h(q[1])
        qc.h(q[2])
        qc.h(q[3])
        qc.h(q[4])
        qc.cx(q[0], q[1])
        qc.cx(q[1], q[4])
        qc.cx(q[4], q[2])
        qc.cx(q[2], q[3])
        qc.barrier(q)
        qc.measure(q, c)
        self.assertEqual(qc.depth(), 6)

    def test_circuit_depth_simple(self):
        """Test depth for simple circuit
        """
        q = QuantumRegister(5, 'q')
        c = ClassicalRegister(1, 'c')
        qc = QuantumCircuit(q, c)
        qc.h(q[0])
        qc.cx(q[0], q[4])
        qc.x(q[2])
        qc.x(q[2])
        qc.x(q[2])
        qc.x(q[4])
        qc.cx(q[4], q[1])
        qc.measure(q[1], c[0])
        self.assertEqual(qc.depth(), 5)

    def test_circuit_depth_multi_reg(self):
        """Test depth for multiple registers
        """
        q1 = QuantumRegister(3, 'q1')
        q2 = QuantumRegister(2, 'q2')
        c = ClassicalRegister(5, 'c')
        qc = QuantumCircuit(q1, q2, c)
        qc.h(q1[0])
        qc.h(q1[1])
        qc.h(q1[2])
        qc.h(q2[0])
        qc.h(q2[1])
        qc.cx(q1[0], q1[1])
        qc.cx(q1[1], q2[1])
        qc.cx(q2[1], q1[2])
        qc.cx(q1[2], q2[0])
        self.assertEqual(qc.depth(), 5)

    def test_circuit_depth_3q_gate(self):
        """Test depth for 3q gate
        """
        q1 = QuantumRegister(3, 'q1')
        q2 = QuantumRegister(2, 'q2')
        c = ClassicalRegister(5, 'c')
        qc = QuantumCircuit(q1, q2, c)
        qc.h(q1[0])
        qc.h(q1[1])
        qc.h(q1[2])
        qc.h(q2[0])
        qc.h(q2[1])
        qc.ccx(q2[1], q1[0], q2[0])
        qc.cx(q1[0], q1[1])
        qc.cx(q1[1], q2[1])
        qc.cx(q2[1], q1[2])
        qc.cx(q1[2], q2[0])
        self.assertEqual(qc.depth(), 6)

    def test_circuit_count_ops(self):
        """Tet circuit count ops
        """
        size = 6
        q = QuantumRegister(size, 'q')
        qc = QuantumCircuit(q)

        ans = {}
        num_gates = np.random.randint(50)
        # h = 0, x = 1, y = 2, z = 3, cx = 4, ccx = 5
        lookup = {0: 'h', 1: 'x', 2: 'y', 3: 'z', 4: 'cx', 5: 'ccx'}

        for _ in range(num_gates):
            item = np.random.randint(6)
            if item in [0, 1, 2, 3]:
                idx = np.random.randint(size)
                if item == 0:
                    qc.h(q[idx])
                elif item == 1:
                    qc.x(q[idx])
                elif item == 2:
                    qc.y(q[idx])
                elif item == 3:
                    qc.z(q[idx])
            else:
                idx = np.random.permutation(size)
                if item == 4:
                    qc.cx(q[int(idx[0])], q[int(idx[1])])
                elif item == 5:
                    qc.ccx(q[int(idx[0])], q[int(idx[1])], q[int(idx[2])])
            if lookup[item] not in ans.keys():
                ans[lookup[item]] = 1
            else:
                ans[lookup[item]] += 1

            self.assertEqual(ans, qc.count_ops())

    def test_circuit_tensor_factors_empty(self):
        """Verify num_tensor_factors is width for empty
        """
        size = np.random.randint(1, 10)
        q = QuantumRegister(size, 'q')
        qc = QuantumCircuit(q)
        self.assertEqual(size, qc.num_tensor_factors())

    def test_circuit_tensor_factors_multi_reg(self):
        """Test tensor factors works over muli registers
        """
        q1 = QuantumRegister(3, 'q1')
        q2 = QuantumRegister(2, 'q2')
        qc = QuantumCircuit(q1, q2)
        qc.h(q1[0])
        qc.h(q1[1])
        qc.h(q1[2])
        qc.h(q2[0])
        qc.h(q2[1])
        qc.cx(q1[0], q1[1])
        qc.cx(q1[1], q2[1])
        qc.cx(q2[1], q1[2])
        qc.cx(q1[2], q2[0])
        self.assertEqual(qc.num_tensor_factors(), 1)


    def test_circuit_tensor_factors_multi_reg2(self):
        """Test tensor factors works over muli registers #2
        """
        q1 = QuantumRegister(3, 'q1')
        q2 = QuantumRegister(2, 'q2')
        qc = QuantumCircuit(q1, q2)
        qc.cx(q1[0], q2[1])
        qc.cx(q2[0], q1[2])
        qc.cx(q1[1], q2[0])
        self.assertEqual(qc.num_tensor_factors(), 2)

    def test_circuit_tensor_factors_disconnected(self):
        """Test tensor factors works with 2q subspaces
        """
        q1 = QuantumRegister(5, 'q1')
        q2 = QuantumRegister(5, 'q2')
        qc = QuantumCircuit(q1, q2)
        qc.cx(q1[0], q2[4])
        qc.cx(q1[1], q2[3])
        qc.cx(q1[2], q2[2])
        qc.cx(q1[3], q2[1])
        qc.cx(q1[4], q2[0])
        self.assertEqual(qc.num_tensor_factors(), 5)

if __name__ == '__main__':
    unittest.main()
