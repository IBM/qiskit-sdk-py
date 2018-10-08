# -*- coding: utf-8 -*-

# Copyright 2018, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

# pylint: disable = no-member

""" `text_drawer` "draws" a circuit in "ascii art" """

import os
import unittest
from math import pi
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.tools.visualization.text import text_drawer
from qiskit.tools.visualization import text as elements
from qiskit.wrapper._circuittoolkit import circuit_from_qasm_string
from .common import QiskitTestCase


class TestTextDrawerBigCircuit(QiskitTestCase):
    """ General cases and use cases, using big circuits. """

    def test_text_sample_circuit(self):
        """ Draw a sample circuit that includes the most common elements of quantum circuits. (taken
        from test/python/test_visualization_output.py:TestVisualizationImplementation:sample_circuit
        """
        qr = QuantumRegister(3, 'q')
        cr = ClassicalRegister(3, 'c')
        circuit = QuantumCircuit(qr, cr)
        circuit.x(qr[0])
        circuit.y(qr[0])
        circuit.z(qr[0])
        circuit.barrier(qr)
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
        path = os.path.dirname(os.path.abspath(__file__))
        print(text_drawer(circuit))
        with open(os.path.join(path, 'references', 'text_ref.txt')) as file:
            self.assertEqual(file.read().rstrip('\n'), text_drawer(circuit))

    def test_text_pager(self):
        """ The pager breaks the circuit when the drawing does not fit in the console."""
        qr = QuantumRegister(1, 'q')
        circuit = QuantumCircuit(qr)
        no_instructions = 50
        for _ in range(no_instructions):
            circuit.x(qr[0])
        self.assertEqual(text_drawer(circuit, line_length=10).count('\n'), no_instructions * 3 + 2)


class TestTextDrawerElement(QiskitTestCase):
    """ Draw each element"""

    def assertEqualElement(self, expected, element):
        self.assertEqual(expected[0], element.top)
        self.assertEqual(expected[1], element.mid)
        self.assertEqual(expected[2], element.bot)

    def test_MeasureTo(self):
        """ MeasureTo element. """
        element = elements.MeasureTo()
        expected = [" ║ ",
                    "═╩═",
                    "   "]
        self.assertEqualElement(expected, element)

    def test_MeasureFrom(self):
        """ MeasureFrom element. """
        element = elements.MeasureFrom()
        expected = ["┌─┐",
                    "┤M├",
                    "└╥┘"]
        self.assertEqualElement(expected, element)


class TestTextDrawerGatesInCircuit(QiskitTestCase):
    """ Gate by gate checks in different settings."""

    def test_text_measure_1(self):
        """ The measure operator, using 3-bit-length registers. """
        expected = '\n'.join(["              ┌─┐",
                              "q_0: |0>──────┤M├",
                              "           ┌─┐└╥┘",
                              "q_1: |0>───┤M├─╫─",
                              "        ┌─┐└╥┘ ║ ",
                              "q_2: |0>┤M├─╫──╫─",
                              "        └╥┘ ║  ║ ",
                              " c_0: 0 ═╬══╬══╩═",
                              "         ║  ║    ",
                              " c_1: 0 ═╬══╩════",
                              "         ║       ",
                              " c_2: 0 ═╩═══════",
                              "                 "])
        qr = QuantumRegister(3, 'q')
        cr = ClassicalRegister(3, 'c')
        circuit = QuantumCircuit(qr, cr)
        circuit.measure(qr, cr)
        self.assertEqual(text_drawer(circuit), expected)

    def test_text_measure_2(self):
        """ The measure operator, using some registers. """
        expected = '\n'.join(["               ",
                              "q1_0: |0>──────",
                              "               ",
                              "q1_1: |0>──────",
                              "            ┌─┐",
                              "q2_0: |0>───┤M├",
                              "         ┌─┐└╥┘",
                              "q2_1: |0>┤M├─╫─",
                              "         └╥┘ ║ ",
                              " c1_0: 0 ═╬══╬═",
                              "          ║  ║ ",
                              " c1_1: 0 ═╬══╬═",
                              "          ║  ║ ",
                              " c2_0: 0 ═╬══╩═",
                              "          ║    ",
                              " c2_1: 0 ═╩════",
                              "               "])
        qr1 = QuantumRegister(2, 'q1')
        cr1 = ClassicalRegister(2, 'c1')
        qr2 = QuantumRegister(2, 'q2')
        cr2 = ClassicalRegister(2, 'c2')
        circuit = QuantumCircuit(qr1, qr2, cr1, cr2)
        circuit.measure(qr2, cr2)
        self.assertEqual(text_drawer(circuit), expected)

    def test_text_swap(self):
        """ Swap drawing. """
        expected = '\n'.join(["               ",
                              "q1_0: |0>────X─",
                              "             │ ",
                              "q1_1: |0>─X──┼─",
                              "          │  │ ",
                              "q2_0: |0>─┼──X─",
                              "          │    ",
                              "q2_1: |0>─X────",
                              "               "])
        qr1 = QuantumRegister(2, 'q1')
        qr2 = QuantumRegister(2, 'q2')
        circuit = QuantumCircuit(qr1, qr2)
        circuit.swap(qr1, qr2)
        self.assertEqual(text_drawer(circuit), expected)

    def test_text_cswap(self):
        """ CSwap drawing. """
        expected = '\n'.join(["                 ",
                              "q_0: |0>─■──X──X─",
                              "         │  │  │ ",
                              "q_1: |0>─X──■──X─",
                              "         │  │  │ ",
                              "q_2: |0>─X──X──■─",
                              "                 "])
        qr = QuantumRegister(3, 'q')
        circuit = QuantumCircuit(qr)
        circuit.cswap(qr[0], qr[1], qr[2])
        circuit.cswap(qr[1], qr[0], qr[2])
        circuit.cswap(qr[2], qr[1], qr[0])
        self.assertEqual(text_drawer(circuit), expected)

    def test_text_cx(self):
        """ cx drawing. """
        expected = '\n'.join(["             ┌───┐",
                              "q_0: |0>──■──┤ X ├",
                              "        ┌─┴─┐└─┬─┘",
                              "q_1: |0>┤ X ├──┼──",
                              "        └───┘  │  ",
                              "q_2: |0>───────■──",
                              "                  "])
        qr = QuantumRegister(3, 'q')
        circuit = QuantumCircuit(qr)
        circuit.cx(qr[0], qr[1])
        circuit.cx(qr[2], qr[0])
        self.assertEqual(text_drawer(circuit), expected)

    def test_text_cy(self):
        """ cy drawing. """
        expected = '\n'.join(["             ┌───┐",
                              "q_0: |0>──■──┤ Y ├",
                              "        ┌─┴─┐└─┬─┘",
                              "q_1: |0>┤ Y ├──┼──",
                              "        └───┘  │  ",
                              "q_2: |0>───────■──",
                              "                  "])
        qr = QuantumRegister(3, 'q')
        circuit = QuantumCircuit(qr)
        circuit.cy(qr[0], qr[1])
        circuit.cy(qr[2], qr[0])
        self.assertEqual(text_drawer(circuit), expected)

    def test_text_cz(self):
        """ cz drawing. """
        expected = '\n'.join(["              ",
                              "q_0: |0>─■──■─",
                              "         │  │ ",
                              "q_1: |0>─■──┼─",
                              "            │ ",
                              "q_2: |0>────■─",
                              "              "])
        qr = QuantumRegister(3, 'q')
        circuit = QuantumCircuit(qr)
        circuit.cz(qr[0], qr[1])
        circuit.cz(qr[2], qr[0])
        self.assertEqual(text_drawer(circuit), expected)

    def test_text_ch(self):
        """ ch drawing. """
        expected = '\n'.join(["             ┌───┐",
                              "q_0: |0>──■──┤ H ├",
                              "        ┌─┴─┐└─┬─┘",
                              "q_1: |0>┤ H ├──┼──",
                              "        └───┘  │  ",
                              "q_2: |0>───────■──",
                              "                  "])
        qr = QuantumRegister(3, 'q')
        circuit = QuantumCircuit(qr)
        circuit.ch(qr[0], qr[1])
        circuit.ch(qr[2], qr[0])
        self.assertEqual(text_drawer(circuit), expected)

    def test_text_cu1(self):
        """ cu1 drawing. """
        expected = '\n'.join(["                          ",
                              "q_0: |0>─■────────■───────",
                              "         │1.5708  │       ",
                              "q_1: |0>─■────────┼───────",
                              "                  │1.5708 ",
                              "q_2: |0>──────────■───────",
                              "                          "])
        qr = QuantumRegister(3, 'q')
        circuit = QuantumCircuit(qr)
        circuit.cu1(pi / 2, qr[0], qr[1])
        circuit.cu1(pi / 2, qr[2], qr[0])
        self.assertEqual(text_drawer(circuit), expected)

    def test_text_ccx(self):
        """ cx drawing. """
        expected = '\n'.join(["                  ┌───┐",
                              "q_0: |0>──■────■──┤ X ├",
                              "          │  ┌─┴─┐└─┬─┘",
                              "q_1: |0>──■──┤ X ├──■──",
                              "        ┌─┴─┐└─┬─┘  │  ",
                              "q_2: |0>┤ X ├──■────■──",
                              "        └───┘          "])
        qr = QuantumRegister(3, 'q')
        circuit = QuantumCircuit(qr)
        circuit.ccx(qr[0], qr[1], qr[2])
        circuit.ccx(qr[2], qr[0], qr[1])
        circuit.ccx(qr[2], qr[1], qr[0])
        self.assertEqual(text_drawer(circuit), expected)

    def test_text_reset(self):
        """ Reset drawing. """
        expected = '\n'.join(["                        ",
                              "q1_0: |0>───────────|0>─",
                              "                        ",
                              "q1_1: |0>──────|0>──────",
                              "                        ",
                              "q2_0: |0>───────────────",
                              "                        ",
                              "q2_1: |0>─|0>───────────",
                              "                        "])
        qr1 = QuantumRegister(2, 'q1')
        qr2 = QuantumRegister(2, 'q2')
        circuit = QuantumCircuit(qr1, qr2)
        circuit.reset(qr1)
        circuit.reset(qr2[1])
        self.assertEqual(text_drawer(circuit), expected)

    def test_text_single_gate(self):
        """ Single Qbit gate drawing. """
        expected = '\n'.join(["                   ┌───┐",
                              "q1_0: |0>──────────┤ H ├",
                              "              ┌───┐└───┘",
                              "q1_1: |0>─────┤ H ├─────",
                              "              └───┘     ",
                              "q2_0: |0>───────────────",
                              "         ┌───┐          ",
                              "q2_1: |0>┤ H ├──────────",
                              "         └───┘          "])
        qr1 = QuantumRegister(2, 'q1')
        qr2 = QuantumRegister(2, 'q2')
        circuit = QuantumCircuit(qr1, qr2)
        circuit.h(qr1)
        circuit.h(qr2[1])
        self.assertEqual(text_drawer(circuit), expected)

    def test_text_barrier(self):
        """ Barrier drawing. """
        expected = '\n'.join(["             ¦ ",
                              "q1_0: |0>────¦─",
                              "             ¦ ",
                              "q1_1: |0>────¦─",
                              "             ¦ ",
                              "q2_0: |0>──────",
                              "          ¦    ",
                              "q2_1: |0>─¦────",
                              "          ¦    "])
        qr1 = QuantumRegister(2, 'q1')
        qr2 = QuantumRegister(2, 'q2')
        circuit = QuantumCircuit(qr1, qr2)
        circuit.barrier(qr1)
        circuit.barrier(qr2[1])
        self.assertEqual(text_drawer(circuit), expected)

    def test_text_conditional_1(self):
        """ Conditional drawing with 1-bit-length regs."""
        qasm_string = """
        OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[1];
        creg c0[1];
        creg c1[1];
        if(c0==1) x q[0];
        if(c1==1) x q[0];
        """
        expected = '\n'.join(["        ┌───────┐┌───────┐",
                              "q_0: |0>┤   X   ├┤   X   ├",
                              "        ├───┴───┤└───┬───┘",
                              "c0_0: 0 ╡ = 0x1 ╞════╪════",
                              "        └───────┘┌───┴───┐",
                              "c1_0: 0 ═════════╡ = 0x1 ╞",
                              "                 └───────┘"])
        circuit = circuit_from_qasm_string(qasm_string)
        self.assertEqual(text_drawer(circuit), expected)

    def test_text_conditional_2(self):
        """ Conditional drawing with 2-bit-length regs."""
        qasm_string = """
        OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[1];
        creg c0[2];
        creg c1[2];
        if(c0==2) x q[0];
        if(c1==2) x q[0];
        """
        expected = '\n'.join(["        ┌───────┐┌───────┐",
                              "q_0: |0>┤   X   ├┤   X   ├",
                              "        ├───┴───┤└───┬───┘",
                              "c0_0: 0 ╡       ╞════╪════",
                              "        │ = 0x2 │    │    ",
                              "c0_1: 0 ╡       ╞════╪════",
                              "        └───────┘┌───┴───┐",
                              "c1_0: 0 ═════════╡       ╞",
                              "                 │ = 0x2 │",
                              "c1_1: 0 ═════════╡       ╞",
                              "                 └───────┘"])
        circuit = circuit_from_qasm_string(qasm_string)
        self.assertEqual(text_drawer(circuit), expected)

    def test_text_conditional_3(self):
        """ Conditional drawing with 3-bit-length regs."""
        qasm_string = """
        OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[1];
        creg c0[3];
        creg c1[3];
        if(c0==3) x q[0];
        if(c1==3) x q[0];
        """
        expected = '\n'.join(["        ┌───────┐┌───────┐",
                              "q_0: |0>┤   X   ├┤   X   ├",
                              "        ├───┴───┤└───┬───┘",
                              "c0_0: 0 ╡       ╞════╪════",
                              "        │       │    │    ",
                              "c0_1: 0 ╡ = 0x3 ╞════╪════",
                              "        │       │    │    ",
                              "c0_2: 0 ╡       ╞════╪════",
                              "        └───────┘┌───┴───┐",
                              "c1_0: 0 ═════════╡       ╞",
                              "                 │       │",
                              "c1_1: 0 ═════════╡ = 0x3 ╞",
                              "                 │       │",
                              "c1_2: 0 ═════════╡       ╞",
                              "                 └───────┘"])
        circuit = circuit_from_qasm_string(qasm_string)
        self.assertEqual(text_drawer(circuit), expected)

    def test_text_conditional_4(self):
        """ Conditional drawing with 4-bit-length regs."""
        qasm_string = """
        OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[1];
        creg c0[4];
        creg c1[4];
        if(c0==4) x q[0];
        if(c1==4) x q[0];
        """
        expected = '\n'.join(["        ┌───────┐┌───────┐",
                              "q_0: |0>┤   X   ├┤   X   ├",
                              "        ├───┴───┤└───┬───┘",
                              "c0_0: 0 ╡       ╞════╪════",
                              "        │       │    │    ",
                              "c0_1: 0 ╡       ╞════╪════",
                              "        │ = 0x4 │    │    ",
                              "c0_2: 0 ╡       ╞════╪════",
                              "        │       │    │    ",
                              "c0_3: 0 ╡       ╞════╪════",
                              "        └───────┘┌───┴───┐",
                              "c1_0: 0 ═════════╡       ╞",
                              "                 │       │",
                              "c1_1: 0 ═════════╡       ╞",
                              "                 │ = 0x4 │",
                              "c1_2: 0 ═════════╡       ╞",
                              "                 │       │",
                              "c1_3: 0 ═════════╡       ╞",
                              "                 └───────┘"])
        circuit = circuit_from_qasm_string(qasm_string)
        self.assertEqual(text_drawer(circuit), expected)

    def test_text_conditional_5(self):
        """ Conditional drawing with 5-bit-length regs."""
        qasm_string = """
        OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[1];
        creg c0[5];
        creg c1[5];
        if(c0==5) x q[0];
        if(c1==5) x q[0];
        """
        expected = '\n'.join(["        ┌───────┐┌───────┐",
                              "q_0: |0>┤   X   ├┤   X   ├",
                              "        ├───┴───┤└───┬───┘",
                              "c0_0: 0 ╡       ╞════╪════",
                              "        │       │    │    ",
                              "c0_1: 0 ╡       ╞════╪════",
                              "        │       │    │    ",
                              "c0_2: 0 ╡ = 0x5 ╞════╪════",
                              "        │       │    │    ",
                              "c0_3: 0 ╡       ╞════╪════",
                              "        │       │    │    ",
                              "c0_4: 0 ╡       ╞════╪════",
                              "        └───────┘┌───┴───┐",
                              "c1_0: 0 ═════════╡       ╞",
                              "                 │       │",
                              "c1_1: 0 ═════════╡       ╞",
                              "                 │       │",
                              "c1_2: 0 ═════════╡ = 0x5 ╞",
                              "                 │       │",
                              "c1_3: 0 ═════════╡       ╞",
                              "                 │       │",
                              "c1_4: 0 ═════════╡       ╞",
                              "                 └───────┘"])
        circuit = circuit_from_qasm_string(qasm_string)
        self.assertEqual(text_drawer(circuit), expected)


if __name__ == '__main__':
    unittest.main()
