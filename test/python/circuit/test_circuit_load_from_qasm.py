# -*- coding: utf-8 -*-

# This code is part of Qiskit.
#
# (C) Copyright IBM 2017.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.


"""Test cases for the circuit qasm_file and qasm_string method."""

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.circuit import Gate, Parameter
from qiskit.exceptions import QiskitError
from qiskit.test import QiskitTestCase, Path
from qiskit.transpiler.passes import Unroller
from qiskit.converters.circuit_to_dag import circuit_to_dag
from qiskit.converters.dag_to_circuit import dag_to_circuit


class LoadFromQasmTest(QiskitTestCase):
    """Test circuit.from_qasm_* set of methods."""

    def setUp(self):
        self.qasm_file_name = 'entangled_registers.qasm'
        self.qasm_file_path = self._get_resource_path(
            'qasm/' + self.qasm_file_name, Path.EXAMPLES)

    def test_qasm_file(self):
        """Test qasm_file and get_circuit.

        If all is correct we should get the qasm file loaded in _qasm_file_path
        """
        q_circuit = QuantumCircuit.from_qasm_file(self.qasm_file_path)
        qr_a = QuantumRegister(4, 'a')
        qr_b = QuantumRegister(4, 'b')
        cr_c = ClassicalRegister(4, 'c')
        cr_d = ClassicalRegister(4, 'd')
        q_circuit_2 = QuantumCircuit(qr_a, qr_b, cr_c, cr_d)
        q_circuit_2.h(qr_a)
        q_circuit_2.cx(qr_a, qr_b)
        q_circuit_2.barrier(qr_a)
        q_circuit_2.barrier(qr_b)
        q_circuit_2.measure(qr_a, cr_c)
        q_circuit_2.measure(qr_b, cr_d)
        self.assertEqual(q_circuit, q_circuit_2)

    def test_fail_qasm_file(self):
        """Test fail_qasm_file.

        If all is correct we should get a QiskitError
        """
        self.assertRaises(QiskitError,
                          QuantumCircuit.from_qasm_file, "")

    def test_fail_qasm_string(self):
        """Test fail_qasm_string.

        If all is correct we should get a QiskitError
        """
        self.assertRaises(QiskitError,
                          QuantumCircuit.from_qasm_str, "")

    def test_qasm_text(self):
        """Test qasm_text and get_circuit.

        If all is correct we should get the qasm file loaded from the string
        """
        qasm_string = "// A simple 8 qubit example\nOPENQASM 2.0;\n"
        qasm_string += "include \"qelib1.inc\";\nqreg a[4];\n"
        qasm_string += "qreg b[4];\ncreg c[4];\ncreg d[4];\nh a;\ncx a, b;\n"
        qasm_string += "barrier a;\nbarrier b;\nmeasure a[0]->c[0];\n"
        qasm_string += "measure a[1]->c[1];\nmeasure a[2]->c[2];\n"
        qasm_string += "measure a[3]->c[3];\nmeasure b[0]->d[0];\n"
        qasm_string += "measure b[1]->d[1];\nmeasure b[2]->d[2];\n"
        qasm_string += "measure b[3]->d[3];"
        q_circuit = QuantumCircuit.from_qasm_str(qasm_string)

        qr_a = QuantumRegister(4, 'a')
        qr_b = QuantumRegister(4, 'b')
        cr_c = ClassicalRegister(4, 'c')
        cr_d = ClassicalRegister(4, 'd')
        ref = QuantumCircuit(qr_a, qr_b, cr_c, cr_d)
        ref.h(qr_a[3])
        ref.cx(qr_a[3], qr_b[3])
        ref.h(qr_a[2])
        ref.cx(qr_a[2], qr_b[2])
        ref.h(qr_a[1])
        ref.cx(qr_a[1], qr_b[1])
        ref.h(qr_a[0])
        ref.cx(qr_a[0], qr_b[0])
        ref.barrier(qr_b)
        ref.measure(qr_b, cr_d)
        ref.barrier(qr_a)
        ref.measure(qr_a, cr_c)

        self.assertEqual(len(q_circuit.cregs), 2)
        self.assertEqual(len(q_circuit.qregs), 2)
        self.assertEqual(q_circuit, ref)

    def test_qasm_text_conditional(self):
        """Test qasm_text and get_circuit when conditionals are present.
        """
        qasm_string = '\n'.join(["OPENQASM 2.0;",
                                 "include \"qelib1.inc\";",
                                 "qreg q[1];",
                                 "creg c0[4];",
                                 "creg c1[4];",
                                 "x q[0];",
                                 "if(c1==4) x q[0];"]) + '\n'
        q_circuit = QuantumCircuit.from_qasm_str(qasm_string)

        qr = QuantumRegister(1, 'q')
        cr0 = ClassicalRegister(4, 'c0')
        cr1 = ClassicalRegister(4, 'c1')
        ref = QuantumCircuit(qr, cr0, cr1)
        ref.x(qr[0])
        ref.x(qr[0]).c_if(cr1, 4)

        self.assertEqual(len(q_circuit.cregs), 2)
        self.assertEqual(len(q_circuit.qregs), 1)
        self.assertEqual(q_circuit, ref)

    def test_opaque_gate(self):
        """Test parse an opaque gate
        See https://github.com/Qiskit/qiskit-terra/issues/1566"""

        qasm_string = '\n'.join(["OPENQASM 2.0;",
                                 "include \"qelib1.inc\";",
                                 "opaque my_gate(theta,phi,lambda) a,b;",
                                 "qreg q[3];",
                                 "my_gate(1,2,3) q[1],q[2];"]) + '\n'
        circuit = QuantumCircuit.from_qasm_str(qasm_string)

        qr = QuantumRegister(3, 'q')
        expected = QuantumCircuit(qr)
        expected.append(Gate(name='my_gate', num_qubits=2, params=[1, 2, 3]), [qr[1], qr[2]])

        self.assertEqual(circuit, expected)

    def test_qasm_example_file(self):
        """Loads qasm/example.qasm.
        """
        qasm_filename = self._get_resource_path('example.qasm', Path.QASMS)
        expected_circuit = QuantumCircuit.from_qasm_str('\n'.join(["OPENQASM 2.0;",
                                                                   "include \"qelib1.inc\";",
                                                                   "qreg q[3];",
                                                                   "qreg r[3];",
                                                                   "creg c[3];",
                                                                   "creg d[3];",
                                                                   "h q[2];",
                                                                   "cx q[2],r[2];",
                                                                   "measure r[2] -> d[2];",
                                                                   "h q[1];",
                                                                   "cx q[1],r[1];",
                                                                   "measure r[1] -> d[1];",
                                                                   "h q[0];",
                                                                   "cx q[0],r[0];",
                                                                   "measure r[0] -> d[0];",
                                                                   "barrier q[0],q[1],q[2];",
                                                                   "measure q[2] -> c[2];",
                                                                   "measure q[1] -> c[1];",
                                                                   "measure q[0] -> c[0];"]) + '\n')

        q_circuit = QuantumCircuit.from_qasm_file(qasm_filename)

        self.assertEqual(q_circuit, expected_circuit)
        self.assertEqual(len(q_circuit.cregs), 2)
        self.assertEqual(len(q_circuit.qregs), 2)

    def test_qasm_qas_string_order(self):
        """ Test that gates are returned in qasm in ascending order"""
        expected_qasm = '\n'.join(["OPENQASM 2.0;",
                                   "include \"qelib1.inc\";",
                                   "qreg q[3];",
                                   "h q[0];",
                                   "h q[1];",
                                   "h q[2];"]) + '\n'
        qasm_string = """OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[3];
        h q;"""
        q_circuit = QuantumCircuit.from_qasm_str(qasm_string)

        self.assertEqual(q_circuit.qasm(), expected_qasm)

    def test_from_qasm_str_custom_gate1(self):
        """ Test load custom gates (simple case)"""
        qasm_string = """OPENQASM 2.0;
                        include "qelib1.inc";
                        gate rinv q {sdg q; h q; sdg q; h q; }
                        qreg qr[1];
                        rinv qr[0];"""
        circuit = QuantumCircuit.from_qasm_str(qasm_string)

        rinv_q = QuantumRegister(1, name='q')
        rinv_gate = QuantumCircuit(rinv_q, name='rinv')
        rinv_gate.sdg(rinv_q)
        rinv_gate.h(rinv_q)
        rinv_gate.sdg(rinv_q)
        rinv_gate.h(rinv_q)
        rinv = rinv_gate.to_instruction()
        qr = QuantumRegister(1, name='qr')
        expected = QuantumCircuit(qr, name='circuit')
        expected.append(rinv, [qr[0]])

        self.assertEqualUnroll(['sdg', 'h'], circuit, expected)

    def test_from_qasm_str_custom_gate2(self):
        """ Test load custom gates (no so simple case, different bit order)
        See: https://github.com/Qiskit/qiskit-terra/pull/3393#issuecomment-551307250
        """
        qasm_string = """OPENQASM 2.0;
                         include "qelib1.inc";
                         gate swap2 a,b {
                           cx a,b;
                           cx b,a;  // different bit order
                           cx a,b;
                         }
                         qreg qr[3];
                         swap2 qr[0], qr[1];
                         swap2 qr[1], qr[2];"""
        circuit = QuantumCircuit.from_qasm_str(qasm_string)

        ab_args = QuantumRegister(2, name='ab')
        swap_gate = QuantumCircuit(ab_args, name='swap2')
        swap_gate.cx(ab_args[0], ab_args[1])
        swap_gate.cx(ab_args[1], ab_args[0])
        swap_gate.cx(ab_args[0], ab_args[1])
        swap = swap_gate.to_instruction()

        qr = QuantumRegister(3, name='qr')
        expected = QuantumCircuit(qr, name='circuit')
        expected.append(swap, [qr[0], qr[1]])
        expected.append(swap, [qr[1], qr[2]])

        self.assertEqualUnroll(['cx'], expected, circuit)

    def test_from_qasm_str_custom_gate3(self):
        """ Test load custom gates (no so simple case, different bit count)
        See: https://github.com/Qiskit/qiskit-terra/pull/3393#issuecomment-551307250
        """
        qasm_string = """OPENQASM 2.0;
                         include "qelib1.inc";
                         gate cswap2 a,b,c
                         {
                           cx c,b;  // different bit count
                           ccx a,b,c; //previously defined gate
                           cx c,b;
                         }
                         qreg qr[3];
                         cswap2 qr[1], qr[0], qr[2];"""
        circuit = QuantumCircuit.from_qasm_str(qasm_string)

        abc_args = QuantumRegister(3, name='abc')
        cswap_gate = QuantumCircuit(abc_args, name='cswap2')
        cswap_gate.cx(abc_args[2], abc_args[1])
        cswap_gate.ccx(abc_args[0], abc_args[1], abc_args[2])
        cswap_gate.cx(abc_args[2], abc_args[1])
        cswap = cswap_gate.to_instruction()

        qr = QuantumRegister(3, name='qr')
        expected = QuantumCircuit(qr, name='circuit')
        expected.append(cswap, [qr[1], qr[0], qr[2]])

        self.assertEqualUnroll(['cx', 'h', 'tdg', 't'], circuit, expected)

    def test_from_qasm_str_custom_gate4(self):
        """ Test load custom gates (parametrized)
        See: https://github.com/Qiskit/qiskit-terra/pull/3393#issuecomment-551307250
        """
        qasm_string = """OPENQASM 2.0;
                         include "qelib1.inc";
                         gate my_u2(phi,lambda) q {u3(1.5707963267948966,phi,lambda) q;}
                         qreg qr[1];
                         my_u2(pi, pi) qr[0];"""
        circuit = QuantumCircuit.from_qasm_str(qasm_string)

        my_u2_circuit = QuantumCircuit(1, name='my_u2')
        phi = Parameter('phi')
        lam = Parameter('lambda')
        my_u2_circuit.u3(1.5707963267948966, phi, lam, 0)
        my_u2 = my_u2_circuit.to_gate()

        qr = QuantumRegister(1, name='qr')
        expected = QuantumCircuit(qr, name='circuit')
        expected.append(my_u2, [qr[0]])
        expected = expected.bind_parameters({phi: 3.141592653589793, lam: 3.141592653589793})

        self.assertEqualUnroll('u3', circuit, expected)

    def test_from_qasm_str_custom_gate5(self):
        """ Test load custom gates (parametrized, with biop and constant)
        See: https://github.com/Qiskit/qiskit-terra/pull/3393#issuecomment-551307250
        """
        qasm_string = """OPENQASM 2.0;
                         include "qelib1.inc";
                         gate my_u2(phi,lambda) q {u3(pi/2,phi,lambda) q;} // biop with pi
                         qreg qr[1];
                         my_u2(pi, pi) qr[0];"""
        circuit = QuantumCircuit.from_qasm_str(qasm_string)

        my_u2_circuit = QuantumCircuit(1, name='my_u2')
        phi = Parameter('phi')
        lam = Parameter('lambda')
        my_u2_circuit.u3(1.5707963267948966, phi, lam, 0)
        my_u2 = my_u2_circuit.to_gate()

        qr = QuantumRegister(1, name='qr')
        expected = QuantumCircuit(qr, name='circuit')
        expected.append(my_u2, [qr[0]])
        expected = expected.bind_parameters({phi: 3.141592653589793, lam: 3.141592653589793})

        self.assertEqualUnroll('u3', circuit, expected)

    def assertEqualUnroll(self, basis, circuit, expected):
        circuit_dag = circuit_to_dag(circuit)
        expected_dag = circuit_to_dag(expected)

        circuit_result = Unroller(basis).run(circuit_dag)
        expected_result = Unroller(basis).run(expected_dag)

        self.assertEqual(circuit_result, expected_result)
