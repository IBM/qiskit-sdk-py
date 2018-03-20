# -*- coding: utf-8 -*-
# pylint: disable=invalid-name,missing-docstring

# Copyright 2017 IBM RESEARCH. All Rights Reserved.
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

import unittest

from qiskit import QuantumProgram
from qiskit import qasm, unroll, mapper
from .common import QiskitTestCase


class MapperTest(QiskitTestCase):
    """Test the mapper."""

    def setUp(self):
        self.seed = 42
        self.qp = QuantumProgram()

    def test_mapper_overoptimization(self):
        """
        The mapper should not change the semantics of the input. An overoptimization introduced
        the issue #81: https://github.com/QISKit/qiskit-sdk-py/issues/81
        """
        self.qp.load_qasm_file(self._get_resource_path('qasm/overoptimization.qasm'), name='test')
        coupling_map = {0: [2], 1: [2], 2: [3], 3: []}
        result1 = self.qp.execute(["test"], backend="local_qasm_simulator",
                                  coupling_map=coupling_map)
        count1 = result1.get_counts("test")
        result2 = self.qp.execute(["test"], backend="local_qasm_simulator", coupling_map=None)
        count2 = result2.get_counts("test")
        self.assertEqual(count1.keys(), count2.keys(), )

    def test_math_domain_error(self):
        """
        The math library operates over floats and introduce floating point errors that should be
        avoided.
        See: https://github.com/QISKit/qiskit-sdk-py/issues/111
        """
        self.qp.load_qasm_file(self._get_resource_path('qasm/math_domain_error.qasm'), name='test')
        coupling_map = {0: [2], 1: [2], 2: [3], 3: []}
        result1 = self.qp.execute(["test"], backend="local_qasm_simulator",
                                  coupling_map=coupling_map, seed=self.seed)

        self.assertEqual(result1.get_counts("test"), {'0001': 507, '0101': 517})

    def test_optimize_1q_gates_issue159(self):
        """Test change in behavior for optimize_1q_gates that removes u1(2*pi) rotations.

        See: https://github.com/QISKit/qiskit-sdk-py/issues/159
        """
        self.qp = QuantumProgram()
        qr = self.qp.create_quantum_register('qr', 2)
        cr = self.qp.create_classical_register('cr', 2)
        qc = self.qp.create_circuit('Bell', [qr], [cr])
        qc.h(qr[0])
        qc.cx(qr[1], qr[0])
        qc.cx(qr[1], qr[0])
        qc.cx(qr[1], qr[0])
        qc.measure(qr[0], cr[0])
        qc.measure(qr[1], cr[1])
        backend = 'local_qasm_simulator'
        cmap = {1: [0], 2: [0, 1, 4], 3: [2, 4]}
        qobj = self.qp.compile(["Bell"], backend=backend, coupling_map=cmap)

        self.assertEqual(self.qp.get_compiled_qasm(qobj, "Bell"), EXPECTED_QASM_1Q_GATES_3_5)

    def test_random_parameter_circuit(self):
        """Run a circuit with randomly generated parameters."""
        self.qp.load_qasm_file(self._get_resource_path('qasm/random_n5_d5.qasm'), name='rand')
        coupling_map = {0: [1], 1: [2], 2: [3], 3: [4]}
        result1 = self.qp.execute(["rand"], backend="local_qasm_simulator",
                                  coupling_map=coupling_map, seed=self.seed)
        res = result1.get_counts("rand")

        expected_result = {'10000': 92, '10100': 27, '01000': 99, '00001': 37,
                           '11100': 31, '01001': 27, '10111': 79, '00111': 43,
                           '00000': 88, '00010': 104, '11111': 14, '00110': 52,
                           '00100': 50, '01111': 21, '10010': 34, '01011': 21,
                           '00011': 15, '01101': 53, '10110': 32, '10101': 12,
                           '01100': 8, '01010': 7, '10011': 15, '11010': 26,
                           '11011': 8, '11110': 4, '01110': 14, '11001': 6,
                           '11000': 1, '11101': 2, '00101': 2}

        self.assertEqual(res, expected_result)

    def test_symbolic_unary(self):
        """Test symbolic math in DAGBackend and optimizer with a prefix.

        See: https://github.com/QISKit/qiskit-sdk-py/issues/172
        """
        ast = qasm.Qasm(filename=self._get_resource_path(
            'qasm/issue172_unary.qasm')).parse()
        unr = unroll.Unroller(ast, backend=unroll.DAGBackend(["cx", "u1", "u2", "u3"]))
        unr.execute()
        circ = mapper.optimize_1q_gates(unr.backend.circuit)
        self.assertEqual(circ.qasm(qeflag=True), EXPECTED_QASM_SYMBOLIC_UNARY)

    def test_symbolic_binary(self):
        """Test symbolic math in DAGBackend and optimizer with a binary operation.

        See: https://github.com/QISKit/qiskit-sdk-py/issues/172
        """
        ast = qasm.Qasm(filename=self._get_resource_path(
            'qasm/issue172_binary.qasm')).parse()

        unr = unroll.Unroller(ast, backend=unroll.DAGBackend(["cx", "u1", "u2", "u3"]))
        unr.execute()
        circ = mapper.optimize_1q_gates(unr.backend.circuit)
        self.assertEqual(circ.qasm(qeflag=True), EXPECTED_QASM_SYMBOLIC_BINARY)

    def test_symbolic_extern(self):
        """Test symbolic math in DAGBackend and optimizer with an external function.

        See: https://github.com/QISKit/qiskit-sdk-py/issues/172
        """
        ast = qasm.Qasm(filename=self._get_resource_path(
            'qasm/issue172_extern.qasm')).parse()
        unr = unroll.Unroller(ast, backend=unroll.DAGBackend(["cx", "u1", "u2", "u3"]))
        unr.execute()
        circ = mapper.optimize_1q_gates(unr.backend.circuit)
        self.assertEqual(circ.qasm(qeflag=True), EXPECTED_QASM_SYMBOLIC_EXTERN)

    def test_symbolic_power(self):
        """Test symbolic math in DAGBackend and optimizer with a power (^).

        See: https://github.com/QISKit/qiskit-sdk-py/issues/172
        """
        ast = qasm.Qasm(data=QASM_SYMBOLIC_POWER).parse()
        unr = unroll.Unroller(ast, backend=unroll.DAGBackend(["cx", "u1", "u2", "u3"]))
        unr.execute()
        circ = mapper.optimize_1q_gates(unr.backend.circuit)
        self.assertEqual(circ.qasm(qeflag=True), EXPECTED_QASM_SYMBOLIC_POWER)


# QASMs expected by the tests.
EXPECTED_QASM_SYMBOLIC_BINARY = """OPENQASM 2.0;
include "qelib1.inc";
qreg qr[1];
creg cr[1];
u1(-0.1 + 0.55*pi) qr[0];
measure qr[0] -> cr[0];\n"""

EXPECTED_QASM_SYMBOLIC_EXTERN = """OPENQASM 2.0;
include "qelib1.inc";
qreg qr[1];
creg cr[1];
u1(-0.479425538604203) qr[0];
measure qr[0] -> cr[0];\n"""

EXPECTED_QASM_SYMBOLIC_POWER = """OPENQASM 2.0;
include "qelib1.inc";
qreg qr[1];
creg cr[1];
u1(pi + (-pi + 0.3)^2.0) qr[0];
measure qr[0] -> cr[0];\n"""

EXPECTED_QASM_SYMBOLIC_UNARY = """OPENQASM 2.0;
include "qelib1.inc";
qreg qr[1];
creg cr[1];
u1(-1.5*pi) qr[0];
measure qr[0] -> cr[0];\n"""

EXPECTED_QASM_1Q_GATES = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg cr[2];
u2(0,3.14159265358979) q[0];
cx q[1],q[0];
cx q[1],q[0];
cx q[1],q[0];
u2(0,3.14159265358979) q[0];
measure q[0] -> cr[1];
u2(0,3.14159265358979) q[1];
measure q[1] -> cr[0];\n"""

# This QASM is the same as EXPECTED_QASM_1Q_GATES, with the u2-measure lines
# swapped.
EXPECTED_QASM_1Q_GATES_3_5 = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg cr[2];
u2(0,3.14159265358979) q[0];
cx q[1],q[0];
cx q[1],q[0];
cx q[1],q[0];
u2(0,3.14159265358979) q[1];
measure q[1] -> cr[0];
u2(0,3.14159265358979) q[0];
measure q[0] -> cr[1];\n"""

QASM_SYMBOLIC_POWER = """OPENQASM 2.0;
include "qelib1.inc";
qreg qr[1];
creg cr[1];
u1(pi) qr[0];
u1((0.3+(-pi))^2) qr[0];
measure qr[0] -> cr[0];"""


if __name__ == '__main__':
    unittest.main()
