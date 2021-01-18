# This code is part of Qiskit.
#
# (C) Copyright IBM 2017, 2020.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Synthesize a single qubit gate to a discrete basis set."""

from typing import List, Union, Tuple
import itertools
import numpy as np

from qiskit.circuit import QuantumCircuit, Gate, QuantumRegister
from qiskit.circuit.library import IGate
from qiskit.converters import circuit_to_dag
from qiskit.transpiler.basepasses import TransformationPass
from qiskit.dagcircuit.dagcircuit import DAGCircuit

from qiskit.transpiler.passes.synthesis.solovay_kitaev_utils import (
    GateSequence,
    compute_rotation_axis,
    compute_rotation_between,
    compute_rotation_from_angle_and_axis,
    solve_decomposition_angle,
    _compute_commutator_so3,
)


class SolovayKitaev():
    """The Solovay Kitaev discrete decomposition algorithm.

    See :class:`~qiskit.transpiler.passes.SolovayKitaevDecomposition` for more information.
    """

    def __init__(self, basis_gates: List[Union[str, Gate]]) -> None:
        """
        Args:
            basis_gates: A list of gates used to approximate the single qubit gates.
        """
        self._basis_gates = basis_gates
        self._basic_approximations = self.generate_basic_approximations(
            basis_gates)

    def generate_basic_approximations(self, basis_gates: List[Union[str, Gate]]
                                      ) -> List[GateSequence]:
        """Generates a list of ``GateSequence``s with the gates in ``basic_gates``.

        Args:
            basis_gates: The gates from which to create the sequences of gates.

        Returns:
            List of GateSequences using the gates in basic_gates.
        """
        depth = 3

        # get all products from all depths
        products = []
        for reps in range(1, depth + 1):
            products += list(list(comb)
                             for comb in itertools.product(*[basis_gates] * reps))

        sequences = []
        for item in products:
            candidate = GateSequence(item)
            accept = _check_candidate(candidate, sequences)
            if accept:
                sequences.append(candidate)

        return sequences

    def _synth_circuit(self, global_phase: float, gate_sequence: GateSequence) -> QuantumCircuit:
        """Converts a ``GateSequence`` to a circuit, additionally adding the ``global_phase``.

        Args:
            global_phase: The global phase of the circuit.
            gate_sequence: GateSequence from which to construct the circuit.

        Returns:
            The gate sequence as a circuit.
        """
        qr = QuantumRegister(1, 'q')
        qc = QuantumCircuit(qr)
        for gate in gate_sequence.gates:
            qc.append(gate, [qr[0]])
        qc.global_phase = global_phase + gate_sequence.global_phase
        return qc

    def run(self, gate_matrix: np.ndarray, recursion_degree: int) -> QuantumCircuit:
        r"""Run the algorithm.

        Args:
            gate_matrix: The 2x2 matrix representing the gate. Does not need to be SU(2).
            recursion_degree: The recursion degree, called :math:`n` in the paper.

        Returns:
            A one-qubit circuit approximating the ``gate_matrix`` in the specified discrete basis.
        """
        # make input matrix SU(2) and get the according global phase
        z = 1 / np.sqrt(np.linalg.det(gate_matrix))
        gate_matrix_su2 = GateSequence.from_matrix(z * gate_matrix)
        global_phase = np.arctan2(np.imag(z), np.real(z))

        # get the decompositon as GateSequence type
        decomposition = self._recurse(gate_matrix_su2, recursion_degree)

        # convert to a circuit and attach the right phases
        # TODO insert simplify again, but it seems to break the accuracy test
        circuit = self._synth_circuit(global_phase, decomposition)

        return circuit

    def _recurse(self, sequence: GateSequence, n: int) -> GateSequence:
        """Performs ``n`` iterations of the Solovay-Kitaev algorithm on ``sequence``.

        Args:
            sequence: GateSequence to which the Solovay-Kitaev algorithm is applied.
            n: number of iterations that the algorithm needs to run.

        Returns:
            GateSequence that approximates ``sequence``.

        Raises:
            ValueError: if ``u`` does not represent an SO(3)-matrix.
        """
        if sequence.product.shape != (3, 3):
            raise ValueError(
                'Shape of U must be (3, 3) but is', sequence.shape)

        if n == 0:
            return self.find_basic_approximation(sequence)

        u_n1 = self._recurse(sequence, n - 1)
        tuple_v_w = commutator_decompose(
            np.dot(sequence.product, np.matrix.getH(u_n1.product)))

        v_n1 = self._recurse(tuple_v_w[0], n - 1)
        w_n1 = self._recurse(tuple_v_w[1], n - 1)
        return v_n1.dot(w_n1).dot(v_n1.adjoint()).dot(w_n1.adjoint()).dot(u_n1)

    def find_basic_approximation(self, sequence: GateSequence) -> Gate:
        """Finds gate in ``self._basic_approximations`` that best represents ``sequence``.

        Args:
            sequence: The gate to find the approximation to.

        Returns:
            Gate in basic approximations that is closest to ``sequence``.
        """
        def key(x):
            return np.linalg.norm(np.subtract(x.product, sequence.product))

        return min(self._basic_approximations, key=key)


def commutator_decompose(u_so3: np.ndarray) -> Tuple[GateSequence, GateSequence]:
    r"""Decompose an :math:`SO(3)`-matrix, :math:`U` as a balanced commutator.

    This function finds two :math:`SO(3)` matrices :math:`V, W` such that the input matrix
    equals

    .. math::

        U = V^\dagger W^\dagger V W.

    For this decomposition, the following statement holds

    .. math::

        ||V - I||_F, ||W - I||_F \leq \frac{\sqrt{||U - I||_F}}{2},

    where :math:`I` is the identity and :math:`||\cdot ||_F` is the Frobenius norm.

    Args:
        u_so3: SO(3)-matrix that needs to be decomposed as balanced commutator.

    Returns:
        Tuple of GateSequences from SO(3)-matrices :math:`V, W`.

    Raises:
        ValueError: if ``u_so3`` is not an SO(3)-matrix.
    """
    descr_method = 'Computation commutator decompose'
    if u_so3.shape != (3, 3):
        raise ValueError(
            descr_method + 'called on matrix of shape', u_so3.shape)

    if abs(np.linalg.det(u_so3) - 1) > 1e-4:
        raise ValueError(
            descr_method + 'called on determinant of', np.linalg.det(u_so3))

    angle = solve_decomposition_angle(u_so3)

    # Compute rotation about x-axis with angle 'angle'
    vx = compute_rotation_from_angle_and_axis(angle, np.array([1, 0, 0]))

    # Compute rotation about y-axis with angle 'angle'
    wy = compute_rotation_from_angle_and_axis(angle, np.array([0, 1, 0]))

    commutator = _compute_commutator_so3(vx, wy)

    u_so3_axis = compute_rotation_axis(u_so3)
    commutator_axis = compute_rotation_axis(commutator)

    sim_matrix = compute_rotation_between(commutator_axis, u_so3_axis)
    sim_matrix_dagger = np.matrix.getH(sim_matrix)

    v = np.dot(np.dot(sim_matrix, vx), sim_matrix_dagger)
    w = np.dot(np.dot(sim_matrix, wy), sim_matrix_dagger)

    return GateSequence.from_matrix(v), GateSequence.from_matrix(w)


def _check_candidate(candidate: GateSequence, sequences: List[GateSequence]) -> bool:
    from qiskit.quantum_info.operators.predicates import matrix_equal
    # check if a matrix representation already exists
    for existing in sequences:
        # eliminate global phase
        if matrix_equal(existing.product, candidate.product, ignore_phase=True):
            # is the new sequence less or more efficient?
            if len(candidate.gates) >= len(existing.gates):
                return False
            return True
    return True


def _simplify(sequence: GateSequence) -> GateSequence:
    id_removed = [
        gate for gate in sequence.gates if not _approximates_identity(gate)]
    no_inverses_together = []
    for index, _ in enumerate(id_removed):
        if index < len(id_removed)-1 and _is_left_to_inverse(id_removed, index):
            continue
        if index > 0 and _is_right_to_inverse(id_removed, index):
            continue
        no_inverses_together.append(id_removed[index])
    return GateSequence(no_inverses_together)


def _approximates_identity(gate: Gate) -> bool:
    return np.linalg.norm(np.subtract(gate.to_matrix(), IGate().to_matrix())) < 1e-4


def _is_left_to_inverse(id_removed: List[GateSequence], index: int) -> bool:
    product = np.dot(id_removed[index].to_matrix(),
                     id_removed[index+1].to_matrix())
    return np.linalg.norm(np.subtract(product, IGate())) < 1e-4


def _is_right_to_inverse(id_removed: List[GateSequence], index: int) -> bool:
    product = np.dot(id_removed[index-1].to_matrix(),
                     id_removed[index].to_matrix())
    return np.linalg.norm(np.subtract(product, IGate())) < 1e-4


class SolovayKitaevDecomposition(TransformationPass):
    r"""Approximately decompose 1q gates to a discrete basis using the Solovay-Kitaev algorithm.

    The Solovay-Kitaev theorem [1] states that any single qubit gate can be approximated to
    arbitrary precision by a set of fixed single-qubit gates, if the set generates a dense
    subset in :math:`SU(2)`. This is an important result, since it means that any single-qubit
    gate can be expressed in terms of a discrete, universal gate set that we know how to implement
    fault-tolerantly. Therefore, the Solovay-Kitaev algorithm allows us to take any
    non-fault tolerant circuit and rephrase it in a fault-tolerant manner.

    This implementation of the Solovay-Kitaev algorithm is based on [2].

    For example, the following circuit

    .. parsed-literal::

             ┌─────────┐
        q_0: ┤ RX(0.8) ├
             └─────────┘

    can be decomposed into

    .. parsed-literal::

        global phase: -π/8
             ┌───┐┌───┐┌───┐
        q_0: ┤ H ├┤ T ├┤ H ├
             └───┘└───┘└───┘

    with an L2-error of approximately 0.01.


    Examples:

        .. jupyter-execute::

            import numpy as np
            from qiskit.circuit import QuantumCircuit
            from qiskit.circuit.library import TGate, HGate, TdgGate
            from qiskit.converters import circuit_to_dag, dag_to_circuit
            from qiskit.transpiler.passes import SolovayKitaevDecomposition
            from qiskit.quantum_info import Operator

            circuit = QuantumCircuit(1)
            circuit.rx(0.8, 0)
            dag = circuit_to_dag(circuit)

            print('Original circuit:')
            print(circuit.draw())

            basis_gates = [TGate(), TdgGate(), HGate()]
            skd = SolovayKitaevDecomposition(recursion_degree=2, basis_gates=basis_gates)

            discretized = dag_to_circuit(skd.run(dag))

            print('Discretized circuit:')
            print(discretized.draw())

            print('Error:', np.linalg.norm(Operator(circuit).data - Operator(discretized).data))


    References:

        [1]: Kitaev, A Yu (1997). Quantum computations: algorithms and error correction.
             Russian Mathematical Surveys. 52 (6): 1191–1249.
             `Online <https://iopscience.iop.org/article/10.1070/RM1997v052n06ABEH002155>`_.

        [2]: Dawson, Christopher M.; Nielsen, Michael A. (2005) The Solovay-Kitaev Algorithm.
             `arXiv:quant-ph/0505030 <https://arxiv.org/abs/quant-ph/0505030>`_


    """

    def __init__(self, recursion_degree: int, basis_gates: List[Union[str, Gate]]) -> None:
        """
        Args:
            recursion_degree: The recursion depth for the Solovay-Kitaev algorithm.
                A larger recursion depth increases the accuracy and length of the
                decomposition.
            basis_gates: A list of gates used to approximate the single qubit gates.
        """
        super().__init__()
        self._recursion_degree = recursion_degree
        self._sk = SolovayKitaev(basis_gates)

    def run(self, dag: DAGCircuit) -> DAGCircuit:
        """Run the SolovayKitaevDecomposition pass on `dag`.

        Args:
            dag: The input dag.

        Returns:
            Output dag with 1q gates synthesized in the discrete target basis.
        """
        for node in dag.nodes():
            if node.type != 'op':
                continue  # skip all nodes that do not represent operations

            if not node.op.num_qubits == 1:
                continue  # ignore all non-single qubit gates

            matrix = node.op.to_matrix()

            # call solovay kitaev
            approximation = self._sk.run(matrix, self._recursion_degree)

            # convert to a dag and replace the gate by the approximation
            substitute = circuit_to_dag(approximation)
            dag.substitute_node_with_dag(node, substitute)

        return dag
