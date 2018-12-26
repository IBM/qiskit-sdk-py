# -*- coding: utf-8 -*-

# Copyright 2017, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""
Base backend object for the unroller that raises BackendError.
"""
from qiskit.unrollers.exceptions import BackendError


class UnrollerBackend:
    """Backend for the unroller that raises BackendError.

    This backend also serves as a base class for other unroller backends.
    """
    # pylint: disable=unused-argument

    def __init__(self, basis=None):
        """Setup this backend.

        basis is a list of operation name strings.
        """
        if basis:
            basis = []

    def set_basis(self, basis):
        """Declare the set of user-defined gates to emit.

        basis is a list of operation name strings.
        """
        raise BackendError("Backend set_basis unimplemented")

    def version(self, version):
        """Print the version string.

        v is a version number.
        """
        raise BackendError("Backend version unimplemented")

    def new_qreg(self, qreg):
        """Create a new quantum register.

        qreg = QuantumRegister object
        """
        raise BackendError("Backend new_qreg unimplemented")

    def new_creg(self, creg):
        """Create a new classical register.

        creg = ClassicalRegister object
        """
        raise BackendError("Backend new_creg unimplemented")

    def define_gate(self, name, gatedata):
        """Define a new quantum gate.

        name is a string.
        gatedata is the AST node for the gate.
        """
        raise BackendError("Backend define_gate unimplemented")

    def u(self, arg, qubit, nested_scope=None):
        """Fundamental single qubit gate.

        arg is 3-tuple of Node expression objects.
        qubit is (regname,idx) tuple.
        nested_scope is a list of dictionaries mapping expression variables
        to Node expression objects in order of increasing nesting depth.
        """
        # pylint: disable=invalid-name
        raise BackendError("Backend u unimplemented")

    def cx(self, qubit0, qubit1):
        """Fundamental two qubit gate.

        qubit0 is (regname,idx) tuple for the control qubit.
        qubit1 is (regname,idx) tuple for the target qubit.
        """
        # pylint: disable=invalid-name
        raise BackendError("Backend cx unimplemented")

    def measure(self, qubit, bit):
        """Measurement operation.

        qubit is (regname, idx) tuple for the input qubit.
        bit is (regname, idx) tuple for the output bit.
        """
        raise BackendError("Backend measure unimplemented")

    def barrier(self, qubitlists):
        """Barrier instruction.

        qubitlists is a list of lists of (regname, idx) tuples.
        """
        raise BackendError("Backend barrier unimplemented")

    def reset(self, qubit):
        """Reset instruction.

        qubit is a (regname, idx) tuple.
        """
        raise BackendError("Backend reset unimplemented")

    def set_condition(self, creg, cval):
        """Attach a current condition.

        creg is a name string.
        cval is the integer value for the test.
        """
        raise BackendError("Backend set_condition unimplemented")

    def drop_condition(self):
        """Drop the current condition."""
        raise BackendError("Backend drop_condition unimplemented")

    def start_gate(self, name, args, qubits, nested_scope=None, extra_fields=None):
        """Start a custom gate.

        Args:
            name (str): name of the gate.
            args (list[Node]): list of expression nodes.
            qubits (list[tuple(str, int)]): list of (regname, idx) tuples.
            nested_scope (list[dict()]): list of dictionaries mapping expression
                variables to Node expression objects in order of increasing
                nesting depth.
            extra_fields (dict(str, obj)): is a dictionary allowing the extension
                or overriding of the gate instruction properties.

        Raises:
            BackendError: if the gate is not part of the basis.
        """
        raise BackendError("Backend start_gate unimplemented")

    def end_gate(self, name, args, qubits, nested_scope=None):
        """End a custom gate.

        name is name string.
        args is list of Node expression objects.
        qubits is list of (regname, idx) tuples.
        nested_scope is a list of dictionaries mapping expression variables
        to Node expression objects in order of increasing nesting depth.
        """
        raise BackendError("Backend end_gate unimplemented")

    def get_output(self):
        """Returns the output generated by the backend.
        Depending on the type of Backend, the output could have different types.
        It must be called once the Qasm parsing has finished
        """
        raise BackendError("Backend get_output unimplemented")
