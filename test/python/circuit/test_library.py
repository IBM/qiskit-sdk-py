# -*- coding: utf-8 -*-

# This code is part of Qiskit.
#
# (C) Copyright IBM 2017, 2020.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Test library of quantum circuits."""

import unittest
from collections import defaultdict
from ddt import ddt, data, unpack
import numpy as np

from qiskit.test.base import QiskitTestCase
from qiskit import BasicAer, execute, transpile
from qiskit.circuit import (QuantumCircuit, QuantumRegister, Parameter, ParameterExpression,
                            ParameterVector)
from qiskit.circuit.exceptions import CircuitError
from qiskit.circuit.random.utils import random_circuit
from qiskit.extensions.standard import XGate, RXGate, CRXGate, CCXGate

from qiskit.circuit.library import Permutation, XOR, InnerProduct
from qiskit.circuit.library.basis_change import QFT
from qiskit.circuit.library.n_local import NLocal, TwoLocal
from qiskit.circuit.library.arithmetic import (LinearPauliRotations, PolynomialPauliRotations,
                                               IntegerComparator, PiecewiseLinearPauliRotations,
                                               WeightedAdder)
from qiskit.converters.circuit_to_dag import circuit_to_dag
from qiskit.quantum_info import Operator


class TestBooleanLogicLibrary(QiskitTestCase):
    """Test library of boolean logic quantum circuits."""

    def test_permutation(self):
        """Test permutation circuit."""
        circuit = Permutation(num_qubits=4, pattern=[1, 0, 3, 2])
        expected = QuantumCircuit(4)
        expected.swap(0, 1)
        expected.swap(2, 3)
        self.assertEqual(circuit, expected)

    def test_permutation_bad(self):
        """Test that [0,..,n-1] permutation is required (no -1 for last element)"""
        self.assertRaises(CircuitError, Permutation, 4, [1, 0, -1, 2])

    def test_xor(self):
        """Test xor circuit."""
        circuit = XOR(num_qubits=3, amount=4)
        expected = QuantumCircuit(3)
        expected.x(2)
        self.assertEqual(circuit, expected)

    def test_inner_product(self):
        """Test inner product circuit."""
        circuit = InnerProduct(num_qubits=3)
        expected = QuantumCircuit(*circuit.qregs)
        expected.cz(0, 3)
        expected.cz(1, 4)
        expected.cz(2, 5)
        self.assertEqual(circuit, expected)


@ddt
class TestBasisChanges(QiskitTestCase):
    """Test the basis changes."""

    def assertQFTIsCorrect(self, qft, num_qubits=None, inverse=False, add_swaps_at_end=False):
        """Assert that the QFT circuit produces the correct matrix.

        Can be provided with an explicit number of qubits, if None is provided the number
        of qubits is set to ``qft.num_qubits``.
        """
        if add_swaps_at_end:
            circuit = QuantumCircuit(*qft.qregs)
            for i in range(circuit.num_qubits // 2):
                circuit.swap(i, circuit.num_qubits - i - 1)

            qft = qft + circuit

        simulated = Operator(qft)

        num_qubits = num_qubits or qft.num_qubits
        expected = np.empty((2 ** num_qubits, 2 ** num_qubits), dtype=complex)
        for i in range(2 ** num_qubits):
            i_qiskit = int(bin(i)[2:].zfill(num_qubits)[::-1], 2)
            for j in range(i, 2 ** num_qubits):
                entry = np.exp(2 * np.pi * 1j * i * j / 2 ** num_qubits) / 2 ** (num_qubits / 2)
                j_qiskit = int(bin(j)[2:].zfill(num_qubits)[::-1], 2)
                expected[i_qiskit, j_qiskit] = entry
                if i != j:
                    expected[j_qiskit, i_qiskit] = entry

        if inverse:
            expected = np.conj(expected)

        expected = Operator(expected)

        self.assertTrue(expected.equiv(simulated))

    @data(True, False)
    def test_qft_matrix(self, inverse):
        """Test the matrix representation of the QFT."""
        num_qubits = 5
        qft = QFT(num_qubits)
        if inverse:
            qft = qft.inverse()
        self.assertQFTIsCorrect(qft, inverse=inverse)

    def test_qft_mutability(self):
        """Test the mutability of the QFT circuit."""
        qft = QFT()

        with self.subTest(msg='empty initialization'):
            self.assertEqual(qft.num_qubits, 0)
            self.assertEqual(qft.data, [])

        with self.subTest(msg='changing number of qubits'):
            qft.num_qubits = 3
            self.assertQFTIsCorrect(qft, num_qubits=3)

        with self.subTest(msg='test diminishing the number of qubits'):
            qft.num_qubits = 1
            self.assertQFTIsCorrect(qft, num_qubits=1)

        with self.subTest(msg='test with swaps'):
            qft.num_qubits = 4
            qft.do_swaps = False
            self.assertQFTIsCorrect(qft, add_swaps_at_end=True)

        with self.subTest(msg='set approximation'):
            qft.approximation_degree = 2
            qft.do_swaps = True
            with self.assertRaises(AssertionError):
                self.assertQFTIsCorrect(qft)

    @data(
        (4, 0, False),
        (3, 0, True),
        (6, 2, False),
        (4, 5, True),
    )
    @unpack
    def test_qft_num_gates(self, num_qubits, approximation_degree, insert_barriers):
        """Test the number of gates in the QFT and the approximated QFT."""
        basis_gates = ['h', 'swap', 'cu1']

        qft = QFT(num_qubits, approximation_degree=approximation_degree,
                  insert_barriers=insert_barriers)
        ops = transpile(qft, basis_gates=basis_gates).count_ops()

        with self.subTest(msg='assert H count'):
            self.assertEqual(ops['h'], num_qubits)

        with self.subTest(msg='assert swap count'):
            self.assertEqual(ops['swap'], num_qubits // 2)

        with self.subTest(msg='assert CU1 count'):
            expected = sum(max(0, min(num_qubits - 1 - k, num_qubits - 1 - approximation_degree))
                           for k in range(num_qubits))
            self.assertEqual(ops.get('cu1', 0), expected)

        with self.subTest(msg='assert barrier count'):
            expected = qft.num_qubits if insert_barriers else 0
            self.assertEqual(ops.get('barrier', 0), expected)


@ddt
class TestFunctionalPauliRotations(QiskitTestCase):
    """Test the functional Pauli rotations."""

    def assertFunctionIsCorrect(self, function_circuit, reference):
        """Assert that ``function_circuit`` implements the reference function ``reference``."""
        num_state_qubits = function_circuit.num_state_qubits
        num_ancilla_qubits = function_circuit.num_ancilla_qubits
        circuit = QuantumCircuit(num_state_qubits + 1 + num_ancilla_qubits)
        circuit.h(list(range(num_state_qubits)))
        circuit.append(function_circuit.to_instruction(), list(range(circuit.num_qubits)))

        backend = BasicAer.get_backend('statevector_simulator')
        statevector = execute(circuit, backend).result().get_statevector()

        probabilities = defaultdict(float)
        for i, statevector_amplitude in enumerate(statevector):
            i = bin(i)[2:].zfill(circuit.num_qubits)[num_ancilla_qubits:]
            probabilities[i] += np.real(np.abs(statevector_amplitude) ** 2)

        unrolled_probabilities = []
        unrolled_expectations = []
        for i, probability in probabilities.items():
            x, last_qubit = int(i[1:], 2), i[0]
            if last_qubit == '0':
                expected_amplitude = np.cos(reference(x)) / np.sqrt(2**num_state_qubits)
            else:
                expected_amplitude = np.sin(reference(x)) / np.sqrt(2**num_state_qubits)

            unrolled_probabilities += [probability]
            unrolled_expectations += [np.real(np.abs(expected_amplitude) ** 2)]

        np.testing.assert_almost_equal(unrolled_probabilities, unrolled_expectations)

    @data(
        ([1, 0.1], 3),
        ([0, 0.4, 2], 2),
    )
    @unpack
    def test_polynomial_function(self, coeffs, num_state_qubits):
        """Test the polynomial rotation."""
        def poly(x):
            res = sum(coeff * x**i for i, coeff in enumerate(coeffs))
            return res

        polynome = PolynomialPauliRotations(num_state_qubits, [2 * coeff for coeff in coeffs])
        self.assertFunctionIsCorrect(polynome, poly)

    def test_polynomial_rotations_mutability(self):
        """Test the mutability of the linear rotations circuit."""

        polynomial_rotations = PolynomialPauliRotations()

        with self.subTest(msg='missing number of state qubits'):
            with self.assertRaises(AttributeError):  # no state qubits set
                print(polynomial_rotations.draw())

        with self.subTest(msg='default setup, just setting number of state qubits'):
            polynomial_rotations.num_state_qubits = 2
            self.assertFunctionIsCorrect(polynomial_rotations, lambda x: x / 2)

        with self.subTest(msg='setting non-default values'):
            polynomial_rotations.coeffs = [0, 1.2 * 2, 0.4 * 2]
            self.assertFunctionIsCorrect(polynomial_rotations, lambda x: 1.2 * x + 0.4 * x ** 2)

        with self.subTest(msg='changing of all values'):
            polynomial_rotations.num_state_qubits = 4
            polynomial_rotations.coeffs = [1 * 2, 0, 0, -0.5 * 2]
            self.assertFunctionIsCorrect(polynomial_rotations, lambda x: 1 - 0.5 * x**3)

    @data(
        (2, 0.1, 0),
        (4, -2, 2),
        (1, 0, 0)
    )
    @unpack
    def test_linear_function(self, num_state_qubits, slope, offset):
        """Test the linear rotation arithmetic circuit."""
        def linear(x):
            return offset + slope * x

        linear_rotation = LinearPauliRotations(num_state_qubits, slope * 2, offset * 2)
        self.assertFunctionIsCorrect(linear_rotation, linear)

    def test_linear_rotations_mutability(self):
        """Test the mutability of the linear rotations circuit."""

        linear_rotation = LinearPauliRotations()

        with self.subTest(msg='missing number of state qubits'):
            with self.assertRaises(AttributeError):  # no state qubits set
                print(linear_rotation.draw())

        with self.subTest(msg='default setup, just setting number of state qubits'):
            linear_rotation.num_state_qubits = 2
            self.assertFunctionIsCorrect(linear_rotation, lambda x: x / 2)

        with self.subTest(msg='setting non-default values'):
            linear_rotation.slope = -2.3 * 2
            linear_rotation.offset = 1 * 2
            self.assertFunctionIsCorrect(linear_rotation, lambda x: 1 - 2.3 * x)

        with self.subTest(msg='changing all values'):
            linear_rotation.num_state_qubits = 4
            linear_rotation.slope = 0.2 * 2
            linear_rotation.offset = 0.1 * 2
            self.assertFunctionIsCorrect(linear_rotation, lambda x: 0.1 + 0.2 * x)

    @data(
        (1, [0], [1], [0]),
        (2, [0, 2], [-0.5, 1], [2, 1]),
        (3, [0, 2, 5], [1, 0, -1], [0, 2, 2]),
        (2, [1, 2], [1, -1], [2, 1]),
        (3, [0, 1], [1, 0], [0, 1])
    )
    @unpack
    def test_piecewise_linear_function(self, num_state_qubits, breakpoints, slopes, offsets):
        """Test the piecewise linear rotations."""
        def pw_linear(x):
            for i, point in enumerate(reversed(breakpoints)):
                if x >= point:
                    return offsets[-(i + 1)] + slopes[-(i + 1)] * (x - point)
            return 0

        pw_linear_rotations = PiecewiseLinearPauliRotations(num_state_qubits, breakpoints,
                                                            [2 * slope for slope in slopes],
                                                            [2 * offset for offset in offsets])

        self.assertFunctionIsCorrect(pw_linear_rotations, pw_linear)

    def test_piecewise_linear_rotations_mutability(self):
        """Test the mutability of the linear rotations circuit."""

        pw_linear_rotations = PiecewiseLinearPauliRotations()

        with self.subTest(msg='missing number of state qubits'):
            with self.assertRaises(AttributeError):  # no state qubits set
                print(pw_linear_rotations.draw())

        with self.subTest(msg='default setup, just setting number of state qubits'):
            pw_linear_rotations.num_state_qubits = 2
            self.assertFunctionIsCorrect(pw_linear_rotations, lambda x: x / 2)

        with self.subTest(msg='setting non-default values'):
            pw_linear_rotations.breakpoints = [0, 2]
            pw_linear_rotations.slopes = [-1 * 2, 1 * 2]
            pw_linear_rotations.offsets = [0, -1.2 * 2]
            self.assertFunctionIsCorrect(pw_linear_rotations,
                                         lambda x: -1.2 + (x - 2) if x >= 2 else -x)

        with self.subTest(msg='changing all values'):
            pw_linear_rotations.num_state_qubits = 4
            pw_linear_rotations.breakpoints = [1, 3, 6]
            pw_linear_rotations.slopes = [-1 * 2, 1 * 2, -0.2 * 2]
            pw_linear_rotations.offsets = [0, -1.2 * 2, 2 * 2]

            def pw_linear(x):
                if x >= 6:
                    return 2 - 0.2 * (x - 6)
                if x >= 3:
                    return -1.2 + (x - 3)
                if x >= 1:
                    return -(x - 1)
                return 0

            self.assertFunctionIsCorrect(pw_linear_rotations, pw_linear)


@ddt
class TestIntegerComparator(QiskitTestCase):
    """Text Fixed Value Comparator"""

    def assertComparisonIsCorrect(self, comp, num_state_qubits, value, geq):
        """Assert that the comparator output is correct."""
        qc = QuantumCircuit(comp.num_qubits)  # initialize circuit
        qc.h(list(range(num_state_qubits)))  # set equal superposition state
        qc.append(comp, list(range(comp.num_qubits)))  # add comparator

        # run simulation
        backend = BasicAer.get_backend('statevector_simulator')
        statevector = execute(qc, backend).result().get_statevector()
        for i, amplitude in enumerate(statevector):
            prob = np.abs(amplitude)**2
            if prob > 1e-6:
                # equal superposition
                self.assertEqual(True, np.isclose(1.0, prob * 2.0**num_state_qubits))
                b_value = '{0:b}'.format(i).rjust(qc.width(), '0')
                x = int(b_value[(-num_state_qubits):], 2)
                comp_result = int(b_value[-num_state_qubits-1], 2)
                if geq:
                    self.assertEqual(x >= value, comp_result == 1)
                else:
                    self.assertEqual(x < value, comp_result == 1)

    @data(
        # n, value, geq
        [1, 0, True],
        [1, 1, True],
        [2, -1, True],
        [3, 5, True],
        [3, 2, True],
        [3, 2, False],
        [4, 6, False]
    )
    @unpack
    def test_fixed_value_comparator(self, num_state_qubits, value, geq):
        """Test the fixed value comparator circuit."""
        # build the circuit with the comparator
        comp = IntegerComparator(num_state_qubits, value, geq=geq)
        self.assertComparisonIsCorrect(comp, num_state_qubits, value, geq)

    def test_mutability(self):
        """Test changing the arguments of the comparator."""

        comp = IntegerComparator()

        with self.subTest(msg='missing num state qubits and value'):
            with self.assertRaises(AttributeError):
                print(comp.draw())

        comp.num_state_qubits = 2

        with self.subTest(msg='missing value'):
            with self.assertRaises(AttributeError):
                print(comp.draw())

        comp.value = 0
        comp.geq = True

        with self.subTest(msg='updating num state qubits'):
            comp.num_state_qubits = 1
            self.assertComparisonIsCorrect(comp, 1, 0, True)

        with self.subTest(msg='updating the value'):
            comp.num_state_qubits = 3
            comp.value = 2
            self.assertComparisonIsCorrect(comp, 3, 2, True)

        with self.subTest(msg='updating geq'):
            comp.geq = False
            self.assertComparisonIsCorrect(comp, 3, 2, False)


class TestAquaApplications(QiskitTestCase):
    """Test applications of the arithmetic library in Aqua use-cases."""

    def test_asian_barrier_spread(self):
        """Test the asian barrier spread model."""
        try:
            from qiskit.aqua.circuits import WeightedSumOperator, FixedValueComparator as Comparator
            from qiskit.aqua.components.uncertainty_problems import (
                UnivariatePiecewiseLinearObjective as PwlObjective,
                MultivariateProblem
            )
            from qiskit.aqua.components.uncertainty_models import MultivariateLogNormalDistribution
        except ImportError:
            import warnings
            warnings.warn('Qiskit Aqua is not installed, skipping the application test.')
            return

        # number of qubits per dimension to represent the uncertainty
        num_uncertainty_qubits = 2

        # parameters for considered random distribution
        spot_price = 2.0  # initial spot price
        volatility = 0.4  # volatility of 40%
        interest_rate = 0.05  # annual interest rate of 5%
        time_to_maturity = 40 / 365  # 40 days to maturity

        # resulting parameters for log-normal distribution
        # pylint: disable=invalid-name
        mu = ((interest_rate - 0.5 * volatility**2) * time_to_maturity + np.log(spot_price))
        sigma = volatility * np.sqrt(time_to_maturity)
        mean = np.exp(mu + sigma**2/2)
        variance = (np.exp(sigma**2) - 1) * np.exp(2*mu + sigma**2)
        stddev = np.sqrt(variance)

        # lowest and highest value considered for the spot price; in between,
        # an equidistant discretization is considered.
        low = np.maximum(0, mean - 3*stddev)
        high = mean + 3*stddev

        # map to higher dimensional distribution
        # for simplicity assuming dimensions are independent and identically distributed)
        dimension = 2
        num_qubits = [num_uncertainty_qubits]*dimension
        low = low * np.ones(dimension)
        high = high * np.ones(dimension)
        mu = mu * np.ones(dimension)
        cov = sigma ** 2 * np.eye(dimension)

        # construct circuit factory
        distribution = MultivariateLogNormalDistribution(num_qubits=num_qubits,
                                                         low=low,
                                                         high=high,
                                                         mu=mu,
                                                         cov=cov)

        # determine number of qubits required to represent total loss
        weights = []
        for n in num_qubits:
            for i in range(n):
                weights += [2**i]

        num_sum_qubits = WeightedSumOperator.get_required_sum_qubits(weights)

        # create circuit factoy
        agg = WeightedSumOperator(sum(num_qubits), weights)

        # set the strike price (should be within the low and the high value of the uncertainty)
        strike_price_1 = 3
        strike_price_2 = 4

        # set the barrier threshold
        barrier = 2.5

        # map strike prices and barrier threshold from [low, high] to {0, ..., 2^n-1}
        max_value = 2**num_sum_qubits - 1
        low_ = low[0]
        high_ = high[0]

        mapped_strike_price_1 = (strike_price_1 - dimension*low_) / \
            (high_ - low_) * (2**num_uncertainty_qubits - 1)
        mapped_strike_price_2 = (strike_price_2 - dimension*low_) / \
            (high_ - low_) * (2**num_uncertainty_qubits - 1)
        mapped_barrier = (barrier - low) / (high - low) * (2**num_uncertainty_qubits - 1)

        conditions = []
        for i in range(dimension):
            # target dimension of random distribution and corresponding condition
            conditions += [(i, Comparator(num_qubits[i], mapped_barrier[i] + 1, geq=False))]

        # set the approximation scaling for the payoff function
        c_approx = 0.25

        # setup piecewise linear objective fcuntion
        breakpoints = [0, mapped_strike_price_1, mapped_strike_price_2]
        slopes = [0, 1, 0]
        offsets = [0, 0, mapped_strike_price_2 - mapped_strike_price_1]
        f_min = 0
        f_max = mapped_strike_price_2 - mapped_strike_price_1
        bull_spread_objective = PwlObjective(
            num_sum_qubits, 0, max_value, breakpoints, slopes, offsets, f_min, f_max, c_approx)

        # define overall multivariate problem
        asian_barrier_spread = MultivariateProblem(
            distribution, agg, bull_spread_objective, conditions=conditions)

        num_req_qubits = asian_barrier_spread.num_target_qubits
        num_req_ancillas = asian_barrier_spread.required_ancillas()

        qr = QuantumRegister(num_req_qubits, name='q')
        qr_ancilla = QuantumRegister(num_req_ancillas, name='q_a')
        qc = QuantumCircuit(qr, qr_ancilla)

        asian_barrier_spread.build(qc, qr, qr_ancilla)
        job = execute(qc, backend=BasicAer.get_backend('statevector_simulator'))

        # evaluate resulting statevector
        value = 0
        for i, amplitude in enumerate(job.result().get_statevector()):
            b = ('{0:0%sb}' % asian_barrier_spread.num_target_qubits).format(
                i)[-asian_barrier_spread.num_target_qubits:]
            prob = np.abs(amplitude)**2
            if prob > 1e-4 and b[0] == '1':
                value += prob
                # all other states should have zero probability due to ancilla qubits
                if i > 2**num_req_qubits:
                    break

        # map value to original range
        mapped_value = asian_barrier_spread.value_to_estimation(
            value) / (2**num_uncertainty_qubits - 1) * (high_ - low_)
        expected = 0.83188
        self.assertAlmostEqual(mapped_value, expected, places=5)


@ddt
class TestWeightedAdder(QiskitTestCase):
    """Test the weighted adder circuit."""

    def assertSummationIsCorrect(self, adder):
        """Assert that ``adder`` correctly implements the summation w.r.t. its set weights."""

        circuit = QuantumCircuit(adder.num_qubits)
        circuit.h(list(range(adder.num_state_qubits)))
        circuit.append(adder.to_instruction(), list(range(adder.num_qubits)))

        backend = BasicAer.get_backend('statevector_simulator')
        statevector = execute(circuit, backend).result().get_statevector()

        probabilities = defaultdict(float)
        for i, statevector_amplitude in enumerate(statevector):
            i = bin(i)[2:].zfill(circuit.num_qubits)[adder.num_ancilla_qubits:]
            probabilities[i] += np.real(np.abs(statevector_amplitude) ** 2)

        expectations = defaultdict(float)
        for x in range(2**adder.num_state_qubits):
            bits = np.array(list(bin(x)[2:].zfill(adder.num_state_qubits)), dtype=int)
            summation = bits.dot(adder.weights[::-1])

            entry = bin(summation)[2:].zfill(adder.num_sum_qubits) \
                + bin(x)[2:].zfill(adder.num_state_qubits)
            expectations[entry] = 1 / 2 ** adder.num_state_qubits

        for state, probability in probabilities.items():
            self.assertAlmostEqual(probability, expectations[state])

    @data(
        [0],
        [1, 2, 1],
        [4],
    )
    def test_summation(self, weights):
        """Test the weighted adder on some examples."""
        adder = WeightedAdder(len(weights), weights)
        self.assertSummationIsCorrect(adder)

    def test_mutability(self):
        """Test the mutability of the weighted adder."""
        adder = WeightedAdder()

        with self.subTest(msg='missing number of state qubits'):
            with self.assertRaises(AttributeError):
                print(adder.draw())

        with self.subTest(msg='default weights'):
            adder.num_state_qubits = 3
            default_weights = 3 * [1]
            self.assertListEqual(adder.weights, default_weights)

        with self.subTest(msg='specify weights'):
            adder.weights = [3, 2, 1]
            self.assertSummationIsCorrect(adder)

        with self.subTest(msg='mismatching number of state qubits and weights'):
            with self.assertRaises(ValueError):
                adder.weights = [0, 1, 2, 3]
                print(adder.draw())

        with self.subTest(msg='change all attributes'):
            adder.num_state_qubits = 4
            adder.weights = [2, 0, 1, 1]
            self.assertSummationIsCorrect(adder)


@ddt
class TestNLocal(QiskitTestCase):
    """Test the n-local circuit class."""

    def assertCircuitEqual(self, qc1, qc2, visual=False, verbosity=0, transpiled=True):
        """An equality test specialized to circuits."""
        basis_gates = ['id', 'u1', 'u3', 'cx']
        qc1_transpiled = transpile(qc1, basis_gates=basis_gates)
        qc2_transpiled = transpile(qc2, basis_gates=basis_gates)

        if verbosity > 0:
            print('-- circuit 1:')
            print(qc1)
            print('-- circuit 2:')
            print(qc2)
            print('-- transpiled circuit 1:')
            print(qc1_transpiled)
            print('-- transpiled circuit 2:')
            print(qc2_transpiled)

        if verbosity > 1:
            print('-- dict:')
            for key in qc1.__dict__.keys():
                if key == '_data':
                    print(key)
                    print(qc1.__dict__[key])
                    print(qc2.__dict__[key])
                else:
                    print(key, qc1.__dict__[key], qc2.__dict__[key])

        if transpiled:
            qc1, qc2 = qc1_transpiled, qc2_transpiled

        if visual:
            self.assertEqual(qc1.draw(), qc2.draw())
        else:
            self.assertEqual(qc1, qc2)

    def test_empty_nlocal(self):
        """Test the creation of an empty NLocal."""
        nlocal = NLocal()
        self.assertEqual(nlocal.num_qubits, 0)
        self.assertEqual(nlocal.num_parameters_settable, 0)
        self.assertEqual(nlocal.reps, 1)

        self.assertEqual(nlocal, QuantumCircuit())

        for attribute in [nlocal.rotation_blocks, nlocal.entanglement_blocks]:
            self.assertEqual(len(attribute), 0)

    @data(
        [(XGate(), [0])],
        [(XGate(), [0]), (XGate(), [2])],
        [(RXGate(0.2), [2]), (CRXGate(-0.2), [1, 3])],
    )
    def test_append_gates_to_empty_nlocal(self, gate_data):
        """Test appending gates to an empty nlocal."""
        nlocal = NLocal()

        max_num_qubits = 0
        for (_, indices) in gate_data:
            max_num_qubits = max(max_num_qubits, max(indices))

        reference = QuantumCircuit(max_num_qubits + 1)
        for (gate, indices) in gate_data:
            nlocal.compose(gate, indices)
            reference.append(gate, indices)

        self.assertCircuitEqual(nlocal, reference, verbosity=0)

    @data(
        [5, 3], [1, 5], [1, 1], [1, 2, 3, 10],
    )
    def test_append_circuit(self, num_qubits):
        """Test appending circuits to an nlocal."""
        # fixed depth of 3 gates per circuit
        depth = 3

        # keep track of a reference circuit
        reference = QuantumCircuit(max(num_qubits))

        # construct the NLocal from the first circuit
        first_circuit = random_circuit(num_qubits[0], depth)
        # TODO Terra bug: if this is to_gate it fails, since the QC adds an instruction not gate
        nlocal = NLocal(max(num_qubits), entanglement_blocks=first_circuit.to_instruction(), reps=1)
        reference.append(first_circuit, list(range(num_qubits[0])))

        # append the rest
        for num in num_qubits[1:]:
            circuit = random_circuit(num, depth)
            nlocal.compose(circuit)
            reference.append(circuit, list(range(num)))

        self.assertCircuitEqual(nlocal, reference)

    @data(
        [5, 3], [1, 5], [1, 1], [1, 2, 3, 10],
    )
    def test_compose_nlocal(self, num_qubits):
        """Test composeing an nlocal to an nlocal."""
        # fixed depth of 3 gates per circuit
        depth = 3

        # keep track of a reference circuit
        reference = QuantumCircuit(max(num_qubits))

        # construct the NLocal from the first circuit
        first_circuit = random_circuit(num_qubits[0], depth)
        # TODO Terra bug: if this is to_gate it fails, since the QC adds an instruction not gate
        nlocal = NLocal(max(num_qubits), entanglement_blocks=first_circuit.to_instruction(), reps=1)
        reference.append(first_circuit, list(range(num_qubits[0])))

        # append the rest
        for num in num_qubits[1:]:
            circuit = random_circuit(num, depth)
            nlocal.compose(NLocal(num, entanglement_blocks=circuit, reps=1))
            reference.append(circuit, list(range(num)))

        self.assertCircuitEqual(nlocal, reference)

    @unittest.skip('Feature missing')
    def test_iadd_overload(self):
        """Test the overloaded + operator."""
        num_qubits, depth = 2, 2

        # construct two circuits for adding
        first_circuit = random_circuit(num_qubits, depth)
        circuit = random_circuit(num_qubits, depth)

        # get a reference
        reference = first_circuit + circuit

        # convert the object to be appended to different types
        others = [circuit, circuit.to_instruction(), circuit.to_gate(), NLocal(circuit)]

        # try adding each type
        for other in others:
            nlocal = NLocal(num_qubits, entanglement_blocks=first_circuit, reps=1)
            nlocal += other
            with self.subTest(msg='type: {}'.format(type(other))):
                self.assertCircuitEqual(nlocal, reference, verbosity=0)

    def test_parameter_getter_from_automatic_repetition(self):
        """Test getting and setting of the nlocal parameters."""
        circuit = QuantumCircuit(2)
        circuit.ry(Parameter('a'), 0)
        circuit.crx(Parameter('b'), 0, 1)

        # repeat circuit and check that parameters are duplicated
        reps = 3
        nlocal = NLocal(2, entanglement_blocks=circuit, reps=reps)
        self.assertTrue(nlocal.num_parameters, 6)
        self.assertTrue(len(nlocal.parameters), 6)

    @data(list(range(6)), ParameterVector('θ', length=6))
    def test_parameter_setter_from_automatic_repetition(self, params):
        """Test getting and setting of the nlocal parameters.

        TODO Test the input ``[0, 1, Parameter('theta'), 3, 4, 5]`` once that's supported.
        """
        circuit = QuantumCircuit(2)
        circuit.ry(Parameter('a'), 0)
        circuit.crx(Parameter('b'), 0, 1)

        # repeat circuit and check that parameters are duplicated
        reps = 3
        nlocal = NLocal(2, entanglement_blocks=circuit, reps=reps)
        nlocal.parameters = params

        param_set = set(p for p in params if isinstance(p, ParameterExpression))
        with self.subTest(msg='Test the parameters of the non-transpiled circuit'):
            # check the parameters of the final circuit
            self.assertEqual(nlocal.parameters, param_set)

        with self.subTest(msg='Test the parameters of the transpiled circuit'):
            basis_gates = ['id', 'u1', 'u2', 'u3', 'cx']
            transpiled_circuit = transpile(nlocal, basis_gates=basis_gates)
            self.assertEqual(transpiled_circuit.parameters, param_set)

    @data(list(range(6)), ParameterVector('θ', length=6), [0, 1, Parameter('theta'), 3, 4, 5])
    def test_parameters_setter(self, params):
        """Test setting the parameters via list."""
        # construct circuit with some parameters
        initial_params = ParameterVector('p', length=6)
        circuit = QuantumCircuit(1)
        for i, initial_param in enumerate(initial_params):
            circuit.ry(i * initial_param, 0)

        # create an NLocal from the circuit and set the new parameters
        nlocal = NLocal(1, entanglement_blocks=circuit, reps=1)
        nlocal.parameters = params

        param_set = set(p for p in params if isinstance(p, ParameterExpression))
        with self.subTest(msg='Test the parameters of the non-transpiled circuit'):
            # check the parameters of the final circuit
            self.assertEqual(nlocal.parameters, param_set)

        with self.subTest(msg='Test the parameters of the transpiled circuit'):
            basis_gates = ['id', 'u1', 'u2', 'u3', 'cx']
            transpiled_circuit = transpile(nlocal, basis_gates=basis_gates)
            self.assertEqual(transpiled_circuit.parameters, param_set)

    def test_repetetive_parameter_setting(self):
        """Test alternate setting of parameters and circuit construction."""
        x = Parameter('x')
        circuit = QuantumCircuit(1)
        circuit.rx(x, 0)

        nlocal = NLocal(1, entanglement_blocks=circuit, reps=3, insert_barriers=True)
        with self.subTest(msg='immediately after initialization'):
            self.assertEqual(len(nlocal.parameters), 3)

        with self.subTest(msg='after circuit construction'):
            self.assertEqual(len(nlocal.parameters), 3)

        q = Parameter('q')
        nlocal.parameters = [x, q, q]
        with self.subTest(msg='setting parameter to Parameter objects'):
            self.assertEqual(nlocal.parameters, set({x, q}))

        nlocal.parameters = [0, -1]
        with self.subTest(msg='setting parameter to numbers'):
            self.assertEqual(nlocal.parameters, set())

    def test_skip_unentangled_qubits(self):
        """Test skipping the unentangled qubits."""
        num_qubits = 6
        entanglement_1 = [[0, 1, 3], [1, 3, 5], [0, 1, 5]]
        skipped_1 = [2, 4]

        entanglement_2 = [
            entanglement_1,
            [[0, 1, 2], [2, 3, 5]]
        ]
        skipped_2 = [4]

        for entanglement, skipped in zip([entanglement_1, entanglement_2], [skipped_1, skipped_2]):
            with self.subTest(entanglement=entanglement, skipped=skipped):
                nlocal = NLocal(num_qubits, rotation_blocks=XGate(), entanglement_blocks=CCXGate(),
                                entanglement=entanglement, reps=3, skip_unentangled_qubits=True)

                skipped_set = set(nlocal.qubits[i] for i in skipped)
                dag = circuit_to_dag(nlocal)
                idle = set(dag.idle_wires())
                self.assertEqual(skipped_set, idle)


@ddt
class TestTwoLocal(QiskitTestCase):
    """Tests for the TwoLocal circuit."""

    def assertCircuitEqual(self, qc1, qc2, visual=False, verbosity=0, transpiled=True):
        """An equality test specialized to circuits."""
        basis_gates = ['id', 'u1', 'u3', 'cx']
        qc1_transpiled = transpile(qc1, basis_gates=basis_gates)
        qc2_transpiled = transpile(qc2, basis_gates=basis_gates)

        if verbosity > 0:
            print('-- circuit 1:')
            print(qc1)
            print('-- circuit 2:')
            print(qc2)
            print('-- transpiled circuit 1:')
            print(qc1_transpiled)
            print('-- transpiled circuit 2:')
            print(qc2_transpiled)

        if verbosity > 1:
            print('-- dict:')
            for key in qc1.__dict__.keys():
                if key == '_data':
                    print(key)
                    print(qc1.__dict__[key])
                    print(qc2.__dict__[key])
                else:
                    print(key, qc1.__dict__[key], qc2.__dict__[key])

        if transpiled:
            qc1, qc2 = qc1_transpiled, qc2_transpiled

        if visual:
            self.assertEqual(qc1.draw(), qc2.draw())
        else:
            self.assertEqual(qc1, qc2)

    def test_skip_final_rotation_layer(self):
        """Test skipping the final rotation layer works."""
        two = TwoLocal(3, ['ry', 'h'], ['cz', 'cx'], reps=2, skip_final_rotation_layer=True)
        self.assertEqual(two.num_parameters, 6)  # would be 9 with a final rotation layer

    @data(
        (5, 'rx', 'cx', 'full', 2, 15),
        (3, 'x', 'z', 'linear', 1, 0),
        (3, ['rx', 'ry'], ['cry', 'cx'], 'circular', 2, 24)
    )
    @unpack
    def test_num_parameters(self, num_qubits, rot, ent, ent_mode, reps, expected):
        """Test the number of parameters."""
        two = TwoLocal(num_qubits, rotation_blocks=rot, entanglement_blocks=ent,
                       entanglement=ent_mode, reps=reps)

        with self.subTest(msg='num_parameters_settable'):
            self.assertEqual(two.num_parameters_settable, expected)

        with self.subTest(msg='num_parameters'):
            self.assertEqual(two.num_parameters, expected)

    def test_empty_two_local(self):
        """Test the setup of an empty two-local circuit."""
        two = TwoLocal()

        with self.subTest(msg='0 qubits'):
            self.assertEqual(two.num_qubits, 0)

        with self.subTest(msg='no blocks are set'):
            self.assertListEqual(two.rotation_blocks, [])
            self.assertListEqual(two.entanglement_blocks, [])

        with self.subTest(msg='equal to empty circuit'):
            self.assertEqual(two, QuantumCircuit())

    @data('rx', RXGate(Parameter('p')), RXGate, 'circuit')
    def test_various_block_types(self, rot):
        """Test setting the rotation blocks to various type and assert the output type is RX."""
        if rot == 'circuit':
            rot = QuantumCircuit(1)
            rot.rx(Parameter('angle'), 0)

        two = TwoLocal(3, rot, 'cz', reps=1)
        self.assertEqual(len(two.rotation_blocks), 1)
        rotation = two.rotation_blocks[0]

        if isinstance(rot, QuantumCircuit):
            # decompose
            rotation = rotation.definition[0][0]

        self.assertIsInstance(rotation, RXGate)

    def test_parameter_setters(self):
        """Test different possibilities to set parameters."""
        two = TwoLocal(3, rotation_blocks='rx', entanglement='cz', reps=2)
        params = [0, 1, 2, Parameter('x'), Parameter('y'), Parameter('z'), 6, 7, 0]
        params_set = set(param for param in params if isinstance(param, Parameter))

        with self.subTest(msg='dict assign and copy'):
            ordered = two.ordered_parameters
            bound = two.assign_parameters(dict(zip(ordered, params)), inplace=False)
            self.assertEqual(bound.parameters, params_set)
            self.assertEqual(two.num_parameters, 9)

        with self.subTest(msg='list assign and copy'):
            ordered = two.ordered_parameters
            bound = two.assign_parameters(params, inplace=False)
            self.assertEqual(bound.parameters, params_set)
            self.assertEqual(two.num_parameters, 9)

        with self.subTest(msg='list assign inplace'):
            ordered = two.ordered_parameters
            two.assign_parameters(params, inplace=True)
            self.assertEqual(two.parameters, params_set)
            self.assertEqual(two.num_parameters, 3)
            self.assertEqual(two.num_parameters_settable, 9)

    def test_parameters_settable_is_constant(self):
        """Test the attribute num_parameters_settable does not change on parameter change."""
        two = TwoLocal(3, rotation_blocks='rx', entanglement='cz', reps=2)
        ordered_params = two.ordered_parameters

        x = Parameter('x')
        two.assign_parameters(dict(zip(ordered_params, [x] * two.num_parameters)), inplace=True)

        with self.subTest(msg='num_parameters collapsed to 1'):
            self.assertEqual(two.num_parameters, 1)

        with self.subTest(msg='num_parameters_settable remained constant'):
            self.assertEqual(two.num_parameters_settable, len(ordered_params))

    def test_iadd_to_circuit(self):
        """Test adding a two-local to an existing circuit."""
        two = TwoLocal(3, ['ry', 'rz'], 'cz', 'full', reps=1, insert_barriers=True)
        circuit = QuantumCircuit(3)
        circuit += two

        reference = QuantumCircuit(3)
        param_iter = iter(two.ordered_parameters)
        for i in range(3):
            reference.ry(next(param_iter), i)
        for i in range(3):
            reference.rz(next(param_iter), i)
        reference.barrier()
        reference.cz(0, 1)
        reference.cz(0, 2)
        reference.cz(1, 2)
        reference.barrier()
        for i in range(3):
            reference.ry(next(param_iter), i)
        for i in range(3):
            reference.rz(next(param_iter), i)

        self.assertCircuitEqual(circuit, reference)

    def test_adding_two(self):
        """Test adding two two-local circuits."""
        entangler_map = [[0, 3], [0, 2]]
        two = TwoLocal(4, [], 'cry', entangler_map, reps=1)
        circuit = two + two

        reference = QuantumCircuit(4)
        params = two.ordered_parameters
        for _ in range(2):
            reference.cry(params[0], 0, 3)
            reference.cry(params[1], 0, 2)

        self.assertCircuitEqual(reference, circuit)


if __name__ == '__main__':
    unittest.main()
