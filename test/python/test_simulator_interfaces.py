# -*- coding: utf-8 -*-
# pylint: disable=invalid-name,unused-import

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
"""Tests for checking qiskit interfaces to simulators."""

import unittest
import qiskit as qk
import qiskit.extensions.simulator
from qiskit.tools.qi.qi import state_fidelity
from qiskit.wrapper import register, execute
from .common import requires_qe_access, QiskitTestCase


class TestCrossSimulation(QiskitTestCase):
    """Test output consistency across simulators.
    """
    _desired_fidelity = 0.99

    def test_statevector(self):
        """statevector from a bell state"""
        q = qk.QuantumRegister(2)
        circ = qk.QuantumCircuit(q)
        circ.h(q[0])
        circ.cx(q[0], q[1])

        sim_cpp = 'local_statevector_simulator_cpp'
        sim_py = 'local_statevector_simulator_py'
        result_cpp = execute(circ, sim_cpp)
        result_py = execute(circ, sim_py)
        statevector_cpp = result_cpp.get_statevector()
        statevector_py = result_py.get_statevector()
        fidelity = state_fidelity(statevector_cpp, statevector_py)
        self.assertGreater(
            fidelity, self._desired_fidelity,
            "cpp vs. py statevector has low fidelity{0:.2g}.".format(fidelity))

    @requires_qe_access
    def test_qasm(self, QE_TOKEN, QE_URL):
        """counts from a GHZ state"""
        register(QE_TOKEN, QE_URL)
        q = qk.QuantumRegister(3)
        c = qk.ClassicalRegister(3)
        circ = qk.QuantumCircuit(q, c)
        circ.h(q[0])
        circ.cx(q[0], q[1])
        circ.cx(q[1], q[2])
        circ.measure(q, c)

        sim_cpp = 'local_qasm_simulator_cpp'
        sim_py = 'local_qasm_simulator_py'
        sim_ibmq = 'ibmq_qasm_simulator'
        sim_hpc = 'ibmq_qasm_simulator_hpc'
        shots = 2000
        result_cpp = execute(circ, sim_cpp, {'shots': shots})
        result_py = execute(circ, sim_py, {'shots': shots})
        result_ibmq = execute(circ, sim_ibmq, {'shots': shots})
        result_hpc = execute(circ, sim_hpc, {'shots': shots})
        counts_cpp = result_cpp.get_counts()
        counts_py = result_py.get_counts()
        counts_ibmq = result_ibmq.get_counts()
        counts_hpc = result_hpc.get_counts()
        self.assertDictAlmostEqual(counts_cpp, counts_py, shots*0.025)
        self.assertDictAlmostEqual(counts_py, counts_ibmq, shots*0.025)
        self.assertDictAlmostEqual(counts_ibmq, counts_hpc, shots*0.025)

    def test_qasm_snapshot(self):
        """snapshot a circuit at multiple places"""
        q = qk.QuantumRegister(3)
        c = qk.ClassicalRegister(3)
        circ = qk.QuantumCircuit(q, c)
        circ.h(q[0])
        circ.cx(q[0], q[1])
        circ.snapshot(1)
        circ.ccx(q[0], q[1], q[2])
        circ.snapshot(2)
        circ.reset(q)
        circ.snapshot(3)

        sim_cpp = 'local_qasm_simulator_cpp'
        sim_py = 'local_qasm_simulator_py'
        result_cpp = execute(circ, sim_cpp, {'shots': 2})
        result_py = execute(circ, sim_py, {'shots': 2})
        snapshots_cpp = result_cpp.get_snapshots()
        snapshots_py = result_py.get_snapshots()
        self.assertEqual(snapshots_cpp.keys(), snapshots_py.keys())
        self.assertEqual(len(snapshots_cpp['1']['quantum_state']),
                         len(snapshots_py['1']['quantum_state']))
        for k in snapshots_cpp.keys():
            fidelity = state_fidelity(snapshots_cpp[k]['quantum_state'][0],
                                      snapshots_py[k]['quantum_state'][0])
            self.assertGreater(fidelity, self._desired_fidelity)

    @requires_qe_access
    def test_qasm_reset_measure(self, QE_TOKEN, QE_URL):
        """counts from a qasm program with measure and reset in the middle"""
        register(QE_TOKEN, QE_URL)
        q = qk.QuantumRegister(3)
        c = qk.ClassicalRegister(3)
        circ = qk.QuantumCircuit(q, c)
        circ.h(q[0])
        circ.cx(q[0], q[1])
        circ.reset(q[0])
        circ.cx(q[1], q[2])
        circ.t(q)
        circ.measure(q[1], c[1])
        circ.h(q[2])
        circ.measure(q[2], c[2])

        # TODO: bring back online simulator tests when reset/measure doesn't
        # get rejected by the api
        sim_cpp = 'local_qasm_simulator_cpp'
        sim_py = 'local_qasm_simulator_py'
        # sim_ibmq = 'ibmq_qasm_simulator'
        # sim_hpc = 'ibmq_qasm_simulator_hpc'
        shots = 1000
        result_cpp = execute(circ, sim_cpp, {'shots': shots})
        result_py = execute(circ, sim_py, {'shots': shots})
        # result_ibmq = execute(circ, sim_ibmq, {'shots': shots})
        # result_hpc = execute(circ, sim_hpc, {'shots': shots})
        counts_cpp = result_cpp.get_counts()
        counts_py = result_py.get_counts()
        # counts_ibmq = result_ibmq.get_counts()
        # counts_hpc = result_hpc.get_counts()
        self.assertDictAlmostEqual(counts_cpp, counts_py, shots*0.025)
        # self.assertDictAlmostEqual(counts_py, counts_ibmq, shots*0.025)
        # self.assertDictAlmostEqual(counts_ibmq, counts_hpc, shots*0.025)


if __name__ == '__main__':
    unittest.main(verbosity=2)
