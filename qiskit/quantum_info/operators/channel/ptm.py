# -*- coding: utf-8 -*-

# Copyright 2019, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.
"""
Pauli Transfer Matrix (PTM) representation of a Quantum Channel.

The PTM is the n-qubit superoperator defined with respect to vectorization in
the Pauli basis. For a quantum channel E, the PTM is defined by

    PTM_{i,j} = Tr[P_i.E(P_j)]

where [P_i, i=0,...4^{n-1}] is the n-qubit Pauli basis in lexicographic order.

Evolution is given by

    |E(ρ)⟩⟩_p = PTM|ρ⟩⟩_p

where |A⟩⟩_p denotes vectorization in the Pauli basis: ⟨i|A⟩⟩_p = Tr[P_i.A]

See [1] for further details.

References:
    [1] C.J. Wood, J.D. Biamonte, D.G. Cory, Quant. Inf. Comp. 15, 0579-0811 (2015)
        Open access: arXiv:1111.6950 [quant-ph]
"""

from numbers import Number

import numpy as np

from qiskit.qiskiterror import QiskitError
from .basechannel import QuantumChannel
from .choi import Choi
from .superop import SuperOp
from .transformations import _to_ptm


class PTM(QuantumChannel):
    """Pauli transfer matrix (PTM) representation of a quantum channel.

    The PTM is the Pauli-basis representation of the PTM.
    """

    def __init__(self, data, input_dim=None, output_dim=None):
        # Check if input is a quantum channel object
        # If so we disregard the dimension kwargs
        if issubclass(data.__class__, QuantumChannel):
            input_dim, output_dim = data.dims
            ptm = _to_ptm(data.rep, data._data, input_dim, output_dim)
        else:
            # Should we force this to be real?
            ptm = np.array(data, dtype=complex)
            # Determine input and output dimensions
            dout, din = ptm.shape
            if output_dim is None:
                output_dim = int(np.sqrt(dout))
            if input_dim is None:
                input_dim = int(np.sqrt(din))
            # Check dimensions
            if output_dim**2 != dout or input_dim**2 != din or input_dim != output_dim:
                raise QiskitError(
                    "Invalid input and output dimension for PTM input.")
            nqubits = int(np.log2(input_dim))
            if 2**nqubits != input_dim:
                raise QiskitError(
                    "Input is not an n-qubit Pauli transfer matrix.")
        super().__init__('PTM', ptm, input_dim, output_dim)

    @property
    def _bipartite_shape(self):
        """Return the shape for bipartite matrix"""
        return (self._output_dim, self._output_dim, self._input_dim,
                self._input_dim)

    def _evolve(self, state):
        """Evolve a quantum state by the QuantumChannel.

        Args:
            state (QuantumState): The input statevector or density matrix.

        Returns:
            DensityMatrix: the output quantum state as a density matrix.
        """
        return SuperOp(self)._evolve(state)

    def is_cptp(self):
        """Return True if completely-positive trace-preserving."""
        # We convert to the Choi representation to check if CPTP
        tmp = Choi(self)
        return tmp.is_cptp()

    def conjugate(self):
        """Return the conjugate of the QuantumChannel."""
        # Since conjugation is basis dependent we transform
        # to the SuperOp representation to compute the
        # conjugate channel
        return PTM(SuperOp(self).conjugate())

    def transpose(self):
        """Return the transpose of the QuantumChannel."""
        # Since conjugation is basis dependent we transform
        # to the SuperOp representation to compute the
        # conjugate channel
        return PTM(SuperOp(self).transpose())

    def compose(self, other, front=False):
        """Return the composition channel self∘other.

        Args:
            other (QuantumChannel): a quantum channel subclass.
            front (bool): If False compose in standard order other(self(input))
                          otherwise compose in reverse order self(other(input))
                          [default: False]

        Returns:
            PTM: The composition channel as a PTM object.

        Raises:
            QiskitError: if other is not a QuantumChannel subclass, or
            has incompatible dimensions.
        """
        if not issubclass(other.__class__, QuantumChannel):
            raise QiskitError('other is not a QuantumChannel subclass')
        # Check dimensions match up
        if front and self._input_dim != other._output_dim:
            raise QiskitError(
                'input_dim of self must match output_dim of other')
        if not front and self._output_dim != other._input_dim:
            raise QiskitError(
                'input_dim of other must match output_dim of self')
        # Convert other to PTM
        if not isinstance(other, PTM):
            other = PTM(other)

        if front:
            # Composition A(B(input))
            input_dim = other._input_dim
            output_dim = self._output_dim
            return PTM(np.dot(self._data, other.data), input_dim, output_dim)
        # Composition B(A(input))
        input_dim = self._input_dim
        output_dim = other._output_dim
        return PTM(np.dot(other.data, self._data), input_dim, output_dim)

    def tensor(self, other):
        """Return the tensor product channel self ⊗ other.

        Args:
            other (QuantumChannel): a quantum channel subclass.

        Returns:
            PTM: the tensor product channel self ⊗ other as a PTM object.

        Raises:
            QiskitError: if other is not a QuantumChannel subclass.
        """
        return self._tensor_product(other, reverse=False)

    def expand(self, other):
        """Return the tensor product channel other ⊗ self.

        Args:
            other (QuantumChannel): a quantum channel subclass.

        Returns:
            PTM: the tensor product channel other ⊗ self as a PTM object.

        Raises:
            QiskitError: if other is not a QuantumChannel subclass.
        """
        return self._tensor_product(other, reverse=True)

    def add(self, other):
        """Return the QuantumChannel self + other.

        Args:
            other (QuantumChannel): a quantum channel subclass.

        Returns:
            PTM: the linear addition self + other as a PTM object.

        Raises:
            QiskitError: if other is not a QuantumChannel subclass, or
            has incompatible dimensions.
        """
        if not issubclass(other.__class__, QuantumChannel):
            raise QiskitError('other is not a QuantumChannel subclass')
        if self.dims != other.dims:
            raise QiskitError("other QuantumChannel dimensions are not equal")
        if not isinstance(other, PTM):
            other = PTM(other)
        input_dim, output_dim = self.dims
        return PTM(self._data + other.data, input_dim, output_dim)

    def subtract(self, other):
        """Return the QuantumChannel self - other.

        Args:
            other (QuantumChannel): a quantum channel subclass.

        Returns:
            PTM: the linear subtraction self - other as PTM object.

        Raises:
            QiskitError: if other is not a QuantumChannel subclass, or
            has incompatible dimensions.
        """
        if not issubclass(other.__class__, QuantumChannel):
            raise QiskitError('other is not a QuantumChannel subclass')
        if self.dims != other.dims:
            raise QiskitError("other QuantumChannel dimensions are not equal")
        if not isinstance(other, PTM):
            other = PTM(other)
        input_dim, output_dim = self.dims
        return PTM(self._data - other.data, input_dim, output_dim)

    def multiply(self, other):
        """Return the QuantumChannel self + other.

        Args:
            other (complex): a complex number.

        Returns:
            PTM: the scalar multiplication other * self as a PTM object.

        Raises:
            QiskitError: if other is not a valid scalar.
        """
        if not isinstance(other, Number):
            raise QiskitError("other is not a number")
        input_dim, output_dim = self.dims
        return PTM(other * self._data, input_dim, output_dim)

    def _tensor_product(self, other, reverse=False):
        """Return the tensor product channel.

        Args:
            other (QuantumChannel): a quantum channel subclass.
            reverse (bool): If False return self ⊗ other, if True return
                            if True return (other ⊗ self) [Default: False
        Returns:
            PTM: the tensor product channel as a PTM object.

        Raises:
            QiskitError: if other is not a QuantumChannel subclass.
        """
        # Convert other to PTM
        if not issubclass(other.__class__, QuantumChannel):
            raise QiskitError('other is not a QuantumChannel subclass')
        if not isinstance(other, PTM):
            other = PTM(other)
        # Combined channel dimensions
        a_in, a_out = self.dims
        b_in, b_out = other.dims
        input_dim = a_in * b_in
        output_dim = a_out * b_out
        if reverse:
            data = np.kron(other.data, self._data)
        else:
            data = np.kron(self._data, other.data)
        return PTM(data, input_dim, output_dim)
