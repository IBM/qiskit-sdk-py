# This code is part of Qiskit.
#
# (C) Copyright IBM 2020
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""
Simulator command to perform multiple pauli gates in a single pass
"""
from qiskit.circuit.quantumregister import QuantumRegister
from qiskit.circuit.library.standard_gates.i import IGate
from qiskit.circuit.library.standard_gates.x import XGate
from qiskit.circuit.library.standard_gates.y import YGate
from qiskit.circuit.library.standard_gates.z import ZGate

from qiskit.circuit.gate import Gate
from qiskit.circuit.exceptions import CircuitError

class PauliGate(Gate):
    r"""A multi-qubit Pauli gate.

        This gate exists for optimization purposes for the
        quantum statevector simulation, since applying multiple
        pauli gates to different qubits at once can be done via
        a single pass on the statevector.

        The functionality is equivalent to applying
        the pauli gates sequentially using standard Qiskit gates
        """

    def __init__(self, label="I"):
        if isinstance(label, float):
            label = "I"
        self.pauli_string = label
        super().__init__('pauli', len(label), [self.pauli_string[::-1]])

    def _define(self):
        """
        gate pauli (p1 a1,...,pn an) { p1 a1; ... ; pn an; }
        """
        # pylint: disable=cyclic-import
        from qiskit.circuit.quantumcircuit import QuantumCircuit
        gates = {'I': IGate, 'X': XGate, 'Y': YGate, 'Z': ZGate}
        q = QuantumRegister(len(self.pauli_string), 'q')
        qc = QuantumCircuit(q,
                            name='{}({})'.format(self.name, self.pauli_string))

        rules = [(gates[p](), [q[i]], [])
                 for (i, p) in enumerate(reversed(self.pauli_string))]
        qc._data = rules
        self.definition = qc

    def inverse(self):
        r"""Return inverted pauli gate (itself)."""
        return PauliGate(self.pauli_string)  # self-inverse

    def to_matrix(self):
        """Return a Numpy.array for the pauli gate.
        i.e. tensor product of the paulis"""
        from qiskit.quantum_info import Pauli
        return Pauli(label=self.pauli_string).to_matrix()

    def validate_parameter(self, parameter):
        if isinstance(parameter, str):
            if all([c in ["I", "X", "Y", "Z"] for c in parameter]):
                return parameter
            else:
                raise CircuitError("Parameter string {0} should contain only "
                                   "'I', 'X', 'Y', 'Z' characters")
        else:
            raise CircuitError("Parameter {0} should be a string of "
                               "'I', 'X', 'Y', 'Z' characters")
