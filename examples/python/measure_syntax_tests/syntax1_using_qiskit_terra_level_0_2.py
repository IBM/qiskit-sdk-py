# -*- coding: utf-8 -*-

# This code is part of Qiskit.
#
# (C) Copyright IBM 2017, 2018.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""
Example showing how to use Qiskit-Terra at level 0 (novice).

This example shows the most basic way to user Terra. It builds some circuits
and runs them on both the BasicAer (local Qiskit provider) or IBMQ (remote IBMQ provider).

To control the compile parameters we have provided a transpile function which can be used 
as a level 1 user.

"""

# Import the Qiskit modules
from qiskit import QuantumCircuit, QiskitError
from qiskit import execute, BasicAer
from qiskit.assertions.asserts import Asserts
from qiskit.assertions.assertmanager import AssertManager

# making another circuit: superpositions
qc1 = QuantumCircuit(2, 2)
qc1.h([0,1])

# Insert a breakpoint, asserting that the 2 qubits are in a superposition state,
# with a critical p-value of 0.05.
breakpoint = qc1.assertsuperposition(.05, [0,1], [0,1])

qc1.measure([0,1], [0,1])

# setting up the backend
print("(BasicAER Backends)")
print(BasicAer.backends())

# running the breakpoint and the job
job_sim = execute([breakpoint, qc1], BasicAer.get_backend('qasm_simulator'))
sim_result = job_sim.result()

# Show the results
print("sim_result.get_counts(qc1) = ")
print(sim_result.get_counts(qc1))

# We obtain a dictionary of the results from our statistical test on our breakpoint
stat_outputs = AssertManager.stat_collect(breakpoint, sim_result)
print("Results of our statistical test:")
print(stat_outputs)
