# This code is part of Qiskit.
#
# (C) Copyright IBM 2017, 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Test boolean expression."""

import unittest
from os import path

from qiskit.test.base import QiskitTestCase
from qiskit import execute, QuantumCircuit, BasicAer
from qiskit.circuit.classicalfunction.boolean_expression import BooleanExpression
from ddt import ddt, unpack, data


@ddt
class TestBooleanExpression(QiskitTestCase):
    """ """
    @data(('x | x', '1', True),
          ('x & x', '0', False),
          ('(x0 & x1 | ~x2) ^ x4', '0110', False),
          ('xx & xxx | ( ~z ^ zz)', '0111', True))
    @unpack
    def test_evaluate(self, expression, input, expected):
        """ Test the constructor of LogicalExpressionOracle"""
        expression = BooleanExpression(expression)
        result = expression.simulate(input)
        self.assertEqual(result, expected)

    @data(('x', False),
          ('not x', True),
          ('(x0 & x1 | ~x2) ^ x4', True),
          ('xx & xxx | ( ~z ^ zz)', True))
    @unpack
    def test_synth(self, expression, expected):
        """
        """
        expression = BooleanExpression(expression)
        expr_circ = expression.synth()

        new_creg = expr_circ._create_creg(1, 'c')
        expr_circ.add_register(new_creg)
        expr_circ.measure(expression.num_qubits-1, new_creg)
        [result] = execute(expr_circ, backend=BasicAer.get_backend('qasm_simulator'),
                           shots=1, seed_simulator=14).result().get_counts().keys()

        self.assertEqual(bool(int(result)), expected)


class TestBooleanExpressionDIMACS(QiskitTestCase):

    def normalize_filenames(self, filename):
        dir = path.dirname(__file__)
        return path.join(dir, filename)

    def test_simple(self):
        filename = self.normalize_filenames('dimacs/simple_v3_c2.cnf')
        simple = BooleanExpression.from_dimacs_file(filename)
        self.assertEqual(simple.name, 'simple_v3_c2.cnf')
        self.assertEqual(simple.num_qubits, 4)
        # print(simple.simulate('101'))

    def test_quinn(self):
        filename = self.normalize_filenames('dimacs/quinn.cnf')
        simple = BooleanExpression.from_dimacs_file(filename)
        self.assertEqual(simple.name, 'quinn.cnf')
        self.assertEqual(simple.num_qubits, 17)
        # print(simple.simulate('101'))

if __name__ == '__main__':
    unittest.main()
