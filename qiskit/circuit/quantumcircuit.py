# -*- coding: utf-8 -*-

# Copyright 2017, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""
Quantum circuit object.
"""
from collections import OrderedDict
from copy import deepcopy
import itertools
import sys
import multiprocessing as mp

from qiskit.qasm import _qasm
from qiskit.exceptions import QiskitError
from .instruction import Instruction
from .quantumregister import QuantumRegister
from .classicalregister import ClassicalRegister


class QuantumCircuit:
    """Quantum circuit."""
    instances = 0
    prefix = 'circuit'

    # Class variable OPENQASM header
    header = "OPENQASM 2.0;"
    extension_lib = "include \"qelib1.inc\";"

    # Class variable with gate definitions
    # This is a dict whose values are dicts with the
    # following keys:
    #   "print" = True or False
    #   "opaque" = True or False
    #   "n_args" = number of real parameters
    #   "n_bits" = number of qubits
    #   "args"   = list of parameter names
    #   "bits"   = list of qubit names
    #   "body"   = GateBody AST node
    definitions = OrderedDict()

    def __init__(self, *regs, name=None):
        """Create a new circuit.

        A circuit is a list of instructions bound to some registers.

        Args:
            *regs (Registers): registers to include in the circuit.
            name (str or None): the name of the quantum circuit. If
                None, an automatically generated string will be assigned.

        Raises:
            QiskitError: if the circuit name, if given, is not valid.
        """
        if name is None:
            name = self.cls_prefix() + str(self.cls_instances())
            # pylint: disable=not-callable
            # (known pylint bug: https://github.com/PyCQA/pylint/issues/1699)
            if sys.platform != "win32" and \
               isinstance(mp.current_process(), mp.context.ForkProcess):
                name += '-{}'.format(mp.current_process().pid)
        self._increment_instances()

        if not isinstance(name, str):
            raise QiskitError("The circuit name should be a string "
                              "(or None to auto-generate a name).")

        self.name = name

        # Data contains a list of instructions in the order they were applied.
        self.data = []

        # This is a map of registers bound to this circuit, by name.
        self.qregs = []
        self.cregs = []
        self.add_register(*regs)

    def __str__(self):
        return str(self.draw(output='text'))

    def __repr__(self):
        repr_str = "QuantumCircuit<width={}, depth={}, gate_count={}, tensor_factors={}>"
        return repr_str.format(self.width(), self.depth(),
                               self.count_ops(), self.num_tensor_factors())

    def __eq__(self, other):
        # TODO: removed the DAG from this function
        from qiskit.converters import circuit_to_dag
        return circuit_to_dag(self) == circuit_to_dag(other)

    @classmethod
    def _increment_instances(cls):
        cls.instances += 1

    @classmethod
    def cls_instances(cls):
        """Return the current number of instances of this class,
        useful for auto naming."""
        return cls.instances

    @classmethod
    def cls_prefix(cls):
        """Return the prefix to use for auto naming."""
        return cls.prefix

    def has_register(self, register):
        """
        Test if this circuit has the register r.

        Args:
            register (Register): a quantum or classical register.

        Returns:
            bool: True if the register is contained in this circuit.
        """
        has_reg = False
        if (isinstance(register, QuantumRegister) and
                register in self.qregs):
            has_reg = True
        elif (isinstance(register, ClassicalRegister) and
              register in self.cregs):
            has_reg = True
        return has_reg

    def combine(self, rhs):
        """
        Append rhs to self if self contains compatible registers.

        Two circuits are compatible if they contain the same registers
        or if they contain different registers with unique names. The
        returned circuit will contain all unique registers between both
        circuits.

        Return self + rhs as a new object.
        """
        if isinstance(rhs, Instruction):
            qregs = {qubit[0] for qubit in rhs.qargs}
            cregs = {cbit[0] for cbit in rhs.cargs}
            qc = QuantumCircuit(*qregs, *cregs)
            qc._attach(rhs)
            rhs = qc
        # Check registers in LHS are compatible with RHS
        self._check_compatible_regs(rhs)

        # Make new circuit with combined registers
        combined_qregs = deepcopy(self.qregs)
        combined_cregs = deepcopy(self.cregs)

        for element in rhs.qregs:
            if element not in self.qregs:
                combined_qregs.append(element)
        for element in rhs.cregs:
            if element not in self.cregs:
                combined_cregs.append(element)
        circuit = QuantumCircuit(*combined_qregs, *combined_cregs)
        for gate in itertools.chain(self.data, rhs.data):
            gate.reapply(circuit)
        return circuit

    def extend(self, rhs):
        """
        Append rhs to self if self contains compatible registers.

        Two circuits are compatible if they contain the same registers
        or if they contain different registers with unique names. The
        returned circuit will contain all unique registers between both
        circuits.

        Modify and return self.
        """
        if isinstance(rhs, Instruction):
            qregs = {qubit[0] for qubit in rhs.qargs}
            cregs = {cbit[0] for cbit in rhs.cargs}
            qc = QuantumCircuit(*qregs, *cregs)
            qc._attach(rhs)
            rhs = qc
        # Check registers in LHS are compatible with RHS
        self._check_compatible_regs(rhs)

        # Add new registers
        for element in rhs.qregs:
            if element not in self.qregs:
                self.qregs.append(element)
        for element in rhs.cregs:
            if element not in self.cregs:
                self.cregs.append(element)

        # Add new gates
        for gate in rhs.data:
            gate.reapply(self)
        return self

    def __add__(self, rhs):
        """Overload + to implement self.combine."""
        return self.combine(rhs)

    def __iadd__(self, rhs):
        """Overload += to implement self.extend."""
        return self.extend(rhs)

    def __len__(self):
        """Return number of operations in circuit."""
        return len(self.data)

    def __getitem__(self, item):
        """Return indexed operation."""
        return self.data[item]

    def _attach(self, instruction):
        """Attach an instruction."""
        # do some compatibility checks
        self._check_dups(instruction.qargs)
        self._check_qargs(instruction.qargs)
        self._check_cargs(instruction.cargs)
        self.data.append(instruction)
        return instruction

    def add_register(self, *regs):
        """Add registers."""
        for register in regs:
            if register in self.qregs or register in self.cregs:
                raise QiskitError("register name \"%s\" already exists"
                                  % register.name)
            if isinstance(register, QuantumRegister):
                self.qregs.append(register)
            elif isinstance(register, ClassicalRegister):
                self.cregs.append(register)
            else:
                raise QiskitError("expected a register")

    def _check_qargs(self, qargs):
        """Raise exception if a qarg is not in this circuit or bad format."""
        if not all(isinstance(i, tuple) and
                   isinstance(i[0], QuantumRegister) and
                   isinstance(i[1], int) for i in qargs):
            raise QiskitError("qarg not (QuantumRegister, int) tuple")
        if not all(self.has_register(i[0]) for i in qargs):
            raise QiskitError("register not in this circuit")
        for qubit in qargs:
            qubit[0].check_range(qubit[1])

    def _check_cargs(self, cargs):
        """Raise exception if clbit is not in this circuit or bad format."""
        if not all(isinstance(i, tuple) and
                   isinstance(i[0], ClassicalRegister) and
                   isinstance(i[1], int) for i in cargs):
            raise QiskitError("carg not (ClassicalRegister, int) tuple")
        if not all(self.has_register(i[0]) for i in cargs):
            raise QiskitError("register not in this circuit")
        for clbit in cargs:
            clbit[0].check_range(clbit[1])

    def _check_dups(self, qubits):
        """Raise exception if list of qubits contains duplicates."""
        squbits = set(qubits)
        if len(squbits) != len(qubits):
            raise QiskitError("duplicate qubit arguments")

    def _check_compatible_regs(self, rhs):
        """Raise exception if the circuits are defined on incompatible registers"""
        list1 = self.qregs + self.cregs
        list2 = rhs.qregs + rhs.cregs
        for element1 in list1:
            for element2 in list2:
                if element2.name == element1.name:
                    if element1 != element2:
                        raise QiskitError("circuits are not compatible")

    def _gate_string(self, name):
        """Return a QASM string for the named gate."""
        out = ""
        if self.definitions[name]["opaque"]:
            out = "opaque " + name
        else:
            out = "gate " + name
        if self.definitions[name]["n_args"] > 0:
            out += "(" + ",".join(self.definitions[name]["args"]) + ")"
        out += " " + ",".join(self.definitions[name]["bits"])
        if self.definitions[name]["opaque"]:
            out += ";"
        else:
            out += "\n{\n" + self.definitions[name]["body"].qasm() + "}\n"
        return out

    def qasm(self):
        """Return OPENQASM string."""
        string_temp = self.header + "\n"
        string_temp += self.extension_lib + "\n"
        for register in self.qregs:
            string_temp += register.qasm() + "\n"
        for register in self.cregs:
            string_temp += register.qasm() + "\n"
        for instruction in self.data:
            string_temp += instruction.qasm() + "\n"
        return string_temp

    def draw(self, scale=0.7, filename=None, style=None, output='text',
             interactive=False, line_length=None, plot_barriers=True,
             reverse_bits=False, justify=None):
        """Draw the quantum circuit

        Using the output parameter you can specify the format. The choices are:
        0. text: ASCII art string
        1. latex: high-quality images, but heavy external software dependencies
        2. matplotlib: purely in Python with no external dependencies

        Defaults to an overcomplete basis, in order to not alter gates.

        Args:
            scale (float): scale of image to draw (shrink if < 1)
            filename (str): file path to save image to
            style (dict or str): dictionary of style or file name of style
                file. You can refer to the
                :ref:`Style Dict Doc <style-dict-doc>` for more information
                on the contents.
            output (str): Select the output method to use for drawing the
                circuit. Valid choices are `text`, `latex`, `latex_source`,
                `mpl`.
            interactive (bool): when set true show the circuit in a new window
                (for `mpl` this depends on the matplotlib backend being used
                supporting this). Note when used with either the `text` or the
                `latex_source` output type this has no effect and will be
                silently ignored.
            line_length (int): sets the length of the lines generated by `text`
            reverse_bits (bool): When set to True reverse the bit order inside
                registers for the output visualization.
            plot_barriers (bool): Enable/disable drawing barriers in the output
                circuit. Defaults to True.
            justify (string): Options are `left`, `right` or `none`, if anything
                else is supplied it defaults to left justified. It refers to where
                gates should be placed in the output circuit if there is an option.
                `none` results in each gate being placed in its own column. Currently
                only supported by text drawer.

        Returns:
            PIL.Image or matplotlib.figure or str or TextDrawing:
                * PIL.Image: (output `latex`) an in-memory representation of the
                  image of the circuit diagram.
                * matplotlib.figure: (output `mpl`) a matplotlib figure object
                  for the circuit diagram.
                * str: (output `latex_source`). The LaTeX source code.
                * TextDrawing: (output `text`). A drawing that can be printed as
                  ascii art

        Raises:
            VisualizationError: when an invalid output method is selected
        """
        from qiskit.tools import visualization
        return visualization.circuit_drawer(self, scale=scale,
                                            filename=filename, style=style,
                                            output=output,
                                            interactive=interactive,
                                            line_length=line_length,
                                            plot_barriers=plot_barriers,
                                            reverse_bits=reverse_bits,
                                            justify=justify)

    def size(self):
        """Return total number of operations in circuit."""
        return len(self.data)

    def depth(self):
        """Return circuit depth (i.e. length of critical path)."""
        # Map qregs to int offset
        qr_offset = 0
        qr_map = {}
        for qr in self.qregs:
            qr_map[qr.name] = qr_offset
            qr_offset += qr.size

        op_stack = [0]*self.width()
        for op in self.data:
            if op.name != 'barrier':
                levels = []
                for q in op.qargs:
                    q_int = qr_map[q[0].name]+q[1]
                    levels.append(op_stack[q_int] + 1)
                max_level = max(levels)
                for q in op.qargs:
                    q_int = qr_map[q[0].name]+q[1]
                    op_stack[q_int] = max_level
        return max(op_stack)

    def width(self):
        """Return number of qubits in circuit."""
        return sum(qr.size for qr in self.qregs)

    def count_ops(self):
        """Count each operation kind in the circuit.

        Returns:
            dict: a breakdown of how many operations of each kind.
        """
        count_ops = {}
        for op in self.data:
            if op.name in count_ops.keys():
                count_ops[op.name] += 1
            else:
                count_ops[op.name] = 1
        return count_ops

    def num_tensor_factors(self):
        """How many non-entangled subcircuits can the circuit be factored to."""
        qr_offset = 0
        qr_map = {}
        for qr in self.qregs:
            qr_map[qr.name] = qr_offset
            qr_offset += qr.size

        sub_graphs = [[qbit] for qbit in range(self.width())]
        num_sub_graphs = len(sub_graphs)
        for op in self.data:
            if len(op.qargs) >= 2 and op.name != 'barrier':
                graphs_touched = []
                num_touched = 0
                for q in op.qargs:
                    q_int = qr_map[q[0].name]+q[1]
                    for k in range(num_sub_graphs):
                        if q_int in sub_graphs[k]:
                            if q_int not in graphs_touched:
                                graphs_touched.append(k)
                                num_touched += 1
                if num_touched > 1:
                    connections = []
                    for idx in graphs_touched:
                        connections.extend(sub_graphs[idx])
                    _sub_graphs = []
                    for idx in range(num_sub_graphs):
                        if idx not in graphs_touched:
                            _sub_graphs.append(sub_graphs[idx])
                    _sub_graphs.append(connections)
                    sub_graphs = _sub_graphs
                    num_sub_graphs -= (num_touched-1)
            if num_sub_graphs == 1:
                break
        return num_sub_graphs

    def copy(self, name=None):
        """
        Args:
          name (str): name to be given to the copied circuit, if None then the name stays the same
        Returns:
          QuantumCircuit: a deepcopy of the current circuit, with the name updated if
                          it was provided
        """
        cpy = deepcopy(self)
        if name:
            cpy.name = name
        return cpy

    @staticmethod
    def from_qasm_file(path):
        """Take in a QASM file and generate a QuantumCircuit object.

        Args:
          path (str): Path to the file for a QASM program
        Return:
          QuantumCircuit: The QuantumCircuit object for the input QASM
        """
        qasm = _qasm.Qasm(filename=path)
        return _circuit_from_qasm(qasm)

    @staticmethod
    def from_qasm_str(qasm_str):
        """Take in a QASM string and generate a QuantumCircuit object.

        Args:
          qasm_str (str): A QASM program string
        Return:
          QuantumCircuit: The QuantumCircuit object for the input QASM
        """
        qasm = _qasm.Qasm(data=qasm_str)
        return _circuit_from_qasm(qasm)


def _circuit_from_qasm(qasm):
    # pylint: disable=cyclic-import
    from qiskit.converters import ast_to_dag
    from qiskit.converters import dag_to_circuit
    ast = qasm.parse()
    dag = ast_to_dag(ast)
    return dag_to_circuit(dag)
