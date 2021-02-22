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

from os.path import basename

from qiskit.circuit import Gate
from .classicalfunction import HAS_TWEEDLEDUM


class BooleanExpression(Gate):
    """The Boolean Expression gate."""

    def __init__(self, expression: str, name: str = None) -> None:
        """
        Args:
            expression (str): The logical expression string.
            name (str): Optional. Instruction gate name. Otherwise part of
                        the expression is going to be used.
        Raises:
            ImportError: If tweedledum is not installed. Tweedledum is required.
        """
        if not HAS_TWEEDLEDUM:
            raise ImportError("To use the BooleanExpression compiler, tweedledum "
                              "must be installed. To install tweedledum run "
                              '"pip install tweedledum".')
        from tweedledum import BoolFunction
        self._tweedledum_bool_expression = BoolFunction.from_expression(expression)
        self.qregs = None  # TODO: Probably from self._tweedledum_bool_expression._signature

        short_expr_for_name = (expression[:10] + '...') if len(expression) > 13 else expression
        num_qubits = self._tweedledum_bool_expression.num_outputs() + \
                     self._tweedledum_bool_expression.num_inputs()
        super().__init__(name or short_expr_for_name, num_qubits=num_qubits, params=[])

    def simulate(self, bitstring: str) -> bool:
        """Evaluate the expression on a bitstring.

        This evaluation is done classically.

        Args:
            bitstring: The bitstring for which to evaluate.

        Returns:
            bool: result of the evaluation.
        """
        from tweedledum import BitVec
        bits = []
        for bit in bitstring:
            bits.append(BitVec(1, bit))
        return bool(self._tweedledum_bool_expression.simulate(*bits))

    def synth(self, registerless=True, synthesizer=None):
        """Synthesis the logic network into a :class:`~qiskit.circuit.QuantumCircuit`.

        Args:
            registerless (bool): Default ``True``. If ``False`` uses the parameter names
                to create registers with those names. Otherwise, creates a circuit with a flat
                quantum register.
            synthesizer (callable): A callable that takes a Logic Network and returns a Tweedledum
                circuit.
        Returns:
            QuantumCircuit: A circuit implementing the logic network.
        """
        from tweedledum.passes import pkrm_synth  # pylint: disable=no-name-in-module
        from .utils import tweedledum2qiskit

        if registerless:
            qregs = None
        else:
            qregs = self.qregs

        logic_network = self._tweedledum_bool_expression._logic_network

        if synthesizer is None:
            synthesizer = pkrm_synth

        return tweedledum2qiskit(synthesizer(logic_network), name=self.name, qregs=qregs)

    def _define(self):
        """The definition of the boolean expression is its synthesis"""
        self.definition = self.synth()

    @classmethod
    def from_dimacs_file(cls, filename: str):
        """Create a BooleanExpression from the string in the DIMACS format.
        Args:
            filename (str): A file in DIMACS format.

        Returns:
            BooleanExpression: A gate for the input string

        Raises:
            ImportError: If tweedledum is not installed. Tweedledum is required.
        """
        if not HAS_TWEEDLEDUM:
            raise ImportError("To use the BooleanExpression compiler, tweedledum "
                              "must be installed. To install tweedledum run "
                              '"pip install tweedledum".')
        from tweedledum import BoolFunction

        expr_obj = cls.__new__(cls)
        expr_obj._tweedledum_bool_expression = BoolFunction.from_dimacs_file(filename)

        num_qubits = expr_obj._tweedledum_bool_expression.num_inputs() + \
                     expr_obj._tweedledum_bool_expression.num_outputs()
        super(BooleanExpression, expr_obj).__init__(name=basename(filename), num_qubits=num_qubits,
                                                    params=[])
        return expr_obj
