# -*- coding: utf-8 -*-
# pylint: disable=invalid-name,no-value-for-parameter,broad-except

# Copyright 2018 IBM RESEARCH. All Rights Reserved.
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
"""Tests for bit reordering fix."""

import unittest
import qiskit
from qiskit.wrapper import register, available_backends, get_backend, execute
from .common import requires_qe_access, QiskitTestCase, slow_test


def lowest_pending_jobs(list_of_backends):
    """Returns the backend with lowest pending jobs."""
    by_pending_jobs = sorted(list_of_backends,
                             key=lambda x: get_backend(x).status['pending_jobs'])
    return by_pending_jobs[0]


@requires_qe_access
def _authenticate(QE_TOKEN, QE_URL):
    sim_backend = 'local_qasm_simulator'
    try:
        register(QE_TOKEN, QE_URL)
        real_backends = available_backends({'simulator': False})
        real_backend = lowest_pending_jobs(real_backends)
    except Exception:
        real_backend = None

    return sim_backend, real_backend


sim, real = _authenticate()


@unittest.skipIf(not real, 'no remote device available.')
class TestBitReordering(QiskitTestCase):
    """Test QISKit's fix for the ibmq hardware reordering bug.

    The bug will be fixed with the introduction of qobj,
    in which case these tests can be used to verify correctness.
    """
    @slow_test
    def test_basic_reordering(self):
        """a simple reordering within a 2-qubit register"""
        q = qiskit.QuantumRegister(2)
        c = qiskit.ClassicalRegister(2)
        circ = qiskit.QuantumCircuit(q, c)
        circ.h(q[0])
        circ.measure(q[0], c[1])
        circ.measure(q[1], c[0])

        shots = 2000
        result_real = execute(circ, real, {"shots": shots, "timeout": 300})
        result_sim = execute(circ, sim, {"shots": shots})
        counts_real = result_real.get_counts()
        counts_sim = result_sim.get_counts()
        threshold = 0.1 * shots
        self.assertDictAlmostEqual(counts_real, counts_sim, threshold)

    @slow_test
    def test_multi_register_reordering(self):
        """a more complicated reordering across 3 registers of different sizes"""
        q0 = qiskit.QuantumRegister(2)
        q1 = qiskit.QuantumRegister(2)
        q2 = qiskit.QuantumRegister(1)
        c0 = qiskit.ClassicalRegister(2)
        c1 = qiskit.ClassicalRegister(2)
        c2 = qiskit.ClassicalRegister(1)
        circ = qiskit.QuantumCircuit(q0, q1, q2, c0, c1, c2)
        circ.h(q0[0])
        circ.cx(q0[0], q2[0])
        circ.x(q1[1])
        circ.h(q2[0])
        circ.ccx(q2[0], q1[1], q1[0])
        circ.barrier()
        circ.measure(q0[0], c2[0])
        circ.measure(q0[1], c0[1])
        circ.measure(q1[0], c0[0])
        circ.measure(q1[1], c1[0])
        circ.measure(q2[0], c1[1])

        shots = 4000
        result_real = execute(circ, real, {"shots": shots, "timeout": 300})
        result_sim = execute(circ, sim, {"shots": shots})
        counts_real = result_real.get_counts()
        counts_sim = result_sim.get_counts()
        threshold = 0.2 * shots
        self.assertDictAlmostEqual(counts_real, counts_sim, threshold)


if __name__ == '__main__':
    unittest.main(verbosity=2)
