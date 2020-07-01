# -*- coding: utf-8 -*-

# This code is part of Qiskit.
#
# (C) Copyright IBM 2020.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

import unittest

import json
import os
from contextlib import contextmanager
from qiskit.test import QiskitTestCase

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.visualization.circuit_visualization import _matplotlib_circuit_drawer
from qiskit.circuit.library import (U3Gate, U2Gate, U1Gate, XGate, SwapGate,
                               MCXGate, YGate, HGate, ZGate, C4XGate, C3XGate, MSGate, RZZGate)
from qiskit.extensions import HamiltonianGate, UnitaryGate
from qiskit.circuit import Gate, Parameter
from qiskit.circuit.library import IQP

import math
import numpy as np
pi = np.pi

RESULTDIR = os.path.dirname(os.path.abspath(__file__))


def save_data(image_filename, testname):
    datafilename = 'result_test.json'
    if os.path.exists(datafilename):
        with open(datafilename, 'r') as datafile:
            data = json.load(datafile)
    else:
        data = {}
    data[image_filename] = {'testname': testname}
    with open(datafilename, 'w') as datafile:
        json.dump(data, datafile)


@contextmanager
def cwd(path):
    oldpwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(oldpwd)


def save_data_wrap(func, testname):
    def wrapper(*args, **kwargs):
        image_filename = kwargs['filename']
        with cwd(RESULTDIR):
            results = func(*args, **kwargs)
            save_data(image_filename, testname)
        return results

    return wrapper


class TestMatplotlibDrawer(QiskitTestCase):
    """Circuit MPL visualization"""

    def setUp(self):
        self.circuit_drawer = save_data_wrap(_matplotlib_circuit_drawer, str(self))

    def test_empty_circuit(self):
        """Test empty circuit"""
        circuit = QuantumCircuit()

        self.circuit_drawer(circuit, filename='empty_circut.png')

    def test_long_name(self):
        """Test to see that long register names can be seen completely
        As reported in #2605
        """

        # add a register with a very long name
        qr = QuantumRegister(4, 'veryLongQuantumRegisterName')
        # add another to make sure adjustments are made based on longest
        qrr = QuantumRegister(1, 'q0')
        circuit = QuantumCircuit(qr, qrr)

        # check gates are shifted over accordingly
        circuit.h(qr)
        circuit.h(qr)
        circuit.h(qr)

        self.circuit_drawer(circuit, filename='long_name.png')

    def test_conditional(self):
        """Test that circuits with conditionals draw correctly
        """
        qr = QuantumRegister(2, 'q')
        cr = ClassicalRegister(2, 'c')
        circuit = QuantumCircuit(qr, cr)

        # check gates are shifted over accordingly
        circuit.h(qr)
        circuit.measure(qr, cr)
        circuit.h(qr[0]).c_if(cr, 2)

        self.circuit_drawer(circuit, filename='conditional.png')

    def test_plot_barriers(self):
        """Test to see that plotting barriers works.
        If it is set to False, no blank columns are introduced"""

        # generate a circuit with barriers and other barrier like instructions in
        q = QuantumRegister(2, 'q')
        c = ClassicalRegister(2, 'c')
        circuit = QuantumCircuit(q, c)

        # check for barriers
        circuit.h(q[0])
        circuit.barrier()

        # check for other barrier like commands
        circuit.h(q[1])

        # this import appears to be unused, but is actually needed to get snapshot instruction
        import qiskit.extensions.simulator  # pylint: disable=unused-import
        circuit.snapshot('1')

        # check the barriers plot properly when plot_barriers= True
        self.circuit_drawer(circuit, filename='plot_barriers_true.png', plot_barriers=True)
        self.circuit_drawer(circuit, filename='plot_barriers_false.png', plot_barriers=False)

    def test_no_barriers_false(self):
        """Generate the same circuit as test_plot_barriers but without the barrier commands
         as this is what the circuit should look like when displayed with plot barriers false"""
        q1 = QuantumRegister(2, 'q')
        c1 = ClassicalRegister(2, 'c')
        circuit = QuantumCircuit(q1, c1)
        circuit.h(q1[0])
        circuit.h(q1[1])

        self.circuit_drawer(circuit, filename='no_barriers.png', plot_barriers=False)

    def test_fold_minus1(self):
        """Test to see that fold=-1 is no folding"""
        qr = QuantumRegister(2, 'q')
        cr = ClassicalRegister(1, 'c')
        circuit = QuantumCircuit(qr, cr)
        for _ in range(3):
            circuit.h(0)
            circuit.x(0)

        self.circuit_drawer(circuit, fold=-1, filename='fold_minus1.png')

    def test_fold_4(self):
        """Test to see that fold=4 is folding"""
        qr = QuantumRegister(2, 'q')
        cr = ClassicalRegister(1, 'c')
        circuit = QuantumCircuit(qr, cr)
        for _ in range(3):
            circuit.h(0)
            circuit.x(0)

        self.circuit_drawer(circuit, fold=4, filename='fold_4.png')

    def test_big_gates(self):
        """Test large gates with params"""
        pi = np.pi
        qr = QuantumRegister(6, 'q')
        circuit = QuantumCircuit(qr)
        A = [[6, 5, 3], [5, 4, 5], [3, 5, 1]]
        circuit.append(IQP(A), [0,1,2])

        desired_vector = [
            1 / math.sqrt(16) * complex(0, 1),
            1 / math.sqrt(8) * complex(1, 0),
            1 / math.sqrt(16) * complex(1, 1),
            0,
            0,
            1 / math.sqrt(8) * complex(1, 2),
            1 / math.sqrt(16) * complex(1, 0),
            0]

        circuit.initialize(desired_vector, [qr[3],qr[4],qr[5]])
        circuit.unitary([[1,0],[0,1]], [qr[0]])
        matrix = np.zeros((4, 4))
        theta = Parameter('theta')
        circuit.append(HamiltonianGate(matrix, theta), [qr[1], qr[2]])
        circuit = circuit.bind_parameters({theta: 1})
        circuit.isometry(np.eye(4, 4), [i for i in range(3,5)],[])

        self.circuit_drawer(circuit, filename='big_gates.png')


if __name__ == '__main__':
    unittest.main(verbosity=1)
