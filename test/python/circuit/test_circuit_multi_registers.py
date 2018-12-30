# -*- coding: utf-8 -*-

# Copyright 2018, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

# pylint: disable=unused-import
# pylint: disable=redefined-builtin

"""Test Qiskit's QuantumCircuit class for multiple registers."""

import os
import tempfile
import unittest

from qiskit import QuantumRegister, ClassicalRegister, QuantumCircuit
from qiskit import QiskitError
from qiskit.converters.circuit_to_dag import circuit_to_dag
from qiskit.test import QiskitTestCase


class TestCircuitMultiRegs(QiskitTestCase):
    """QuantumCircuit Qasm tests."""

    def test_circuit_multi(self):
        """Test circuit multi regs declared at start.
        """
        qreg0 = QuantumRegister(2, 'q0')
        creg0 = ClassicalRegister(2, 'c0')
        qreg1 = QuantumRegister(2, 'q1')
        creg1 = ClassicalRegister(2, 'c1')
        circ = QuantumCircuit(qreg0, qreg1)
        circ.x(qreg0[1])
        circ.x(qreg1[0])

        meas = QuantumCircuit(qreg0, qreg1, creg0, creg1)
        meas.measure(qreg0, creg0)
        meas.measure(qreg1, creg1)

        qc = circ + meas

        circ2 = QuantumCircuit()
        circ2.add_register(qreg0)
        circ2.add_register(qreg1)
        circ2.x(qreg0[1])
        circ2.x(qreg1[0])

        meas2 = QuantumCircuit()
        meas2.add_register(qreg0)
        meas2.add_register(qreg1)
        meas2.add_register(creg0)
        meas2.add_register(creg1)
        meas2.measure(qreg0, creg0)
        meas2.measure(qreg1, creg1)

        qc2 = circ2 + meas2

        dag_qc = circuit_to_dag(qc)
        dag_qc2 = circuit_to_dag(qc2)
        dag_circ2 = circuit_to_dag(circ2)
        dag_circ = circuit_to_dag(circ)

        self.assertEqual(dag_qc, dag_qc2)
        self.assertEqual(dag_circ, dag_circ2)
