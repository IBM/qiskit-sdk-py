# -*- coding: utf-8 -*-

# This code is part of Qiskit.
#
# (C) Copyright IBM 2017, 2018.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""A test for visualizing device coupling maps"""
import unittest
import os
import matplotlib.pyplot as plt
from qiskit.test.mock import FakeProvider
from qiskit.test import QiskitTestCase
from qiskit.visualization.gate_map import _GraphDist, plot_gate_map, plot_circuit_layout
from qiskit import QuantumRegister, QuantumCircuit
from qiskit.transpiler import Layout
from .visualization import path_to_diagram_reference, QiskitVisualizationTestCase


class TestGateMap(QiskitVisualizationTestCase):
    """ visual tests for plot_gate_map """
    backends = []

    def setUp(self):
        """ setup for backend """
        self.backends = list(filter(lambda x:
                                    not (x.configuration().simulator
                                         or x.configuration().n_qubits == 2),
                                    FakeProvider().backends()))

    def test_plot_gate_map(self):
        """ tests plotting of gate map of a device (20 qubit, 16 qubit, 14 qubit and 5 qubit)"""
        for backend in self.backends:
            n = backend.configuration().n_qubits
            img_ref = path_to_diagram_reference(str(n) + "bit_quantum_computer.png")
            filename = "temp.png"
            fig = plot_gate_map(backend)
            fig.savefig(filename, bbox_inches="tight")
            self.assertImagesAreEqual(filename, img_ref, 0.2)
            os.remove(filename)

    def test_plot_circuit_layout(self):
        """ tests plot_circuit_layout for each device (20 qubit, 16 qubit, 14 qubit and 5 qubit)"""
        qr = QuantumRegister(3, 'qr')
        circuit = QuantumCircuit(qr)
        circuit._layout = Layout({qr[0]: 4, qr[1]: 0, qr[2]: 2})
        for backend in [self.backends[2]]:
            n = backend.configuration().n_qubits
            img_ref = path_to_diagram_reference(str(n) + "_plot_circuit_layout.png")
            filename = "temp.png"
            fig = plot_circuit_layout(circuit, backend)
            fig.savefig(filename, bbox_inches="tight")
            self.assertImagesAreEqual(filename, img_ref, 0.1)
            os.remove(filename)


class TestGraphDist(QiskitTestCase):
    """ tests _GraphdDist functions """

    def setUp(self):
        """ setup plots for _GraphDist """
        ax1 = plt.subplots(figsize=(5, 5))[1]
        ax2 = plt.subplots(figsize=(9, 3))[1]
        ax1.axis("off")
        ax2.axis("off")
        self.ax1 = ax1
        self.ax2 = ax2
        self.ax1_x0, self.ax1_y0 = ax1.transAxes.transform((0, 0))
        self.ax1_x1, self.ax1_y1 = ax1.transAxes.transform((1, 1))
        self.ax2_x0, self.ax2_y0 = ax2.transAxes.transform((0, 0))
        self.ax2_x1, self.ax2_y1 = ax2.transAxes.transform((1, 1))
        self.ax1_bounds_x, self.ax1_bounds_y = ax1.get_xlim(), ax1.get_ylim()
        self.ax2_bounds_x, self.ax2_bounds_y = ax2.get_xlim(), ax2.get_ylim()
        self.size = 4
        self.real_values = [self.ax1_x1 - self.ax1_x0, self.ax1_y1 - self.ax1_y0,
                            self.ax2_x1 - self.ax2_x0, self.ax2_y1 - self.ax2_y0]
        self.abs_values = [self.ax1_bounds_x[0] - self.ax1_bounds_x[1],
                           self.ax1_bounds_y[0] - self.ax1_bounds_y[1],
                           self.ax2_bounds_x[0] - self.ax2_bounds_x[1],
                           self.ax2_bounds_y[0] - self.ax2_bounds_y[1]]
        self.val = []
        for i in range(4):
            val = (self.size / self.real_values[i]) * self.abs_values[i]
            self.val.append(val)

    def test_dist_real(self):
        """ tests dist_real calculation for different figsize """
        params = [(self.ax1, self.real_values[0], True), (self.ax1, self.real_values[1], False),
                  (self.ax2, self.real_values[2], True), (self.ax2, self.real_values[3], False)]
        for test_val, expected_val, bool_op in params:
            with self.subTest():
                self.assertEqual(expected_val, _GraphDist(self.size, test_val, bool_op).dist_real)

    def test_dist_abs(self):
        """ tests dist_abs calculation for different figsize """
        params = [(self.ax1, self.abs_values[0], True), (self.ax1, self.abs_values[1], False),
                  (self.ax2, self.abs_values[2], True), (self.ax2, self.abs_values[3], False)]
        for test_val, expected_val, bool_op in params:
            with self.subTest():
                self.assertEqual(expected_val, _GraphDist(self.size, test_val, bool_op).dist_abs)

    def test_value(self):
        """ tests value calculation for size = 4 """
        params = [(self.ax1, self.val[0], True), (self.ax1, self.val[1], False),
                  (self.ax2, self.val[2], True), (self.ax2, self.val[3], False)]
        for test_val, expected_val, bool_op in params:
            with self.subTest():
                self.assertEqual(expected_val, _GraphDist(self.size, test_val, bool_op).value)


if __name__ == '__main__':
    unittest.main(verbosity=2)
