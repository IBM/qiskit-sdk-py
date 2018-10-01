# -*- coding: utf-8 -*-

# Copyright 2018, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""Tests for comparing the outputs of text drawing of circtuis with expected ones."""

import os
import unittest
from math import pi
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from .common import QiskitTestCase
from qiskit.tools.visualization.text import text_drawer


class TestCircuitTextDrawer(QiskitTestCase):
    def sample_circuit(self):
        """Generate a sample circuit that includes the most common elements of
        quantum circuits.
        """
        qr = QuantumRegister(3, 'q')
        cr = ClassicalRegister(3, 'c')
        circuit = QuantumCircuit(qr, cr)
        circuit.x(qr[0])
        circuit.y(qr[0])
        circuit.z(qr[0])
        circuit.barrier(qr[0])
        circuit.barrier(qr[1])
        circuit.barrier(qr[2])
        circuit.h(qr[0])
        circuit.s(qr[0])
        circuit.sdg(qr[0])
        circuit.t(qr[0])
        circuit.tdg(qr[0])
        circuit.iden(qr[0])
        circuit.reset(qr[0])
        circuit.rx(pi, qr[0])
        circuit.ry(pi, qr[0])
        circuit.rz(pi, qr[0])
        circuit.u0(pi, qr[0])
        circuit.u1(pi, qr[0])
        circuit.u2(pi, pi, qr[0])
        circuit.u3(pi, pi, pi, qr[0])
        circuit.swap(qr[0], qr[1])
        circuit.cx(qr[0], qr[1])
        circuit.cy(qr[0], qr[1])
        circuit.cz(qr[0], qr[1])
        circuit.ch(qr[0], qr[1])
        circuit.cu1(pi, qr[0], qr[1])
        circuit.cu3(pi, pi, pi, qr[0], qr[1])
        circuit.crz(pi, qr[0], qr[1])
        circuit.ccx(qr[0], qr[1], qr[2])
        circuit.cswap(qr[0], qr[1], qr[2])
        circuit.measure(qr, cr)

        return circuit

    def test_text_measure_1(self):
        expected = '\n'.join([
            "             ┌─┐",
            "q0: |0>──────┤M├",
            "          ┌─┐└╥┘",
            "q1: |0>───┤M├─╫─",
            "       ┌─┐└╥┘ ║ ",
            "q2: |0>┤M├─╫──╫─",
            "       └╥┘ ║  ║ ",
            " c0: 0 ═╬══╬══╩═",
            "        ║  ║    ",
            " c1: 0 ═╬══╩════",
            "        ║       ",
            " c2: 0 ═╩═══════",
            "                "])
        qr = QuantumRegister(3, 'q')
        cr = ClassicalRegister(3, 'c')
        circuit = QuantumCircuit(qr, cr)
        circuit.measure(qr, cr)
        self.assertEqual(text_drawer(circuit, line_length=50), expected)


if __name__ == '__main__':
    unittest.main()
