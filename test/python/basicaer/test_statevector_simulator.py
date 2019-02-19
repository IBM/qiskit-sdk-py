# -*- coding: utf-8 -*-

# Copyright 2018, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

import unittest

from qiskit.providers.builtinsimulators import StatevectorSimulatorPy
from qiskit.test import ReferenceCircuits
from qiskit.test.providers import BackendTestCase


class StatevectorSimulatorTest(BackendTestCase):
    """Test BasicAer statevector simulator."""

    __test__ = True
    backend_cls = StatevectorSimulatorPy
    circuit = ReferenceCircuits.bell_no_measure()

    def test_run_circuit(self):
        """Test final state vector for single circuit run."""
        result = super().test_run_circuit()
        actual = result.get_statevector(self.circuit)

        # state is 1/sqrt(2)|00> + 1/sqrt(2)|11>, up to a global phase
        self.assertAlmostEqual((abs(actual[0]))**2, 1/2)
        self.assertEqual(actual[1], 0)
        self.assertEqual(actual[2], 0)
        self.assertAlmostEqual((abs(actual[3]))**2, 1/2)


if __name__ == '__main__':
    unittest.main()
