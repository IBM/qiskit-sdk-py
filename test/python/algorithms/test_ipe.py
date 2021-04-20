# This code is part of Qiskit.
#
# (C) Copyright IBM 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Test iterative phase estimation"""

import math
import unittest
from test.python.algorithms import QiskitAlgorithmsTestCase
from ddt import ddt, data, unpack
from qiskit.algorithms.phase_estimators import IterativePhaseEstimation
import qiskit
from qiskit import QuantumCircuit
from qiskit.opflow import (H, X, Z, I)


@ddt
class TestIterativePhaseEstimation(QiskitAlgorithmsTestCase):
    """Evolution tests."""

    # pylint: disable=invalid-name
    def one_phase(self, unitary_circuit, state_preparation=None, num_iterations=6,
                  backend_type=None):
        """Run phase estimation with operator, eigenvalue pair `unitary_circuit`,
        `state_preparation`. Return the estimated phase as a value in :math:`[0,1)`.
        """
        if backend_type is None:
            backend_type = 'qasm_simulator'
        backend = qiskit.BasicAer.get_backend(backend_type)
        qi = qiskit.utils.QuantumInstance(backend=backend, shots=10000)
        p_est = IterativePhaseEstimation(num_iterations=num_iterations, quantum_instance=qi)
        result = p_est.estimate(unitary=unitary_circuit, state_preparation=state_preparation)
        phase = result.phase
        return phase

    @data((X.to_circuit(), 0.5, 'statevector_simulator'),
          (X.to_circuit(), 0.5, 'qasm_simulator'),
          (None, 0.0, 'qasm_simulator'))
    @unpack
    def test_qpe_Z(self, state_preparation, expected_phase, backend_type):
        """eigenproblem Z, |0> and |1>"""
        unitary_circuit = Z.to_circuit()
        phase = self.one_phase(unitary_circuit, state_preparation, backend_type=backend_type)
        self.assertEqual(phase, expected_phase)

    @data((H.to_circuit(), 0.0), ((H @ X).to_circuit(), 0.5))
    @unpack
    def test_qpe_X_plus_minus(self, state_preparation, expected_phase):
        """eigenproblem X, (|+>, |->)"""
        unitary_circuit = X.to_circuit()
        phase = self.one_phase(unitary_circuit, state_preparation)
        self.assertEqual(phase, expected_phase)

    @data((X.to_circuit(), 0.125), (I.to_circuit(), 0.875))
    @unpack
    def test_qpe_RZ(self, state_preparation, expected_phase):
        """eigenproblem RZ, (|0>, |1>)"""
        alpha = math.pi / 2
        unitary_circuit = QuantumCircuit(1)
        unitary_circuit.rz(alpha, 0)
        phase = self.one_phase(unitary_circuit, state_preparation)
        self.assertEqual(phase, expected_phase)

    def test_check_num_iterations(self):
        """test check for num_iterations greater than zero"""
        unitary_circuit = X.to_circuit()
        state_preparation = None
        with self.assertRaises(ValueError):
            self.one_phase(unitary_circuit, state_preparation, num_iterations=-1)


if __name__ == '__main__':
    unittest.main()
