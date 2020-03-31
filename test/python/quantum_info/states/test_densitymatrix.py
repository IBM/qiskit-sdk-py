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

# pylint: disable=invalid-name

"""Tests for DensityMatrix quantum state class."""

import unittest
import logging
import numpy as np
from numpy.testing import assert_allclose

from qiskit.test import QiskitTestCase
from qiskit import QiskitError
from qiskit import QuantumRegister, QuantumCircuit
from qiskit.extensions.standard import HGate

from qiskit.quantum_info.random import random_unitary
from qiskit.quantum_info.states import DensityMatrix, Statevector
from qiskit.quantum_info.operators.operator import Operator

logger = logging.getLogger(__name__)


class TestDensityMatrix(QiskitTestCase):
    """Tests for DensityMatrix class."""

    @classmethod
    def rand_vec(cls, n, normalize=False):
        """Return complex vector or statevector"""
        seed = np.random.randint(0, np.iinfo(np.int32).max)
        logger.debug("rand_vec RandomState seeded with seed=%s", seed)
        rng = np.random.RandomState(seed)
        vec = rng.rand(n) + 1j * rng.rand(n)
        if normalize:
            vec /= np.sqrt(np.dot(vec, np.conj(vec)))
        return vec

    @classmethod
    def rand_rho(cls, n):
        """Return random pure state density matrix"""
        rho = cls.rand_vec(n, normalize=True)
        return np.outer(rho, np.conjugate(rho))

    def test_init_array_qubit(self):
        """Test subsystem initialization from N-qubit array."""
        # Test automatic inference of qubit subsystems
        rho = self.rand_rho(8)
        for dims in [None, 8]:
            state = DensityMatrix(rho, dims=dims)
            assert_allclose(state.data, rho)
            self.assertEqual(state.dim, 8)
            self.assertEqual(state.dims(), (2, 2, 2))
            self.assertEqual(state.num_qubits, 3)

    def test_init_array(self):
        """Test initialization from array."""
        rho = self.rand_rho(3)
        state = DensityMatrix(rho)
        assert_allclose(state.data, rho)
        self.assertEqual(state.dim, 3)
        self.assertEqual(state.dims(), (3,))
        self.assertIsNone(state.num_qubits)

        rho = self.rand_rho(2 * 3 * 4)
        state = DensityMatrix(rho, dims=[2, 3, 4])
        assert_allclose(state.data, rho)
        self.assertEqual(state.dim, 2 * 3 * 4)
        self.assertEqual(state.dims(), (2, 3, 4))
        self.assertIsNone(state.num_qubits)

    def test_init_array_except(self):
        """Test initialization exception from array."""
        rho = self.rand_rho(4)
        self.assertRaises(QiskitError, DensityMatrix, rho, dims=[4, 2])
        self.assertRaises(QiskitError, DensityMatrix, rho, dims=[2, 4])
        self.assertRaises(QiskitError, DensityMatrix, rho, dims=5)

    def test_init_densitymatrix(self):
        """Test initialization from DensityMatrix."""
        rho1 = DensityMatrix(self.rand_rho(4))
        rho2 = DensityMatrix(rho1)
        self.assertEqual(rho1, rho2)

    def test_init_statevector(self):
        """Test initialization from DensityMatrix."""
        vec = self.rand_vec(4)
        target = DensityMatrix(np.outer(vec, np.conjugate(vec)))
        rho = DensityMatrix(Statevector(vec))
        self.assertEqual(rho, target)

    def test_from_circuit(self):
        """Test initialization from a circuit."""
        # random unitaries
        u0 = random_unitary(2).data
        u1 = random_unitary(2).data
        # add to circuit
        qr = QuantumRegister(2)
        circ = QuantumCircuit(qr)
        circ.unitary(u0, [qr[0]])
        circ.unitary(u1, [qr[1]])
        target_vec = Statevector(np.kron(u1, u0).dot([1, 0, 0, 0]))
        target = DensityMatrix(target_vec)
        rho = DensityMatrix.from_instruction(circ)
        self.assertEqual(rho, target)

        # Test tensor product of 1-qubit gates
        circuit = QuantumCircuit(3)
        circuit.h(0)
        circuit.x(1)
        circuit.ry(np.pi / 2, 2)
        target = DensityMatrix.from_label('000').evolve(Operator(circuit))
        rho = DensityMatrix.from_instruction(circuit)
        self.assertEqual(rho, target)

        # Test decomposition of Controlled-u1 gate
        lam = np.pi / 4
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.h(1)
        circuit.cu1(lam, 0, 1)
        target = DensityMatrix.from_label('00').evolve(Operator(circuit))
        rho = DensityMatrix.from_instruction(circuit)
        self.assertEqual(rho, target)

        # Test decomposition of controlled-H gate
        circuit = QuantumCircuit(2)
        circ.x(0)
        circuit.ch(0, 1)
        target = DensityMatrix.from_label('00').evolve(Operator(circuit))
        rho = DensityMatrix.from_instruction(circuit)
        self.assertEqual(rho, target)

    def test_from_instruction(self):
        """Test initialization from an instruction."""
        target_vec = Statevector(np.dot(HGate().to_matrix(), [1, 0]))
        target = DensityMatrix(target_vec)
        rho = DensityMatrix.from_instruction(HGate())
        self.assertEqual(rho, target)

    def test_from_label(self):
        """Test initialization from a label"""
        x_p = DensityMatrix(np.array([[0.5, 0.5], [0.5, 0.5]]))
        x_m = DensityMatrix(np.array([[0.5, -0.5], [-0.5, 0.5]]))
        y_p = DensityMatrix(np.array([[0.5, -0.5j], [0.5j, 0.5]]))
        y_m = DensityMatrix(np.array([[0.5, 0.5j], [-0.5j, 0.5]]))
        z_p = DensityMatrix(np.diag([1, 0]))
        z_m = DensityMatrix(np.diag([0, 1]))

        label = '0+r'
        target = z_p.tensor(x_p).tensor(y_p)
        self.assertEqual(target, DensityMatrix.from_label(label))

        label = '-l1'
        target = x_m.tensor(y_m).tensor(z_m)
        self.assertEqual(target, DensityMatrix.from_label(label))

    def test_equal(self):
        """Test __eq__ method"""
        for _ in range(10):
            rho = self.rand_rho(4)
            self.assertEqual(DensityMatrix(rho),
                             DensityMatrix(rho.tolist()))

    def test_rep(self):
        """Test Operator representation string property."""
        state = DensityMatrix(self.rand_rho(2))
        self.assertEqual(state.rep, 'DensityMatrix')

    def test_copy(self):
        """Test DensityMatrix copy method"""
        for _ in range(5):
            rho = self.rand_rho(4)
            orig = DensityMatrix(rho)
            cpy = orig.copy()
            cpy._data[0] += 1.0
            self.assertFalse(cpy == orig)

    def test_is_valid(self):
        """Test is_valid method."""
        state = DensityMatrix(np.eye(2))
        self.assertFalse(state.is_valid())
        for _ in range(10):
            state = DensityMatrix(self.rand_rho(4))
            self.assertTrue(state.is_valid())

    def test_to_operator(self):
        """Test to_operator method for returning projector."""
        for _ in range(10):
            rho = self.rand_rho(4)
            target = Operator(rho)
            op = DensityMatrix(rho).to_operator()
            self.assertEqual(op, target)

    def test_evolve(self):
        """Test evolve method for operators."""
        for _ in range(10):
            op = random_unitary(4)
            rho = self.rand_rho(4)
            target = DensityMatrix(np.dot(op.data, rho).dot(op.adjoint().data))
            evolved = DensityMatrix(rho).evolve(op)
            self.assertEqual(target, evolved)

    def test_evolve_subsystem(self):
        """Test subsystem evolve method for operators."""
        # Test evolving single-qubit of 3-qubit system
        for _ in range(5):
            rho = self.rand_rho(8)
            state = DensityMatrix(rho)
            op0 = random_unitary(2)
            op1 = random_unitary(2)
            op2 = random_unitary(2)

            # Test evolve on 1-qubit
            op = op0
            op_full = Operator(np.eye(4)).tensor(op)
            target = DensityMatrix(np.dot(op_full.data, rho).dot(op_full.adjoint().data))
            self.assertEqual(state.evolve(op, qargs=[0]), target)

            # Evolve on qubit 1
            op_full = Operator(np.eye(2)).tensor(op).tensor(np.eye(2))
            target = DensityMatrix(np.dot(op_full.data, rho).dot(op_full.adjoint().data))
            self.assertEqual(state.evolve(op, qargs=[1]), target)

            # Evolve on qubit 2
            op_full = op.tensor(np.eye(4))
            target = DensityMatrix(np.dot(op_full.data, rho).dot(op_full.adjoint().data))
            self.assertEqual(state.evolve(op, qargs=[2]), target)

            # Test evolve on 2-qubits
            op = op1.tensor(op0)

            # Evolve on qubits [0, 2]
            op_full = op1.tensor(np.eye(2)).tensor(op0)
            target = DensityMatrix(np.dot(op_full.data, rho).dot(op_full.adjoint().data))
            self.assertEqual(state.evolve(op, qargs=[0, 2]), target)

            # Evolve on qubits [2, 0]
            op_full = op0.tensor(np.eye(2)).tensor(op1)
            target = DensityMatrix(np.dot(op_full.data, rho).dot(op_full.adjoint().data))
            self.assertEqual(state.evolve(op, qargs=[2, 0]), target)

            # Test evolve on 3-qubits
            op = op2.tensor(op1).tensor(op0)

            # Evolve on qubits [0, 1, 2]
            op_full = op
            target = DensityMatrix(np.dot(op_full.data, rho).dot(op_full.adjoint().data))
            self.assertEqual(state.evolve(op, qargs=[0, 1, 2]), target)

            # Evolve on qubits [2, 1, 0]
            op_full = op0.tensor(op1).tensor(op2)
            target = DensityMatrix(np.dot(op_full.data, rho).dot(op_full.adjoint().data))
            self.assertEqual(state.evolve(op, qargs=[2, 1, 0]), target)

    def test_conjugate(self):
        """Test conjugate method."""
        for _ in range(10):
            rho = self.rand_rho(4)
            target = DensityMatrix(np.conj(rho))
            state = DensityMatrix(rho).conjugate()
            self.assertEqual(state, target)

    def test_expand(self):
        """Test expand method."""
        for _ in range(10):
            rho0 = self.rand_rho(2)
            rho1 = self.rand_rho(3)
            target = np.kron(rho1, rho0)
            state = DensityMatrix(rho0).expand(DensityMatrix(rho1))
            self.assertEqual(state.dim, 6)
            self.assertEqual(state.dims(), (2, 3))
            assert_allclose(state.data, target)

    def test_tensor(self):
        """Test tensor method."""
        for _ in range(10):
            rho0 = self.rand_rho(2)
            rho1 = self.rand_rho(3)
            target = np.kron(rho0, rho1)
            state = DensityMatrix(rho0).tensor(DensityMatrix(rho1))
            self.assertEqual(state.dim, 6)
            self.assertEqual(state.dims(), (3, 2))
            assert_allclose(state.data, target)

    def test_add(self):
        """Test add method."""
        for _ in range(10):
            rho0 = self.rand_rho(4)
            rho1 = self.rand_rho(4)
            state0 = DensityMatrix(rho0)
            state1 = DensityMatrix(rho1)
            self.assertEqual(state0.add(state1), DensityMatrix(rho0 + rho1))
            self.assertEqual(state0 + state1, DensityMatrix(rho0 + rho1))

    def test_add_except(self):
        """Test add method raises exceptions."""
        state1 = DensityMatrix(self.rand_rho(2))
        state2 = DensityMatrix(self.rand_rho(3))
        self.assertRaises(QiskitError, state1.add, state2)

    def test_subtract(self):
        """Test subtract method."""
        for _ in range(10):
            rho0 = self.rand_rho(4)
            rho1 = self.rand_rho(4)
            state0 = DensityMatrix(rho0)
            state1 = DensityMatrix(rho1)
            self.assertEqual(state0 - state1, DensityMatrix(rho0 - rho1))

    def test_multiply(self):
        """Test multiply method."""
        for _ in range(10):
            rho = self.rand_rho(4)
            state = DensityMatrix(rho)
            val = np.random.rand() + 1j * np.random.rand()
            self.assertEqual(state.multiply(val), DensityMatrix(val * rho))
            self.assertEqual(val * state, DensityMatrix(val * state))

    def test_negate(self):
        """Test negate method"""
        for _ in range(10):
            rho = self.rand_rho(4)
            state = DensityMatrix(rho)
            self.assertEqual(-state, DensityMatrix(-1 * rho))

    def test_to_dict(self):
        """Test to_dict method"""

        with self.subTest(msg='dims = (2, 2)'):
            rho = DensityMatrix(np.arange(1, 17).reshape(4, 4))
            target = {
                '00|00': 1, '01|00': 2, '10|00': 3, '11|00': 4,
                '00|01': 5, '01|01': 6, '10|01': 7, '11|01': 8,
                '00|10': 9, '01|10': 10, '10|10': 11, '11|10': 12,
                '00|11': 13, '01|11': 14, '10|11': 15, '11|11': 16
            }
            self.assertDictAlmostEqual(target, rho.to_dict())

        with self.subTest(msg='dims = (2, 3)'):
            rho = DensityMatrix(np.diag(np.arange(1, 7)), dims=(2, 3))
            target = {}
            for i in range(2):
                for j in range(3):
                    key = '{1}{0}|{1}{0}'.format(i, j)
                    target[key] = 2 * j + i + 1
            self.assertDictAlmostEqual(target, rho.to_dict())

        with self.subTest(msg='dims = (2, 11)'):
            vec = DensityMatrix(np.diag(np.arange(1, 23)), dims=(2, 11))
            target = {}
            for i in range(2):
                for j in range(11):
                    key = '{1},{0}|{1},{0}'.format(i, j)
                    target[key] = 2 * j + i + 1
            self.assertDictAlmostEqual(target, vec.to_dict())

    def test_probabilities_product(self):
        """Test probabilities method for product state"""

        state = DensityMatrix.from_label('+0')

        # 2-qubit qargs
        with self.subTest(msg='P(None)'):
            probs = state.probabilities()
            target = np.array([0.5, 0, 0.5, 0])
            self.assertTrue(np.allclose(probs, target))

        with self.subTest(msg='P([0, 1])'):
            probs = state.probabilities([0, 1])
            target = np.array([0.5, 0, 0.5, 0])
            self.assertTrue(np.allclose(probs, target))

        with self.subTest(msg='P([1, 0]'):
            probs = state.probabilities([1, 0])
            target = np.array([0.5, 0.5, 0, 0])
            self.assertTrue(np.allclose(probs, target))

        # 1-qubit qargs
        with self.subTest(msg='P([0])'):
            probs = state.probabilities([0])
            target = np.array([1, 0])
            self.assertTrue(np.allclose(probs, target))

        with self.subTest(msg='P([1])'):
            probs = state.probabilities([1])
            target = np.array([0.5, 0.5])
            self.assertTrue(np.allclose(probs, target))

    def test_probabilities_ghz(self):
        """Test probabilities method for GHZ state"""

        psi = (Statevector.from_label('000') +
               Statevector.from_label('111')) / np.sqrt(2)
        state = DensityMatrix(psi)

        # 3-qubit qargs
        target = np.array([0.5, 0, 0, 0, 0, 0, 0, 0.5])
        for qargs in [[0, 1, 2], [2, 1, 0], [1, 2, 0], [1, 0, 2]]:
            with self.subTest(msg='P({})'.format(qargs)):
                probs = state.probabilities(qargs)
                self.assertTrue(np.allclose(probs, target))

        # 2-qubit qargs
        target = np.array([0.5, 0, 0, 0.5])
        for qargs in [[0, 1], [2, 1], [1, 2], [1, 2]]:
            with self.subTest(msg='P({})'.format(qargs)):
                probs = state.probabilities(qargs)
                self.assertTrue(np.allclose(probs, target))

        # 1-qubit qargs
        target = np.array([0.5, 0.5])
        for qargs in [[0], [1], [2]]:
            with self.subTest(msg='P({})'.format(qargs)):
                probs = state.probabilities(qargs)
                self.assertTrue(np.allclose(probs, target))

    def test_probabilities_w(self):
        """Test probabilities method with W state"""

        psi = (Statevector.from_label('001') +
               Statevector.from_label('010') +
               Statevector.from_label('100')) / np.sqrt(3)
        state = DensityMatrix(psi)

        # 3-qubit qargs
        target = np.array([0, 1/3, 1/3, 0, 1/3, 0, 0, 0])
        for qargs in [[0, 1, 2], [2, 1, 0], [1, 2, 0], [1, 0, 2]]:
            with self.subTest(msg='P({})'.format(qargs)):
                probs = state.probabilities(qargs)
                self.assertTrue(np.allclose(probs, target))

        # 2-qubit qargs
        target = np.array([1/3, 1/3, 1/3, 0])
        for qargs in [[0, 1], [2, 1], [1, 2], [1, 2]]:
            with self.subTest(msg='P({})'.format(qargs)):
                probs = state.probabilities(qargs)
                self.assertTrue(np.allclose(probs, target))

        # 1-qubit qargs
        target = np.array([2/3, 1/3])
        for qargs in [[0], [1], [2]]:
            with self.subTest(msg='P({})'.format(qargs)):
                probs = state.probabilities(qargs)
                self.assertTrue(np.allclose(probs, target))

    def test_probabilities_dict_product(self):
        """Test probabilities_dict method for product state"""

        state = DensityMatrix.from_label('+0')

        # 2-qubit qargs
        with self.subTest(msg='P(None)'):
            probs = state.probabilities_dict()
            target = {'00': 0.5, '10': 0.5}
            self.assertDictAlmostEqual(probs, target)

        with self.subTest(msg='P([0, 1])'):
            probs = state.probabilities_dict([0, 1])
            target = {'00': 0.5, '10': 0.5}
            self.assertDictAlmostEqual(probs, target)

        with self.subTest(msg='P([1, 0]'):
            probs = state.probabilities_dict([1, 0])
            target = {'00': 0.5, '01': 0.5}
            self.assertDictAlmostEqual(probs, target)

        # 1-qubit qargs
        with self.subTest(msg='P([0])'):
            probs = state.probabilities_dict([0])
            target = {'0': 1}
            self.assertDictAlmostEqual(probs, target)

        with self.subTest(msg='P([1])'):
            probs = state.probabilities_dict([1])
            target = {'0': 0.5, '1': 0.5}
            self.assertDictAlmostEqual(probs, target)

    def test_probabilities_dict_ghz(self):
        """Test probabilities_dict method for GHZ state"""

        psi = (Statevector.from_label('000') +
               Statevector.from_label('111')) / np.sqrt(2)
        state = DensityMatrix(psi)

        # 3-qubit qargs
        target = {'000': 0.5, '111': 0.5}
        for qargs in [[0, 1, 2], [2, 1, 0], [1, 2, 0], [1, 0, 2]]:
            with self.subTest(msg='P({})'.format(qargs)):
                probs = state.probabilities_dict(qargs)
                self.assertDictAlmostEqual(probs, target)

        # 2-qubit qargs
        target = {'00': 0.5, '11': 0.5}
        for qargs in [[0, 1], [2, 1], [1, 2], [1, 2]]:
            with self.subTest(msg='P({})'.format(qargs)):
                probs = state.probabilities_dict(qargs)
                self.assertDictAlmostEqual(probs, target)

        # 1-qubit qargs
        target = {'0': 0.5, '1': 0.5}
        for qargs in [[0], [1], [2]]:
            with self.subTest(msg='P({})'.format(qargs)):
                probs = state.probabilities_dict(qargs)
                self.assertDictAlmostEqual(probs, target)

    def test_probabilities_dict_w(self):
        """Test probabilities_dict method with W state"""

        psi = (Statevector.from_label('001') +
               Statevector.from_label('010') +
               Statevector.from_label('100')) / np.sqrt(3)
        state = DensityMatrix(psi)

        # 3-qubit qargs
        target = np.array([0, 1/3, 1/3, 0, 1/3, 0, 0, 0])
        target = {'001': 1/3, '010': 1/3, '100': 1/3}
        for qargs in [[0, 1, 2], [2, 1, 0], [1, 2, 0], [1, 0, 2]]:
            with self.subTest(msg='P({})'.format(qargs)):
                probs = state.probabilities_dict(qargs)
                self.assertDictAlmostEqual(probs, target)

        # 2-qubit qargs
        target = {'00': 1/3, '01': 1/3, '10': 1/3}
        for qargs in [[0, 1], [2, 1], [1, 2], [1, 2]]:
            with self.subTest(msg='P({})'.format(qargs)):
                probs = state.probabilities_dict(qargs)
                self.assertDictAlmostEqual(probs, target)

        # 1-qubit qargs
        target = {'0': 2/3, '1': 1/3}
        for qargs in [[0], [1], [2]]:
            with self.subTest(msg='P({})'.format(qargs)):
                probs = state.probabilities_dict(qargs)
                self.assertDictAlmostEqual(probs, target)

    def test_sample_measure_ghz(self):
        """Test sample measure method for GHZ state"""

        shots = 2000
        threshold = 0.02 * shots
        state = DensityMatrix((
            Statevector.from_label('000') +
            Statevector.from_label('111')) / np.sqrt(2))
        state.seed(100)

        # 3-qubit qargs
        target = {'000': shots / 2, '111': shots / 2}
        for qargs in [[0, 1, 2], [2, 1, 0], [1, 2, 0], [1, 0, 2]]:

            with self.subTest(msg='counts (qargs={})'.format(qargs)):
                counts = state.sample_measure(qargs=qargs, shots=shots)
                self.assertDictAlmostEqual(counts, target, threshold)

            with self.subTest(msg='memory (qargs={})'.format(qargs)):
                memory = state.sample_measure(qargs=qargs, shots=shots, memory=True)
                self.assertEqual(len(memory), shots)
                self.assertEqual(set(memory), set(target))

        # 2-qubit qargs
        target = {'00': shots / 2, '11': shots / 2}
        for qargs in [[0, 1], [2, 1], [1, 2], [1, 2]]:

            with self.subTest(msg='counts (qargs={})'.format(qargs)):
                counts = state.sample_measure(qargs=qargs, shots=shots)
                self.assertDictAlmostEqual(counts, target, threshold)

            with self.subTest(msg='memory (qargs={})'.format(qargs)):
                memory = state.sample_measure(qargs=qargs, shots=shots, memory=True)
                self.assertEqual(len(memory), shots)
                self.assertEqual(set(memory), set(target))

        # 1-qubit qargs
        target = {'0': shots / 2, '1': shots / 2}
        for qargs in [[0], [1], [2]]:

            with self.subTest(msg='counts (qargs={})'.format(qargs)):
                counts = state.sample_measure(qargs=qargs, shots=shots)
                self.assertDictAlmostEqual(counts, target, threshold)

            with self.subTest(msg='memory (qargs={})'.format(qargs)):
                memory = state.sample_measure(qargs=qargs, shots=shots, memory=True)
                self.assertEqual(len(memory), shots)
                self.assertEqual(set(memory), set(target))

    def test_sample_measure_w(self):
        """Test sample measure method for W state"""
        shots = 3000
        threshold = 0.02 * shots
        state = DensityMatrix((
            Statevector.from_label('001') +
            Statevector.from_label('010') +
            Statevector.from_label('100')) / np.sqrt(3))
        state.seed(100)

        target = {'001': shots / 3, '010': shots / 3, '100': shots / 3}
        for qargs in [[0, 1, 2], [2, 1, 0], [1, 2, 0], [1, 0, 2]]:

            with self.subTest(msg='P({})'.format(qargs)):
                counts = state.sample_measure(qargs=qargs, shots=shots)
                self.assertDictAlmostEqual(counts, target, threshold)

            with self.subTest(msg='memory (qargs={})'.format(qargs)):
                memory = state.sample_measure(qargs=qargs, shots=shots, memory=True)
                self.assertEqual(len(memory), shots)
                self.assertEqual(set(memory), set(target))

        # 2-qubit qargs
        target = {'00': shots / 3, '01': shots / 3, '10': shots / 3}
        for qargs in [[0, 1], [2, 1], [1, 2], [1, 2]]:

            with self.subTest(msg='P({})'.format(qargs)):
                counts = state.sample_measure(qargs=qargs, shots=shots)
                self.assertDictAlmostEqual(counts, target, threshold)

            with self.subTest(msg='memory (qargs={})'.format(qargs)):
                memory = state.sample_measure(qargs=qargs, shots=shots, memory=True)
                self.assertEqual(len(memory), shots)
                self.assertEqual(set(memory), set(target))

        # 1-qubit qargs
        target = {'0': 2 * shots / 3, '1': shots / 3}
        for qargs in [[0], [1], [2]]:

            with self.subTest(msg='P({})'.format(qargs)):
                counts = state.sample_measure(qargs=qargs, shots=shots)
                self.assertDictAlmostEqual(counts, target, threshold)

            with self.subTest(msg='memory (qargs={})'.format(qargs)):
                memory = state.sample_measure(qargs=qargs, shots=shots, memory=True)
                self.assertEqual(len(memory), shots)
                self.assertEqual(set(memory), set(target))

    def test_sample_measure_qutrit(self):
        """Test sample measure method for qutrit state"""
        p = 0.3
        shots = 1000
        threshold = 0.02 * shots
        state = DensityMatrix(np.diag([p, 0, 1 - p]))
        state.seed(100)

        with self.subTest(msg='counts'):
            target = {'0': shots * p, '2': shots * (1 - p)}
            counts = state.sample_measure(shots=shots)
            self.assertDictAlmostEqual(counts, target, threshold)

        with self.subTest(msg='memory'):
            memory = state.sample_measure(shots=shots, memory=True)
            self.assertEqual(len(memory), shots)
            self.assertEqual(set(memory), set(['0', '2']))


if __name__ == '__main__':
    unittest.main()
