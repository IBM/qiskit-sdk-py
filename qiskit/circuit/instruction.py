# -*- coding: utf-8 -*-

# Copyright 2017, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""
A generic quantum instruction.

Instructions can be implementable on hardware (u, cx, etc.) or in simulation
(snapshot, noise, etc.).

Instructions can be unitary (a.k.a Gate) or non-unitary.

Instructions are identified by the following:

    name: A string to identify the type of instruction.
          Used to request a specific instruction on the backend, or in visualizing circuits.

    num_qubits, num_clbits: dimensions of the instruction

    params: List of parameters to specialize a specific intruction instance.

Instructions do not have any context about where they are in a circuit (which qubits/clbits).
The circuit itself keeps this context.
"""
from copy import deepcopy
import sympy
import numpy

from qiskit.qasm._node import _node
from qiskit.exceptions import QiskitError


class Instruction:
    """Generic quantum instruction."""

    def __init__(self, name, num_qubits, num_clbits, params, circuit=None, is_reversible=True):
        """Create a new instruction.
        Args:
            name (str): instruction name
            num_qubits (int): instruction's qubit width
            num_clbits (int): instructions's clbit width
            params (list[sympy.Basic|qasm.Node|int|float|complex|str|ndarray]): list of parameters
            circuit (QuantumCircuit or Instruction): where the instruction is attached
            is_reversible (bool): whether the instruction can be inverted
        Raises:
            QiskitError: when the register is not in the correct format.
        """
        self.name = name
        self.num_qubits = num_qubits
        self.num_clbits = num_clbits
        if self.num_qubits < 0 or self.num_clbits < 0:
            raise QiskitError("bad instruction dimensions: %d qubits, %d clbits." %
                              self.num_qubits, self.num_clbits)

        self.params = []  # a list of gate params stored
        for single_param in params:
            # example: u2(pi/2, sin(pi/4))
            if isinstance(single_param, sympy.Basic):
                self.params.append(single_param)
            # example: OpenQASM parsed instruction
            elif isinstance(single_param, _node.Node):
                self.params.append(single_param.sym())
            # example: u3(0.1, 0.2, 0.3)
            elif isinstance(single_param, (int, float)):
                self.params.append(sympy.Number(single_param))
            # example: Initialize([complex(0,1), complex(0,0)])
            elif isinstance(single_param, complex):
                self.params.append(single_param.real + single_param.imag * sympy.I)
            # example: snapshot('label')
            elif isinstance(single_param, str):
                self.params.append(sympy.Symbol(single_param))
            # example: numpy.array([[1, 0], [0, 1]])
            elif isinstance(single_param, numpy.ndarray):
                self.params.append(single_param)
            # example: sympy.Matrix([[1, 0], [0, 1]])
            elif isinstance(single_param, sympy.Matrix):
                self.params.append(single_param)
            else:
                raise QiskitError("invalid param type {0} in instruction "
                                  "{1}".format(type(single_param), name))
        # tuple (ClassicalRegister, int) when the instruction has a conditional ("if")
        self.control = None
        # reference to the circuit containing this instruction
        self.circuit = circuit
        # flag to keep track of gate reversibility
        self.is_reversible = is_reversible
        if self.is_reversible and num_clbits > 0:
            raise QiskitError("instruction %s cannot be reversible and "
                              "act on classical bits." % self.name)

    def __eq__(self, other):
        """Two instructions are the same if they have the same name and same
        params.

        Args:
            other (instruction): other instruction

        Returns:
            bool: are self and other equal.
        """
        res = False
        if type(self) is type(other) and \
                self.name == other.name and (self.params == other.params or
                                             [float(param) for param in other.params] == [
                                                 float(param) for param in self.params]):
            res = True
        return res

    def check_circuit(self):
        """Raise exception if self.circuit is None."""
        if self.circuit is None:
            raise QiskitError("Instruction's circuit not assigned")

    def c_if(self, classical, val):
        """Add classical control on register classical and value val."""
        self.check_circuit()
        if not self.circuit.has_register(classical):
            raise QiskitError("the control creg is not in the circuit")
        if val < 0:
            raise QiskitError("control value should be non-negative")
        self.control = (classical, val)
        return self

    def copy(self, name=None):
        """
        deepcopy of the instruction.

        Args:
          name (str): name to be given to the copied circuit,
            if None then the name stays the same

        Returns:
          Instruction: a deepcopy of the current instruction, with the name
            updated if it was provided
        """
        cpy = deepcopy(self)
        if name:
            cpy.name = name
        return cpy

    def _modifiers(self, gate):
        """Apply any modifiers of this instruction to another one."""
        if self.control is not None:
            self.check_circuit()
            if not gate.circuit.has_register(self.control[0]):
                raise QiskitError("control register %s not found"
                                  % self.control[0].name)
            gate.c_if(self.control[0], self.control[1])

    def _qasmif(self, string):
        """Print an if statement if needed."""
        if self.control is None:
            return string
        return "if(%s==%d) " % (self.control[0].name, self.control[1]) + string

    def qasm(self):
        """Return a default OpenQASM string for the instruction.

        Derived instructions may override this to print in a
        different format (e.g. measure q[0] -> c[0];).
        """
        name_param = self.name
        if self.params:
            name_param = "%s(%s)" % (name_param,
                                     ",".join([str(i) for i in self.params]))

        return self._qasmif(name_param)
