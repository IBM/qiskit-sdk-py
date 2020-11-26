# -*- coding: utf-8 -*-

# This code is part of Qiskit.
#
# (C) Copyright IBM 2019, 2020.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""
CNOTDihedral operator class.

Methods for working with the CNOT-dihedral group.

Example:

  from dihedral import CNOTDihedral
  g = CNOTDihedral(3)  # create identity element on 3 qubits
  g.cnot(0,1)          # apply CNOT from qubit 0 to qubit 1
  g.flip(2)            # apply X on qubit 2
  g.phase(3, 1)        # apply T^3 on qubit 1
  print(g)             # pretty print g

  phase polynomial =
   0 + 3*x_0 + 3*x_1 + 2*x_0*x_1
  affine function =
   (x_0,x_0 + x_1,x_2 + 1)

 This means that |x_0 x_1 x_2> transforms to omega^{p(x)}|f(x)>,
 where omega = exp(i*pi/4) from which we can read that
 T^3 on qubit 1 AFTER CNOT_{0,1} is the same as
 T^3 on qubit 0, T^3 on qubit 1, and CS_{0,1} BEFORE CNOT_{0,1}.
"""

import itertools
import numpy as np

from qiskit.exceptions import QiskitError
from qiskit.quantum_info.operators.base_operator import BaseOperator
from qiskit.quantum_info.operators.operator import Operator
from qiskit.quantum_info.operators.pauli import Pauli
from qiskit.quantum_info.operators.scalar_op import ScalarOp
from qiskit.quantum_info.synthesis.cnotdihedral_decompose import decompose_cnotdihedral
from qiskit.circuit import QuantumCircuit, Instruction
from .dihedral_circuits import _append_circuit
from .polynomial import SpecialPolynomial


class CNOTDihedral(BaseOperator):
    """CNOT-dihedral Object Class.
    The CNOT-dihedral group on num_qubits qubits is generated by the gates
    CNOT, T and X.

    References:
        1. Shelly Garion and Andrew W. Cross, *On the structure of the CNOT-Dihedral group*,
           `arXiv:2006.12042 [quant-ph] <https://arxiv.org/abs/2006.12042>`_
        2. Andrew W. Cross, Easwar Magesan, Lev S. Bishop, John A. Smolin and Jay M. Gambetta,
           *Scalable randomised benchmarking of non-Clifford gates*,
           npj Quantum Inf 2, 16012 (2016).
    """

    def __init__(self, data, validate=True):
        """Initialize a CNOTDihedral operator object."""

        # Initialize from another CNOTDihedral by sharing the underlying
        # poly, linear and shift
        if isinstance(data, CNOTDihedral):
            self.linear = data.linear
            self.shift = data.shift
            self.poly = data.poly

        # Initialize from ScalarOp as N-qubit identity discarding any global phase
        elif isinstance(data, ScalarOp):
            if not data.is_unitary() or set(data._input_dims) != {2} or \
                    data.num_qubits is None:
                raise QiskitError("Can only initialize from N-qubit identity ScalarOp.")
            self._num_qubits = data.num_qubits
            # phase polynomial
            self.poly = SpecialPolynomial(self._num_qubits)
            # n x n invertible matrix over Z_2
            self.linear = np.eye(self._num_qubits, dtype=np.int8)
            # binary shift, n coefficients in Z_2
            self.shift = np.zeros(self._num_qubits, dtype=np.int8)

        # Initialize from a QuantumCircuit or Instruction object
        elif isinstance(data, (QuantumCircuit, Instruction)):
            self._num_qubits = data.num_qubits
            elem = self.from_circuit(data)
            self.poly = elem.poly
            self.linear = elem.linear
            self.shift = elem.shift

        # Construct the identity element on num_qubits qubits.
        elif isinstance(data, int):
            self._num_qubits = data
            # phase polynomial
            self.poly = SpecialPolynomial(self._num_qubits)
            # n x n invertible matrix over Z_2
            self.linear = np.eye(self._num_qubits, dtype=np.int8)
            # binary shift, n coefficients in Z_2
            self.shift = np.zeros(self._num_qubits, dtype=np.int8)

        elif isinstance(data, Pauli):
            self._num_qubits = data.num_qubits
            elem = self.from_circuit(data.to_instruction())
            self.poly = elem.poly
            self.linear = elem.linear
            self.shift = elem.shift

        # Initialize BaseOperator
        dims = self._num_qubits * (2,)
        super().__init__(dims, dims)

        # Validate the CNOTDihedral element
        if validate and not self.is_cnotdihedral():
            raise QiskitError('Invalid CNOTDihedsral element.')

    def _z2matmul(self, left, right):
        """Compute product of two n x n z2 matrices."""
        prod = np.mod(np.dot(left, right), 2)
        return prod

    def _z2matvecmul(self, mat, vec):
        """Compute mat*vec of n x n z2 matrix and vector."""
        prod = np.mod(np.dot(mat, vec), 2)
        return prod

    def __mul__(self, other):
        """Left multiplication self * other."""
        if self.num_qubits != other.num_qubits:
            raise QiskitError("Multiplication on different number of qubits.")
        result = CNOTDihedral(self.num_qubits)
        result.shift = [(x[0] + x[1]) % 2
                        for x in zip(self._z2matvecmul(self.linear, other.shift), self.shift)]
        result.linear = self._z2matmul(self.linear, other.linear)
        # Compute x' = B1*x + c1 using the p_j identity
        new_vars = []
        for i in range(self.num_qubits):
            support = np.arange(self.num_qubits)[np.nonzero(other.linear[i])]
            poly = SpecialPolynomial(self.num_qubits)
            poly.set_pj(support)
            if other.shift[i] == 1:
                poly = -1 * poly
                poly.weight_0 = (poly.weight_0 + 1) % 8
            new_vars.append(poly)
        # p' = p1 + p2(x')
        result.poly = other.poly + self.poly.evaluate(new_vars)
        return result

    def __rmul__(self, other):
        """Right multiplication other * self."""
        if self.num_qubits != other.num_qubits:
            raise QiskitError("Multiplication on different number of qubits.")
        result = CNOTDihedral(self.num_qubits)
        result.shift = [(x[0] + x[1]) % 2
                        for x in zip(self._z2matvecmul(other.linear,
                                                       self.shift),
                                     other.shift)]
        result.linear = self._z2matmul(other.linear, self.linear)
        # Compute x' = B1*x + c1 using the p_j identity
        new_vars = []
        for i in range(self.num_qubits):
            support = np.arange(self.num_qubits)[np.nonzero(self.linear[i])]
            poly = SpecialPolynomial(self.num_qubits)
            poly.set_pj(support)
            if other.shift[i] == 1:
                poly = -1 * poly
                poly.weight_0 = (poly.weight_0 + 1) % 8
            new_vars.append(poly)
        # p' = p1 + p2(x')
        result.poly = self.poly + other.poly.evaluate(new_vars)
        return result

    @property
    def key(self):
        """Return a string representation of a CNOT-dihedral object."""
        tup = (self.poly.key, tuple(map(tuple, self.linear)),
               tuple(self.shift))
        return str(tup)

    def __eq__(self, x):
        """Test equality."""
        return isinstance(x, CNOTDihedral) and self.key == x.key

    def cnot(self, i, j):
        """Apply a CNOT gate to this element.
        Left multiply the element by CNOT_{i,j}.
        """

        if not 0 <= i < self.num_qubits or not 0 <= j < self.num_qubits:
            raise QiskitError("cnot qubits are out of bounds.")
        self.linear[j] = (self.linear[i] + self.linear[j]) % 2
        self.shift[j] = (self.shift[i] + self.shift[j]) % 2

    def phase(self, k, i):
        """Apply an k-th power of T to this element.
        Left multiply the element by T_i^k.
        """
        if not 0 <= i < self.num_qubits:
            raise QiskitError("phase qubit out of bounds.")
        # If the kth bit is flipped, conjugate this gate
        if self.shift[i] == 1:
            k = (7*k) % 8
        # Take all subsets \alpha of the support of row i
        # of weight up to 3 and add k*(-2)**(|\alpha| - 1) mod 8
        # to the corresponding term.
        support = np.arange(self.num_qubits)[np.nonzero(self.linear[i])]
        subsets_2 = itertools.combinations(support, 2)
        subsets_3 = itertools.combinations(support, 3)
        for j in support:
            value = self.poly.get_term([j])
            self.poly.set_term([j], (value + k) % 8)
        for j in subsets_2:
            value = self.poly.get_term(list(j))
            self.poly.set_term(list(j), (value + -2 * k) % 8)
        for j in subsets_3:
            value = self.poly.get_term(list(j))
            self.poly.set_term(list(j), (value + 4 * k) % 8)

    def flip(self, i):
        """Apply X to this element.
        Left multiply the element by X_i.
        """
        if not 0 <= i < self.num_qubits:
            raise QiskitError("flip qubit out of bounds.")
        self.shift[i] = (self.shift[i] + 1) % 2

    def __str__(self):
        """Return formatted string representation."""
        out = "phase polynomial = \n"
        out += str(self.poly)
        out += "\naffine function = \n"
        out += " ("
        for row in range(self.num_qubits):
            wrote = False
            for col in range(self.num_qubits):
                if self.linear[row][col] != 0:
                    if wrote:
                        out += (" + x_" + str(col))
                    else:
                        out += ("x_" + str(col))
                        wrote = True
            if self.shift[row] != 0:
                out += " + 1"
            if row != self.num_qubits - 1:
                out += ","
        out += ")\n"
        return out

    def _add(self, other, qargs=None):
        """Not implemented."""
        raise NotImplementedError(
            "{} does not support addition".format(type(self)))

    def _multiply(self, other):
        """Not implemented."""
        raise NotImplementedError(
            "{} does not support scalar multiplication".format(type(self)))

    def to_circuit(self):
        """Return a QuantumCircuit implementing the CNOT-Dihedral element.

        Return:
            QuantumCircuit: a circuit implementation of the CNOTDihedral object.
        Remark:
            Decompose 1 and 2-qubit CNOTDihedral elements.

        References:
            1. Shelly Garion and Andrew W. Cross, *On the structure of the CNOT-Dihedral group*,
               `arXiv:2006.12042 [quant-ph] <https://arxiv.org/abs/2006.12042>`_
            2. Andrew W. Cross, Easwar Magesan, Lev S. Bishop, John A. Smolin and Jay M. Gambetta,
               *Scalable randomised benchmarking of non-Clifford gates*,
               npj Quantum Inf 2, 16012 (2016).
        """
        return decompose_cnotdihedral(self)

    def to_instruction(self):
        """Return a Gate instruction implementing the CNOTDihedral object."""
        return self.to_circuit().to_gate()

    def from_circuit(self, circuit):
        """Initialize from a QuantumCircuit or Instruction.

        Args:
            circuit (QuantumCircuit or ~qiskit.circuit.Instruction):
                instruction to initialize.
        Returns:
            CNOTDihedral: the CNOTDihedral object for the circuit.
        Raises:
            QiskitError: if the input instruction is not CNOTDihedral or contains
                         classical register instruction.
        """
        if not isinstance(circuit, (QuantumCircuit, Instruction)):
            raise QiskitError("Input must be a QuantumCircuit or Instruction")

        # Convert circuit to an instruction
        if isinstance(circuit, QuantumCircuit):
            circuit = circuit.to_instruction()

        # Initialize an identity CNOTDihedral object
        elem = CNOTDihedral(self.num_qubits)
        _append_circuit(elem, circuit)
        return elem

    def to_matrix(self):
        """Convert operator to Numpy matrix."""
        return self.to_operator().data

    def to_operator(self):
        """Convert to an Operator object."""
        return Operator(self.to_instruction())

    def compose(self, other, qargs=None, front=False):
        """Return the composed operator.

        Args:
            other (CNOTDihedral): an operator object.
            qargs (None): using specific qargs is not implemented for this operator.
            front (bool): if True compose using right operator multiplication,
                          instead of left multiplication [default: False].
        Returns:
            CNOTDihedral: The operator self @ other.
        Raises:
            QiskitError: if operators have incompatible dimensions for
                         composition.
            NotImplementedError: if qargs is not None.

        Additional Information:
            Composition (``@``) is defined as `left` matrix multiplication for
            matrix operators. That is that ``A @ B`` is equal to ``B * A``.
            Setting ``front=True`` returns `right` matrix multiplication
            ``A * B`` and is equivalent to the :meth:`dot` method.
        """
        if qargs is not None:
            raise NotImplementedError("compose method does not support qargs.")
        if self.num_qubits != other.num_qubits:
            raise QiskitError("Incompatible dimension for composition")
        if front:
            other = self * other
        else:
            other = other * self
        other.poly.weight_0 = 0  # set global phase
        return other

    def dot(self, other, qargs=None):
        """Return the right multiplied operator self * other.

        Args:
            other (CNOTDihedral): an operator object.
            qargs (None): using specific qargs is not implemented for this operator.
        Returns:
            CNOTDihedral: The operator self * other.
        Raises:
            QiskitError: if operators have incompatible dimensions for composition.
            NotImplementedError: if qargs is not None.
        """
        if qargs is not None:
            raise NotImplementedError("dot method does not support qargs.")
        if self.num_qubits != other.num_qubits:
            raise QiskitError("Incompatible dimension for composition")
        other = self * other
        other.poly.weight_0 = 0  # set global phase
        return other

    def _tensor_product(self, other, reverse=False):
        """Returns the tensor product operator.

         Args:
             other (CNOTDihedral): another operator subclass object.
             reverse (bool): If False return self tensor other,
                            if True return other tensor self [Default: False].
         Returns:
             CNOTDihedral: the tensor product operator: self tensor other.
         Raises:
             QiskitError: if other cannot be converted into an CNOTDihderal object.
        """

        if not isinstance(other, CNOTDihedral):
            raise QiskitError("Tensored element is not a CNOTDihderal object.")

        if reverse:
            elem0 = self
            elem1 = other
        else:
            elem0 = other
            elem1 = self

        result = CNOTDihedral(elem0.num_qubits + elem1.num_qubits)
        linear = np.block([[elem0.linear,
                            np.zeros((elem0.num_qubits, elem1.num_qubits), dtype=np.int8)],
                           [np.zeros((elem1.num_qubits, elem0.num_qubits), dtype=np.int8),
                            elem1.linear]])
        result.linear = linear
        shift = np.block([elem0.shift, elem1.shift])
        result.shift = shift

        for i in range(elem0.num_qubits):
            value = elem0.poly.get_term([i])
            result.poly.set_term([i], value)
            for j in range(i):
                value = elem0.poly.get_term([j, i])
                result.poly.set_term([j, i], value)
                for k in range(j):
                    value = elem0.poly.get_term([k, j, i])
                    result.poly.set_term([k, j, i], value)

        for i in range(elem1.num_qubits):
            value = elem1.poly.get_term([i])
            result.poly.set_term([i + elem0.num_qubits], value)
            for j in range(i):
                value = elem1.poly.get_term([j, i])
                result.poly.set_term([j + elem0.num_qubits, i + elem0.num_qubits], value)
                for k in range(j):
                    value = elem1.poly.get_term([k, j, i])
                    result.poly.set_term([k + elem0.num_qubits, j + elem0.num_qubits,
                                          i + elem0.num_qubits], value)

        return result

    def tensor(self, other):
        """Return the tensor product operator: self tensor other.

         Args:
             other (CNOTDihedral): an operator subclass object.
         Returns:
             CNOTDihedral: the tensor product operator: self tensor other.
         """

        return self._tensor_product(other, reverse=True)

    def expand(self, other):
        """Return the tensor product operator: other tensor self.

         Args:
             other (CNOTDihedral): an operator subclass object.
         Returns:
             CNOTDihedral: the tensor product operator: other tensor other.
         """

        return self._tensor_product(other, reverse=False)

    def adjoint(self):
        """Return the conjugate transpose of the CNOTDihedral element"""

        circ = self.to_instruction()
        result = self.from_circuit(circ.inverse())
        return result

    def conjugate(self):
        """Return the conjugate of the CNOTDihedral element."""
        circ = self.to_instruction()
        new_circ = QuantumCircuit(self.num_qubits)
        qargs = list(range(self.num_qubits))
        for instr, qregs, _ in circ.definition:
            new_qubits = [qargs[tup.index] for tup in qregs]
            if instr.name == 'p':
                params = 2 * np.pi - instr.params[0]
                instr.params[0] = params
                new_circ.append(instr, new_qubits)
            else:
                new_circ.append(instr, new_qubits)
        result = self.from_circuit(new_circ)
        return result

    def transpose(self):
        """Return the transpose of the CNOT-Dihedral element."""

        circ = self.to_instruction()
        result = self.from_circuit(circ.reverse_ops())
        return result

    def is_cnotdihedral(self):
        """Return True if input is a CNOTDihedral element."""

        if self.poly.weight_0 != 0 or \
                len(self.poly.weight_1) != self.num_qubits or \
                len(self.poly.weight_2) != int(self.num_qubits * (self.num_qubits - 1) / 2) \
                or len(self.poly.weight_3) != int(self.num_qubits * (self.num_qubits - 1)
                                                  * (self.num_qubits - 2) / 6):
            return False
        if (self.linear).shape != (self.num_qubits, self.num_qubits) or \
                len(self.shift) != self.num_qubits or \
                not np.allclose((np.linalg.det(self.linear) % 2), 1):
            return False
        if not (set(self.poly.weight_1.flatten())).issubset({0, 1, 2, 3, 4, 5, 6, 7}) or \
                not (set(self.poly.weight_2.flatten())).issubset({0, 2, 4, 6}) or \
                not (set(self.poly.weight_3.flatten())).issubset({0, 4}):
            return False
        if not (set(self.shift.flatten())).issubset({0, 1}) or \
                not (set(self.linear.flatten())).issubset({0, 1}):
            return False
        return True
