# -*- coding: utf-8 -*-

# This code is part of Qiskit.
#
# (C) Copyright IBM 2017.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""
Assertion of classical states.
"""
from qiskit.circuit.instruction import Instruction
from qiskit.circuit.measure import Measure
from qiskit.circuit.asserts import Asserts
from qiskit.circuit.quantumcircuit import QuantumCircuit
from qiskit.exceptions import QiskitError
from random import randint
from scipy.stats import chisquare

class AssertClassical(Asserts):
    """Assertion of classical states
       and Quantum measurement in the computational basis."""
    def __init__(self,qubit,cbit,pcrit,expval):
        super().__init__()
        self._type = "classical"
        self._pcrit = pcrit
        self._expval = expval

    def get_stats(results):
        counts = results.get_counts()
        res_list = []
        exp_list = []
        numshots = sum(list(exp_results.values()))
        for key, value in exp_results.items():
            res_list.append(value)
            if int(key) == self._expval:
                exp_list.append(numshots)
            else:
                exp_list.append(0)
        print("exp_list = ")
        print(exp_list)
        print("rest_list = ")
        print(res_list)
        chisq, pval = (chisquare(res_list, f_exp = exp_list))
        print("chisq, pval = ")
        print(chisq, pval)
        return (chisq, pval)


def assertclassical(self, expval, qubit, cbit):
    """Create classical assertion

    Args:
        expval: integer
        qubit (QuantumRegister|list|tuple): quantum register
        cbit (ClassicalRegister|list|tuple): classical register

    Returns:
        qiskit.QuantumCircuit: copy of quantum circuit at the assert point.

    Raises:
        QiskitError: if qubit is not in this circuit or bad format;
            if cbit is not in this circuit or not creg.
    """
    randString = str(randint(0, 1000000000))
    theClone = self.copy("breakpoint"+randString)
    Asserts.StatOutputs[theClone.name] = {"type": "Classical", "expval": expval}
    theClone.append(AssertClassical(), [qubit], [cbit])
    return theClone

QuantumCircuit.assertclassical = assertclassical
