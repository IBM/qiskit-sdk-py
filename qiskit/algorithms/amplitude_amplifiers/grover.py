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

"""Grover's search algorithm."""

from typing import Optional, Union, Dict, List, Callable
import logging
import operator
import math
import numpy as np

from qiskit import ClassicalRegister, QuantumCircuit
from qiskit.circuit.library import GroverOperator
from qiskit.providers import Backend
from qiskit.providers import BaseBackend
from qiskit.quantum_info import Statevector

from qiskit.utils import QuantumInstance, algorithm_globals
from qiskit.quantum_info import partial_trace
from ..algorithm_result import AlgorithmResult
from ..exceptions import AlgorithmError


logger = logging.getLogger(__name__)


class Grover:
    r"""Grover's Search algorithm.

    Grover's Search [1, 2] is a well known quantum algorithm for that can be used for
    searching through unstructured collections of records for particular targets
    with quadratic speedup compared to classical algorithms.

    Given a set :math:`X` of :math:`N` elements :math:`X=\{x_1,x_2,\ldots,x_N\}`
    and a boolean function :math:`f : X \rightarrow \{0,1\}`, the goal of an
    unstructured-search problem is to find an element :math:`x^* \in X` such
    that :math:`f(x^*)=1`.

    The search is called *unstructured* because there are no guarantees as to how
    the database is ordered.  On a sorted database, for instance, one could perform
    binary search to find an element in :math:`\mathbb{O}(\log N)` worst-case time.
    Instead, in an unstructured-search problem, there is no prior knowledge about
    the contents of the database. With classical circuits, there is no alternative
    but to perform a linear number of queries to find the target element.
    Conversely, Grover's Search algorithm allows to solve the unstructured-search
    problem on a quantum computer in :math:`\mathcal{O}(\sqrt{N})` queries.

    To carry out this search a so-called oracle is required, that flags a good element/state.
    The action of the oracle :math:`\mathcal{S}_f` is

    .. math::

        \mathcal{S}_f |x\rangle = (-1)^{f(x)} |x\rangle,

    i.e. it flips the phase of the state :math:`|x\rangle` if :math:`x` is a hit.
    The details of how :math:`S_f` works are unimportant to the algorithm; Grover's
    search algorithm treats the oracle as a black box.

    This class supports oracles in form of :class:`~qiskit.QuantumCircuit`

    With oracle at hand, Grover's Search constructs the Grover operator to amplify the amplitudes
    of the good states:

    .. math::

        \mathcal{Q} = H^{\otimes n} \mathcal{S}_0 H^{\otimes n} \mathcal{S}_f
                    = D \mathcal{S}_f,

    where :math:`\mathcal{S}_0` flips the phase of the all-zero state and acts as identity
    on all other states. Sometimes the first three operands are summarized as diffusion operator,
    which implements a reflection over the equal superposition state.

    If the number of solutions is known, we can calculate how often :math:`\mathcal{Q}` should be
    applied to find a solution with very high probability, see the method
    `optimal_num_iterations`. If the number of solutions is unknown, the algorithm tries different
    powers of Grover's operator, see the `iterations` argument, and after each iteration checks
    if a good state has been measured using `good_state`.

    The generalization of Grover's Search, Quantum Amplitude Amplification [3] uses a modified
    version of :math:`\mathcal{Q}` where the diffusion operator does not reflect about the
    equal superposition state, but another state specified via an operator :math:`\mathcal{A}`:

    .. math::

        \mathcal{Q} = \mathcal{A} \mathcal{S}_0 \mathcal{A}^\dagger \mathcal{S}_f.

    For more information, see the :class:`~qiskit.circuit.library.GroverOperator` in the
    circuit library.

    References:
        [1]: L. K. Grover (1996), A fast quantum mechanical algorithm for database search,
            `arXiv:quant-ph/9605043 <https://arxiv.org/abs/quant-ph/9605043>`_.
        [2]: I. Chuang & M. Nielsen, Quantum Computation and Quantum Information,
            Cambridge: Cambridge University Press, 2000. Chapter 6.1.2.
        [3]: Brassard, G., Hoyer, P., Mosca, M., & Tapp, A. (2000).
            Quantum Amplitude Amplification and Estimation.
            `arXiv:quant-ph/0005055 <http://arxiv.org/abs/quant-ph/0005055>`_.

    """

    def __init__(self,
                 oracle: Union[QuantumCircuit, Statevector],
                 good_state: Optional[Union[Callable[[str], bool],
                                            List[str], List[int], Statevector]] = None,
                 state_preparation: Optional[QuantumCircuit] = None,
                 iterations: Union[int, List[int]] = 1,
                 sample_from_iterations: bool = False,
                 post_processing: Callable[[List[int]], List[int]] = None,
                 grover_operator: Optional[QuantumCircuit] = None,
                 quantum_instance: Optional[Union[QuantumInstance, Backend, BaseBackend]] = None
                 ) -> None:
        r"""
        Args:
            oracle: The oracle to flip the phase of good states, :math:`\mathcal{S}_f`.
            good_state: A callable to check if a given measurement corresponds to a good state.
                For convenience, a list of bitstrings, a list of integer or statevector can be
                passed instead of a function. If the input is a list of bitstrings, each bitstrings
                in the list represents a good state. If the input is a list of integer,
                each integer represent the index of the good state to be :math:`|1\rangle`.
                If it is a :class:`~qiskit.quantum_info.Statevector`, it represents a superposition
                of all good states.
            state_preparation: The state preparation :math:`\mathcal{A}`. If None then Grover's
                 Search by default uses uniform superposition.
            iterations: Specify the number of iterations/power of Grover's operator to be checked.
                It the number of solutions is known, this should be an integer specifying the
                optimal number of iterations (see ``optimal_num_iterations``). Alternatively,
                this can be a list of powers to check.
            sample_from_iterations: If True, instead of taking the values in ``iterations`` as
                powers of the Grover operator, a random integer sample between 0 and smaller value
                than the iteration is used as a power, see [1], Section 4.
            post_processing: An optional post processing applied to the top measurement. Can be used
                e.g. to convert from the bit-representation of the measurement `[1, 0, 1]` to a
                DIMACS CNF format `[1, -2, 3]`.
            grover_operator: A circuit implementing the Grover operator :math:`\mathcal{Q}`.
                If None, the operator is constructed automatically using the
                :class:`~qiskit.circuit.library.GroverOperator` from the circuit library.
            quantum_instance: A Quantum Instance or Backend to run the circuits.

        Raises:
            TypeError: If ``init_state`` is of unsupported type or is of type ``InitialState` but
                the oracle is not of type ``Oracle``.
            TypeError: If ``oracle`` is of unsupported type.


        References:
            [1]: Boyer et al., Tight bounds on quantum searching
                 `<https://arxiv.org/abs/quant-ph/9605034>`_
        """
        self._quantum_instance = None
        if quantum_instance:
            self.quantum_instance = quantum_instance

        self._oracle = oracle

        # Construct GroverOperator circuit
        if grover_operator is not None:
            self._grover_operator = grover_operator
        else:
            # wrap in method to hide the logic of handling deprecated arguments, can be simplified
            # once the deprecated arguments are removed
            self._grover_operator = _construct_grover_operator(oracle, state_preparation)

        max_iterations = np.ceil(2 ** (len(self._grover_operator.reflection_qubits) / 2))
        if not isinstance(iterations, list):
            iterations = [iterations]
        # else: already a list

        # cutoff if max_iterations is exceeded (legacy code, should considered for removal?)
        self._iterations = []
        for iteration in iterations:
            self._iterations += [iteration]
            if iteration > max_iterations:
                break

        # check the type of good_state
        _check_is_good_state(good_state)

        self._is_good_state = good_state
        self._sample_from_iterations = sample_from_iterations
        self._post_processing = post_processing

        if isinstance(iterations, list) and len(iterations) > 1:
            logger.debug('Incremental mode specified, \
                ignoring "num_iterations" and "num_solutions".')

        self._ret = GroverResult()

    @property
    def quantum_instance(self) -> Optional[QuantumInstance]:
        """ Returns quantum instance. """
        return self._quantum_instance

    @quantum_instance.setter
    def quantum_instance(self, quantum_instance: Union[QuantumInstance,
                                                       BaseBackend, Backend]) -> None:
        """ Sets quantum instance. """
        if isinstance(quantum_instance, (BaseBackend, Backend)):
            quantum_instance = QuantumInstance(quantum_instance)
        self._quantum_instance = quantum_instance

    @staticmethod
    def optimal_num_iterations(num_solutions: int, num_qubits: int) -> int:
        """Return the optimal number of iterations, if the number of solutions is known.

        Args:
            num_solutions: The number of solutions.
            num_qubits: The number of qubits used to encode the states.

        Returns:
            The optimal number of iterations for Grover's algorithm to succeed.
        """
        return math.floor(np.pi * np.sqrt(2 ** num_qubits / num_solutions) / 4)

    def _run_experiment(self, power):
        """Run a grover experiment for a given power of the Grover operator."""
        if self._quantum_instance.is_statevector:
            qc = self.construct_circuit(power, measurement=False)
            result = self._quantum_instance.execute(qc)
            statevector = result.get_statevector(qc)
            num_bits = len(self._grover_operator.reflection_qubits)
            # trace out work qubits
            if qc.width() != num_bits:
                rho = partial_trace(statevector, range(num_bits, qc.width()))
                statevector = np.diag(rho.data)
            max_amplitude = max(statevector.max(), statevector.min(), key=abs)
            max_amplitude_idx = np.where(statevector == max_amplitude)[0][0]
            top_measurement = np.binary_repr(max_amplitude_idx, num_bits)

        else:
            qc = self.construct_circuit(power, measurement=True)
            measurement = self._quantum_instance.execute(qc).get_counts(qc)
            self._ret.measurement = dict(measurement)
            top_measurement = max(measurement.items(), key=operator.itemgetter(1))[0]

        self._ret.top_measurement = top_measurement

        # as_list = [int(bit) for bit in top_measurement]
        # return self.post_processing(as_list), self.is_good_state(top_measurement)
        return self.post_processing(top_measurement), self.is_good_state(top_measurement)

    def is_good_state(self, bitstr: str) -> bool:
        """Check whether a provided bitstring is a good state or not.

        Args:
            bitstr: The measurement as bitstring.

        Returns:
            True if the measurement is a good state, False otherwise.
        """
        if callable(self._is_good_state):
            return self._is_good_state(bitstr)
        elif isinstance(self._is_good_state, list):
            if all(isinstance(good_bitstr, str) for good_bitstr in self._is_good_state):
                return bitstr in self._is_good_state
            else:
                return all(bitstr[good_index] == '1'  # type:ignore
                           for good_index in self._is_good_state)
        # else isinstance(self._is_good_state, Statevector) must be True
        return bitstr in self._is_good_state.probabilities_dict()

    def post_processing(self, measurement: List[int]) -> List[int]:
        """Do the post-processing to the measurement result

        Args:
            measurement: The measurement as list of int.

        Returns:
            Do the post-processing based on the post_processing argument.
            Just return the input bitstr
        """
        if self._post_processing is not None:
            return self._post_processing(measurement)

        return measurement

    def construct_circuit(self, power: Optional[int] = None,
                          measurement: bool = False) -> QuantumCircuit:
        """Construct the circuit for Grover's algorithm with ``power`` Grover operators.

        Args:
            power: The number of times the Grover operator is repeated. If None, this argument
                is set to the first item in ``iterations``.
            measurement: Boolean flag to indicate if measurement should be included in the circuit.

        Returns:
            QuantumCircuit: the QuantumCircuit object for the constructed circuit
        """
        if power is None:
            power = self._iterations[0]

        qc = QuantumCircuit(self._grover_operator.num_qubits, name='Grover circuit')
        qc.compose(self._grover_operator.state_preparation, inplace=True)
        if power > 0:
            qc.compose(self._grover_operator.power(power), inplace=True)

        if measurement:
            measurement_cr = ClassicalRegister(len(self._grover_operator.reflection_qubits))
            qc.add_register(measurement_cr)
            qc.measure(self._grover_operator.reflection_qubits, measurement_cr)

        self._ret.circuit = qc
        return qc

    def run(self,
            quantum_instance: Optional[
                Union[QuantumInstance, Backend, BaseBackend]] = None,
            **kwargs) -> 'GroverResult':
        """Execute the algorithm with selected backend.

        Args:
            quantum_instance: the experimental setting.
            kwargs (dict): kwargs
        Returns:
            results of an algorithm.
        Raises:
            AlgorithmError: If a quantum instance or backend has not been provided
        """
        if quantum_instance is None and self.quantum_instance is None:
            raise AlgorithmError("A QuantumInstance or Backend "
                                 "must be supplied to run the quantum algorithm.")
        if isinstance(quantum_instance, (BaseBackend, Backend)):
            self.quantum_instance = QuantumInstance(quantum_instance)
            self.quantum_instance.set_config(**kwargs)
        else:
            if quantum_instance is not None:
                self.quantum_instance = quantum_instance

        return self._run()

    def _run(self) -> 'GroverResult':
        # If ``rotation_counts`` is specified, run Grover's circuit for the powers specified
        # in ``rotation_counts``. Once a good state is found (oracle_evaluation is True), stop.
        for power in self._iterations:
            if self._sample_from_iterations:
                power = algorithm_globals.random.integers(power)
            assignment, oracle_evaluation = self._run_experiment(power)
            if oracle_evaluation:
                break

        self._ret.assignment = assignment
        self._ret.oracle_evaluation = oracle_evaluation
        return self._ret

    @property
    def grover_operator(self) -> QuantumCircuit:
        """Returns grover_operator."""
        return self._grover_operator


def _construct_grover_operator(oracle, state_preparation):
    # check the type of state_preparation
    if not (isinstance(state_preparation, QuantumCircuit) or state_preparation is None):
        raise TypeError('Unsupported type "{}" of state_preparation'.format(
            type(state_preparation)))

    # check to oracle type
    reflection_qubits = None
    if not isinstance(oracle, (QuantumCircuit, Statevector)):
        raise TypeError('Unsupported type "{}" of oracle'.format(type(oracle)))

    grover_operator = GroverOperator(oracle=oracle,
                                     state_preparation=state_preparation,
                                     reflection_qubits=reflection_qubits)
    return grover_operator


def _check_is_good_state(is_good_state):
    """Check whether a provided is_good_state is one of the supported types or not"""
    is_compatible = False
    if callable(is_good_state):
        is_compatible = True
    if isinstance(is_good_state, list):
        if all(isinstance(good_bitstr, str) for good_bitstr in is_good_state) or \
           all(isinstance(good_index, int) for good_index in is_good_state):
            is_compatible = True
    if isinstance(is_good_state, Statevector):
        is_compatible = True

    if not is_compatible:
        raise TypeError('Unsupported type "{}" of is_good_state'.format(type(is_good_state)))


class GroverResult(AlgorithmResult):
    """Grover Result."""

    def __init__(self) -> None:
        super().__init__()
        self._measurement = None
        self._top_measurement = None
        self._circuit = None
        self._assignment = None
        self._oracle_evaluation = None

    @property
    def measurement(self) -> Optional[Dict[str, int]]:
        """ returns measurement """
        return self._measurement

    @measurement.setter
    def measurement(self, value: Dict[str, int]) -> None:
        """ set measurement """
        self._measurement = value

    @property
    def top_measurement(self) -> Optional[str]:
        """ return top measurement """
        return self._top_measurement

    @top_measurement.setter
    def top_measurement(self, value: str) -> None:
        """ set top measurement """
        self._top_measurement = value

    @property
    def circuit(self) -> Optional[QuantumCircuit]:
        """ return circuit """
        return self._circuit

    @circuit.setter
    def circuit(self, value: QuantumCircuit) -> None:
        """ set circuit """
        self._circuit = value

    @property
    def assignment(self) -> List[int]:
        """ return assignment """
        return self._assignment

    @assignment.setter
    def assignment(self, value: List[int]) -> None:
        """ set assignment """
        self._assignment = value

    @property
    def oracle_evaluation(self) -> bool:
        """ return oracle evaluation """
        return self._oracle_evaluation

    @oracle_evaluation.setter
    def oracle_evaluation(self, value: bool) -> None:
        """ set oracle evaluation """
        self._oracle_evaluation = value
