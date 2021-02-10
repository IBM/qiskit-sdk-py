# This code is part of Qiskit.
#
# (C) Copyright IBM 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""A quantum oracle constructed from a logical expression or a string in the DIMACS format."""

from qiskit.circuit import QuantumCircuit
from qiskit.exceptions import QiskitError
from .classicalfunction import HAS_TWEEDLEDUM
from .utils import tweedledum2qiskit


class BooleanExpression(QuantumCircuit):
    r"""The Logical Expression Quantum Oracle.

    The Logical Expression Oracle, as its name suggests, constructs circuits for any arbitrary
    input logical expressions. A logical expression is composed of logical operators
    `&` (`AND`), `|` (`OR`) and `~` (`NOT`),
    as well as symbols for literals (variables).
    For example, `'a & b'`, and `(v0 | ~v1) & (~v2 & v3)`
    are both valid string representation of boolean logical expressions.

    For convenience, this oracle, in addition to parsing arbitrary logical expressions,
    also supports input strings in the `DIMACS CNF format
    <http://www.satcompetition.org/2009/format-benchmarks2009.html>`__,
    which is the standard format for specifying SATisfiability (SAT) problem instances in
    `Conjunctive Normal Form (CNF) <https://en.wikipedia.org/wiki/Conjunctive_normal_form>`__,
    which is a conjunction of one or more clauses, where a clause is a disjunction of one
    or more literals.

    The following is an example of a CNF expressed in the DIMACS format:

    .. code:: text

      c This is an example DIMACS CNF file with 3 satisfying assignments: 1 -2 3, -1 -2 -3, 1 2 -3.
      p cnf 3 5
      -1 -2 -3 0
      1 -2 3 0
      1 2 -3 0
      1 -2 -3 0
      -1 2 3 0

    The first line, following the `c` character, is a comment. The second line specifies that the
    CNF is over three boolean variables --- let us call them  :math:`x_1, x_2, x_3`, and contains
    five clauses.  The five clauses, listed afterwards, are implicitly joined by the logical `AND`
    operator, :math:`\land`, while the variables in each clause, represented by their indices,
    are implicitly disjoined by the logical `OR` operator, :math:`lor`. The :math:`-` symbol
    preceding a boolean variable index corresponds to the logical `NOT` operator, :math:`lnot`.
    Character `0` (zero) marks the end of each clause.  Essentially, the code above corresponds
    to the following CNF:

    :math:`(\lnot x_1 \lor \lnot x_2 \lor \lnot x_3)
    \land (x_1 \lor \lnot x_2 \lor x_3)
    \land (x_1 \lor x_2 \lor \lnot x_3)
    \land (x_1 \lor \lnot x_2 \lor \lnot x_3)
    \land (\lnot x_1 \lor x_2 \lor x_3)`.

    This is an example showing how to search for a satisfying assignment to an SAT problem encoded
    in DIMACS using the `Logical Expression oracle with the Grover algorithm.
    <https://github.com/Qiskit/qiskit-tutorials-community/blob/master/optimization/grover.ipynb>`__

    Logic expressions, regardless of the input formats, are parsed and stored as a source string,
    from which the corresponding circuits are constructed by
    :class:`~qiskit.circuit.classicalfunction.ClassicalFunction`.
    The oracle circuits
    can then be used with any oracle-oriented algorithms when appropriate. For example, an oracle
    built from a DIMACS input can be used with the Grover's algorithm to search for a satisfying
    assignment to the encoded SAT instance.

    Examples:
        >>> from qiskit.circuit import BooleanExpression
        >>> from qiskit.algorithms.amplitude_amplifiers import Grover
        >>> expr = "(x0 & x1 | ~x2) ^ x4"
        >>> oracle = BooleanExpression(expr)
        >>> grover = Grover(oracle=oracle, good_state=oracle.evaluate_bitstring)
    """

    def __init__(self, expression: str, name: str = None) -> None:
        """
        Args:
            expression: The logical expression string.
        """

        if not isinstance(expression, str):
            raise QiskitError('BooleanExpression needs a Python expression as a string.')
        if not HAS_TWEEDLEDUM:
            raise ImportError("To use the BooleanExpression compiler, tweedledum "
                              "must be installed. To install tweedledum run "
                              '"pip install tweedledum".')
        from tweedledum import BoolExpression
        self._tweedledum_bool_expression = BoolExpression(expression)

        short_expression_for_name = (expression[:10] + '..') if len(expression) > 13 else expression
        # super().__init__(self.name,
        #                  num_qubits=sum([qreg.size for qreg in self.qregs]),
        #                  params=[])
        super().__init__(len(self._tweedledum_bool_expression._parameters_signature) +
                         len(self._tweedledum_bool_expression._return_signature),
                         name=name or short_expression_for_name)

    def evaluate(self, bitstring: str) -> bool:
        """Evaluate the oracle on a bitstring.

        This evaluation is done classically.

        Args:
            bitstring: The bitstring for which to evaluate.

        Returns:
            bool: result of the evaluation.
        """
        from tweedledum import BitVec
        input = []
        for bit in bitstring:
            input.append(BitVec(1, bit))
        return bool(self._tweedledum_bool_expression.simulate(*input))

    def synth(self, registerless=True):
        """Synthesis the logic network into a :class:`~qiskit.circuit.QuantumCircuit`.

        Args:
            registerless (bool): Default ``True``. If ``False`` uses the parameter names to create
            registers with those names. Otherwise, creates a circuit with a flat quantum register.

        Returns:
            QuantumCircuit: A circuit implementing the logic network.
        """
        from tweedledum.passes import xag_synth

        if registerless:
            qregs = None
        else:
            qregs = self.qregs

        logic_network = self._tweedledum_bool_expression._logic_network

        return tweedledum2qiskit(xag_synth(logic_network), name=self.name, qregs=qregs)

    def _define(self):
        """The definition of the boolean expression is its synthesis"""
        self.definition = self.synth()

    @classmethod
    def from_dimacs_file(cls, filename: str, name=None):
        """Create a BooleanExpression from the string in the DIMACS format.
        Args:
            dimacs: The string in the DIMACS format.

        Returns:
            A quantum circuit (BooleanExpression) for the input string
        """
        from tweedledum.classical import read_dimacs
        bool_exp_instance = cls.__new__(cls)
        bool_exp_instance._tweedledum_bool_expression = read_dimacs(filename)
        super().__init__(len(bool_exp_instance._tweedledum_bool_expression._parameters_signature) +
                         len(bool_exp_instance._tweedledum_bool_expression._return_signature),
                         name=name or filename)
        return bool_exp_instance
