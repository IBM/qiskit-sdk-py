# This code is part of Qiskit.
#
# (C) Copyright IBM 2018, 2020.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

# pylint: disable=no-name-in-module,import-error


""" Test Operator construction, including OpPrimitives and singletons. """

import unittest
from test.python.opflow import QiskitOpflowTestCase
from ddt import ddt, data
import numpy

from qiskit.circuit import QuantumCircuit, Parameter
from qiskit.utils import QuantumInstance
from qiskit.opflow import (
    StateFn, Zero, One, H, X, I, Z, Plus, Minus, CircuitSampler, ListOp
)


@ddt
class TestStateOpMeasEvals(QiskitOpflowTestCase):
    """Tests of evals of Meas-Operator-StateFn combos."""

    def test_statefn_overlaps(self):
        """ state functions overlaps test """
        wf = (4 * StateFn({'101010': .5, '111111': .3})) + ((3 + .1j) * (Zero ^ 6))
        wf_vec = StateFn(wf.to_matrix())
        self.assertAlmostEqual(wf.adjoint().eval(wf), 14.45)
        self.assertAlmostEqual(wf_vec.adjoint().eval(wf_vec), 14.45)
        self.assertAlmostEqual(wf_vec.adjoint().eval(wf), 14.45)
        self.assertAlmostEqual(wf.adjoint().eval(wf_vec), 14.45)

    def test_wf_evals_x(self):
        """ wf evals x test """
        qbits = 4
        wf = ((Zero ^ qbits) + (One ^ qbits)) * (1 / 2 ** .5)
        # Note: wf = Plus^qbits fails because TensoredOp can't handle it.
        wf_vec = StateFn(wf.to_matrix())
        op = X ^ qbits
        # op = I^6
        self.assertAlmostEqual(wf.adjoint().eval(op.eval(wf)), 1)
        self.assertAlmostEqual(wf_vec.adjoint().eval(op.eval(wf)), 1)
        self.assertAlmostEqual(wf.adjoint().eval(op.eval(wf_vec)), 1)
        self.assertAlmostEqual(wf_vec.adjoint().eval(op.eval(wf_vec)), 1)

        # op = (H^X^Y)^2
        op = H ^ 6
        wf = ((Zero ^ 6) + (One ^ 6)) * (1 / 2 ** .5)
        wf_vec = StateFn(wf.to_matrix())
        # print(wf.adjoint().to_matrix() @ op.to_matrix() @ wf.to_matrix())
        self.assertAlmostEqual(wf.adjoint().eval(op.eval(wf)), .25)
        self.assertAlmostEqual(wf_vec.adjoint().eval(op.eval(wf)), .25)
        self.assertAlmostEqual(wf.adjoint().eval(op.eval(wf_vec)), .25)
        self.assertAlmostEqual(wf_vec.adjoint().eval(op.eval(wf_vec)), .25)

    def test_coefficients_correctly_propagated(self):
        """Test that the coefficients in SummedOp and states are correctly used."""
        try:
            from qiskit.providers.aer import Aer
        except Exception as ex:  # pylint: disable=broad-except
            self.skipTest("Aer doesn't appear to be installed. Error: '{}'".format(str(ex)))
            return
        with self.subTest('zero coeff in SummedOp'):
            op = 0 * (I + Z)
            state = Plus
            self.assertEqual((~StateFn(op) @ state).eval(), 0j)

        backend = Aer.get_backend('qasm_simulator')
        q_instance = QuantumInstance(backend, seed_simulator=97, seed_transpiler=97)
        op = I
        with self.subTest('zero coeff in summed StateFn and CircuitSampler'):
            state = 0 * (Plus + Minus)
            sampler = CircuitSampler(q_instance).convert(~StateFn(op) @ state)
            self.assertEqual(sampler.eval(), 0j)

        with self.subTest('coeff gets squared in CircuitSampler shot-based readout'):
            state = (Plus + Minus) / numpy.sqrt(2)
            sampler = CircuitSampler(q_instance).convert(~StateFn(op) @ state)
            self.assertAlmostEqual(sampler.eval(), 1+0j)

    def test_is_measurement_correctly_propagated(self):
        """Test if is_measurement property of StateFn is propagated to converted StateFn."""
        try:
            from qiskit.providers.aer import Aer
        except Exception as ex:  # pylint: disable=broad-except
            self.skipTest("Aer doesn't appear to be installed. Error: '{}'".format(str(ex)))
            return
        backend = Aer.get_backend('qasm_simulator')
        q_instance = QuantumInstance(backend)  # no seeds needed since no values are compared
        state = Plus
        sampler = CircuitSampler(q_instance).convert(~state @ state)
        self.assertTrue(sampler.oplist[0].is_measurement)

    def test_parameter_binding_on_listop(self):
        """Test passing a ListOp with differing parameters works with the circuit sampler."""
        try:
            from qiskit.providers.aer import Aer
        except Exception as ex:  # pylint: disable=broad-except
            self.skipTest("Aer doesn't appear to be installed. Error: '{}'".format(str(ex)))
            return
        x, y = Parameter('x'), Parameter('y')

        circuit1 = QuantumCircuit(1)
        circuit1.p(0.2, 0)
        circuit2 = QuantumCircuit(1)
        circuit2.p(x, 0)
        circuit3 = QuantumCircuit(1)
        circuit3.p(y, 0)

        bindings = {x: -0.4, y: 0.4}
        listop = ListOp([StateFn(circuit) for circuit in [circuit1, circuit2, circuit3]])

        sampler = CircuitSampler(Aer.get_backend('qasm_simulator'))
        sampled = sampler.convert(listop, params=bindings)

        self.assertTrue(all(len(op.parameters) == 0 for op in sampled.oplist))

    def test_list_op_eval_coeff_with_nonlinear_combofn(self):
        """Test evaluating a ListOp with non-linear combo function works with coefficients."""
        state = One
        op = ListOp(5 * [I], coeff=2, combo_fn=numpy.prod)
        expr1 = ~StateFn(op) @ state

        expr2 = ListOp(5 * [~state @ I @ state], coeff=2, combo_fn=numpy.prod)

        self.assertEqual(expr1.eval(), 2)  # if the coeff is propagated too far the result is 4
        self.assertEqual(expr2.eval(), 2)

    def test_single_parameter_binds(self):
        """Test passing parameter binds as a dictionary to the circuit sampler."""
        try:
            from qiskit.providers.aer import Aer
        except Exception as ex:  # pylint: disable=broad-except
            self.skipTest("Aer doesn't appear to be installed. Error: '{}'".format(str(ex)))
            return

        x = Parameter('x')
        circuit = QuantumCircuit(1)
        circuit.ry(x, 0)
        expr = ~StateFn(H) @ StateFn(circuit)

        sampler = CircuitSampler(Aer.get_backend('statevector_simulator'))

        res = sampler.convert(expr, params={x: 0}).eval()

        self.assertIsInstance(res, complex)

    @data('all', 'last')
    def test_circuit_sampler_caching(self, caching):
        """Test caching all operators works."""
        try:
            from qiskit.providers.aer import Aer
        except Exception as ex:  # pylint: disable=broad-except
            self.skipTest("Aer doesn't appear to be installed. Error: '{}'".format(str(ex)))
            return

        x = Parameter('x')
        circuit = QuantumCircuit(1)
        circuit.ry(x, 0)
        expr1 = ~StateFn(H) @ StateFn(circuit)
        expr2 = ~StateFn(X) @ StateFn(circuit)

        sampler = CircuitSampler(Aer.get_backend('statevector_simulator'), caching=caching)

        res1 = sampler.convert(expr1, params={x: 0}).eval()
        res2 = sampler.convert(expr2, params={x: 0}).eval()
        res3 = sampler.convert(expr1, params={x: 0}).eval()
        res4 = sampler.convert(expr2, params={x: 0}).eval()

        self.assertEqual(res1, res3)
        self.assertEqual(res2, res4)
        if caching == 'last':
            self.assertEqual(len(sampler._cached_ops.keys()), 1)
        else:
            self.assertEqual(len(sampler._cached_ops.keys()), 2)

    def test_global_phase_in_circuit_state_fn(self):
        """Test that circuits using isometry are evaluated correctly in CircuitStateFn."""
        vector = numpy.array([1, 2, 3, 1])
        circuit = QuantumCircuit(2)
        circuit.isometry(vector / numpy.linalg.norm(vector), [0, 1], None)
        result = (~StateFn(I ^ I) @ StateFn(circuit)).eval()
        self.assertAlmostEqual(result, 1+0j)


if __name__ == '__main__':
    unittest.main()
