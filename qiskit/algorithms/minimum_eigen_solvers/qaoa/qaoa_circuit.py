# This code is part of Qiskit.
#
# (C) Copyright IBM 2018, 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Global X phases and parameterized problem hamiltonian."""

from typing import Optional, Union, cast, Set

import numpy as np

from qiskit import QuantumCircuit
from qiskit.circuit import Parameter, ParameterVector
from qiskit.circuit.library import BlueprintCircuit
from qiskit.opflow import OperatorBase, I, X, CircuitStateFn, H, CircuitOp, EvolutionFactory


class QAOACircuit(BlueprintCircuit):
    """Global X phases and parameterized problem hamiltonian."""

    def __init__(self,
                 cost_operator: OperatorBase,
                 param_p: int,
                 initial_state: Optional[QuantumCircuit] = None,
                 mixer_operator: Optional[Union[QuantumCircuit, OperatorBase]] = None,
                 name: str = "qaoa"):
        """
        Constructor, following the QAOA paper https://arxiv.org/abs/1411.4028

        Args:
            cost_operator: The operator representing the cost of the optimization problem,
                denoted as U(B, gamma) in the original paper.
            param_p: The integer parameter p, which determines the depth of the circuit,
                as specified in the original paper.
            initial_state: An optional initial state to use.
            mixer_operator: An optional custom mixer to use instead of the global X-rotations,
                denoted as U(B, beta) in the original paper. Can be an operator or
                an optionally parameterized quantum circuit.
            name: A name of the circuit, default 'qaoa'
        Raises:
            TypeError: invalid input
        """
        super().__init__(name=name)
        self._cost_operator = cost_operator
        self._param_p = param_p
        self._initial_state = initial_state
        self._mixer_operator = mixer_operator

        # set this circuit as a not-built circuit
        self._num_qubits = 0
        self._num_parameters = 0
        self._bounds = None
        self._mixer = None
        self._data = None

    def _check_configuration(self, raise_on_failure: bool = True) -> bool:
        valid = True

        if self._cost_operator is None:
            valid = False
            if raise_on_failure:
                raise AttributeError("The operator representing the cost of "
                                     "the optimization problem is not set")
        if self._param_p is None or self._param_p < 1:
            valid = False
            if raise_on_failure:
                raise AttributeError("The integer parameter p, which determines the depth "
                                     "of the circuit, either not set or set to non-positive value")

        return valid

    def _build(self) -> None:
        """Build the circuit."""
        if self._data:
            return

        self._check_configuration()
        self._data = []

        # calculate bounds, num_parameters, mixer
        self._calculate_parameters()

        # parametrize circuit and build it
        param_vector = ParameterVector("θ", self._num_parameters)
        circuit = self._construct_circuit(param_vector)

        # append(replace) the circuit to this
        self.add_register(circuit.num_qubits)
        self.compose(circuit, inplace=True)

    @property
    def parameters(self) -> Set[Parameter]:
        """Get the :class:`~qiskit.circuit.Parameter` objects in the circuit.

        Returns:
            A set containing the unbound circuit parameters.
        """
        self._build()
        return super().parameters

    def _calculate_parameters(self):
        self._num_qubits = self._cost_operator.num_qubits

        if isinstance(self._mixer_operator, QuantumCircuit):
            self._num_parameters = (1 + self._mixer_operator.num_parameters) * self._param_p
            self._bounds = [(None, None)] * self._param_p + [(None, None)] * \
                self._param_p * self._mixer_operator.num_parameters
            self._mixer = self._mixer_operator
        elif isinstance(self._mixer_operator, OperatorBase):
            self._num_parameters = 2 * self._param_p
            self._bounds = [(None, None)] * self._param_p + [(None, None)] * self._param_p
            self._mixer = self._mixer_operator
        elif self._mixer_operator is None:
            self._num_parameters = 2 * self._param_p
            self._bounds = [(None, None)] * self._param_p + [(0, 2 * np.pi)] * self._param_p
            # Mixer is just a sum of single qubit X's on each qubit. Evolving by this operator
            # will simply produce rx's on each qubit.
            mixer_terms = [(I ^ left) ^ X ^ (I ^ (self._num_qubits - left - 1))
                           for left in range(self._num_qubits)]
            self._mixer = sum(mixer_terms)

    def _construct_circuit(self, parameters) -> QuantumCircuit:
        """Construct a parametrized circuit."""
        if not len(parameters) == self._num_parameters:
            raise ValueError('Incorrect number of angles: expecting {}, but {} given.'.format(
                self._num_parameters, len(parameters)
            ))

        # initialize circuit, possibly based on given register/initial state
        if isinstance(self._initial_state, QuantumCircuit):
            circuit_op = CircuitStateFn(self._initial_state)
        else:
            circuit_op = (H ^ self._num_qubits)

        # iterate over layers
        for idx in range(self._param_p):
            # the first [:self._p] parameters are used for the cost operator,
            # so we apply them here
            circuit_op = (self._cost_operator * parameters[idx]).exp_i().compose(circuit_op)
            if isinstance(self._mixer, OperatorBase):
                mixer = cast(OperatorBase, self._mixer)
                # we apply beta parameter in case of operator based mixer.
                circuit_op = (mixer * parameters[idx + self._param_p]).exp_i().compose(circuit_op)
            else:
                # mixer as a quantum circuit that can be parameterized
                mixer = cast(QuantumCircuit, self._mixer)
                num_params = mixer.num_parameters
                # the remaining [self._p:] parameters are used for the mixer,
                # there may be multiple layers, so parameters are grouped by layers.
                param_values = parameters[self._param_p + num_params * idx:
                                          self._param_p + num_params * (idx + 1)]
                param_dict = dict(zip(mixer.parameters, param_values))
                mixer = mixer.assign_parameters(param_dict)
                circuit_op = CircuitOp(mixer).compose(circuit_op)

        evolution = EvolutionFactory.build(self._cost_operator)
        circuit_op = evolution.convert(circuit_op)
        return circuit_op.to_circuit()

    @property
    def cost_operator(self) -> OperatorBase:
        """Returns an operator representing the cost of the optimization problem."""
        return self._cost_operator

    @cost_operator.setter
    def cost_operator(self, cost_operator: OperatorBase) -> None:
        """Sets cost operator."""
        self._cost_operator = cost_operator
        self._data = None

    @property
    def param_p(self) -> int:
        """Returns the `p` parameter, which determines the depth of the circuit."""
        return self._param_p

    @param_p.setter
    def param_p(self, param_p: int) -> None:
        """Sets the `p` parameter."""
        self._param_p = param_p
        self._data = None

    @property
    def initial_state(self) -> Optional[QuantumCircuit]:
        """Returns an optional initial state as a circuit"""
        return self._initial_state

    @initial_state.setter
    def initial_state(self, initial_state: Optional[QuantumCircuit]) -> None:
        """Sets initial state."""
        self._initial_state = initial_state
        self._data = None

    @property
    def mixer_operator(self) -> Optional[Union[QuantumCircuit, OperatorBase]]:
        """Returns an optional mixer operator expressed as an operator or a quantum circuit."""
        return self._mixer_operator

    @mixer_operator.setter
    def mixer_operator(self, mixer_operator: Optional[Union[QuantumCircuit, OperatorBase]]) -> None:
        """Sets mixer operator."""
        self._mixer_operator = mixer_operator
        self._data = None
