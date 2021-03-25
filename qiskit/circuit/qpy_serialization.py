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

# pylint: disable=invalid-name,too-many-boolean-expressions,redundant-keyword-arg

"""
===========================================================
QPY serialization (:mod:`qiskit.circuit.qpy_serialization`)
===========================================================

.. currentmodule:: qiskit.circuit.qpy_serialization

.. autosummary::

    load
    dump

QPY Format
==========

The QPY serialization format is a portable cross-platform binary
serialization format for :class:`~qiskit.circuit.QuantumCircuit` objects in Qiskit. The basic
file format is as follows:

A QPY file (or memory object) always starts with the following 7
byte UTF8 string: ``QISKIT`` which is immediately followed by the overall
file header. The contents of thie file header as defined as a C struct are:

.. code-block:: c

    struct {
        unsigned char qpy_version;
        unsigned char qiskit_major_version;
        unsigned char qiskit_minor_version;
        unsigned char qiskit_patch_version;
        unsigned long long num_circuits;
    }

All values use network byte order [#f1]_ (big endian) for cross platform
compatibility. All strings will be padded with ``0x00`` after the string
if the string is shorter than the max size.

The file header is immediately followed by the circuit payloads.
Each individual circuit is composed of the following parts:

``HEADER | METADATA | REGISTERS | CUSTOM_DEFINITIONS | INSTRUCTIONS``

There is a circuit payload for each circuit (where the total number is dictated
by ``num_circuits`` in the file header). There is no padding between the
circuits in the data.

HEADER
------

The contents of HEADER as defined as a C struct are:

.. code-block:: c

    struct {
        char name[32];
        double global_phase;
        unsigned int num_qubits;
        unsigned int num_clbits;
        unsigned long long metadata_size;
        unsigned int num_registers;
        unsigned long long num_instructions;
        unsigned long long num_custom_gates;
    }

METADATA
--------

The METADATA field is a UTF8 encoded json string. After reading the HEADER
(which is a fixed size at the start of the QPY file you then read the
``metadata_size`` number of bytes and parse the JSON to get the metadata for
the circuit.

REGISTERS
---------

The contents of REGISTERS is a number of REGISTER object. If num_registers is
> 0 then after reading METADATA you read that number of REGISTER structs defined
as:

.. code-block:: c

    struct {
        char type;
        unsigned int size;
        char name[10];
    }

``type`` can be ``'q'`` or ``'c'``.

CUSTOM_DEFINITIONS
------------------

If the circuit contains custom defitions for any of the instruction in the circuit.
this section

CUSTOM_DEFINITION_HEADER contents are defined as:

.. code-block:: c

    struct {
        unsigned long long size;
    }

If size is greater than 0 that means the circuit contains custom instruction(s).
Each custom instruction is defined with a CUSTOM_INSTRUCTION block defined as:

.. code-block:: c

    struct {
        char name[32];
        char type;
        _Bool custom_definition;
        unsigned long long size
    }

If ``custom_definition`` is ``True`` that means that the immediately following
` size`` bytes contains a QPY circuit data which can be used for the custom
definition of that gate. If ``custom_definition`` is ``False`` than the
instruction can be considered opaque (ie no definition).

INSTRUCTIONS
------------

The contents of INSTRUCTIONS is a list of INSTRUCTION metadata objects

.. code-block:: c

    struct {
        char name[32];
        unsigned short num_parameters;
        unsigned int num_qargs;
        unsigned int num_cargs;
        _Bool has_conditionl
        char conditonal_reg[10];
        long long conditional_value;
    }

``name`` here is the Qiskit class name for the Instruction class if it's
defined in Qiskit. Otherwise it falls back to the custom instruction name.

which is immediately followed by the INSTRUCTION_ARG structs for the list of
arguments of that instruction. These are in the order of all quantum arguments
(there are num_qargs of these) followed by all classical arguments (num_cargs
of these).

The contents of each INSTRUCTION_ARG is:

.. code-block:: c

    struct {
        char type;
        unisgned int size;
        char name[10];
    }

``type`` can be ``'q'`` or ``'c'``.

After all arguments for an instruction the parameters are specified with
``num_parameters`` INSTRUCTION_PARAM structs.

The contents of each INSTRUCTION_PARAM is:

.. code-block:: c

    struct {
        char type;
        unsigned long long size;
    }

After each INSTRUCTION_PARAM the next ``size`` bytes are the parameter's data.
The ``type`` field can be ``'i'``, ``'f'``, ``'p'``, or ``'n'`` which dictate
the format. For ``'i'`` it's an integer, ``'f'`` it's a double, ``'p'`` defines
a :class:`~qiskit.circuit.Paramter` object  which is represented by a PARAM
struct (see below), and ``'n'`` represents an object from numpy (either an
``ndarray`` or a numpy type) which means the data is .npy format [#f2]_
data.


PARAMETER
---------

A PARAMETER represents a :class:`~qiskit.circuit.Parameter` object the data for
a INSTRUCTION_PARAM. The contents of the PARAMETER are defined as:

.. code-block:: c

    struct {
        char name[32];
        char uuid[16];
    }

.. [#f1] https://tools.ietf.org/html/rfc1700
.. [#f2] https://numpy.org/doc/stable/reference/generated/numpy.lib.format.html
"""
from collections import namedtuple
import io
import json
import struct
import uuid
import warnings

import numpy as np

from qiskit.circuit.quantumcircuit import QuantumCircuit
from qiskit.circuit.quantumregister import QuantumRegister
from qiskit.circuit.classicalregister import ClassicalRegister
from qiskit.circuit.parameter import Parameter
from qiskit.circuit.gate import Gate
from qiskit.circuit.instruction import Instruction
from qiskit.circuit import library
from qiskit import circuit as circuit_mod
from qiskit import extensions
from qiskit.extensions import quantum_initializer
from qiskit.version import __version__
from qiskit.exceptions import QiskitError

# v1 Binary Format
# ----------------
# FILE_HEADER
FILE_HEADER = namedtuple('FILE_HEADER', ['preface', 'qpy_version', 'major_version',
                                         'minor_version', 'patch_version',
                                         'num_circuits'])
FILE_HEADER_PACK = '!6sBBBBQ'
FILE_HEADER_SIZE = struct.calcsize(FILE_HEADER_PACK)

# HEADER binary format
HEADER = namedtuple('HEADER', ['name', 'global_phase',
                               'num_qubits', 'num_clbits', 'metadata_size',
                               'num_registers', 'num_instructions'])
HEADER_PACK = '!32sdIIQIQ'
HEADER_SIZE = struct.calcsize(HEADER_PACK)

# CUSTOM_DEFINITIONS
# CUSTOM DEFINITION HEADER
CUSTOM_DEFINITION_HEADER = namedtuple('CUSTOM_DEFINITION_HEADER', ['size'])
CUSTOM_DEFINITION_HEADER_PACK = '!Q'
CUSTOM_DEFINITION_HEADER_SIZE = struct.calcsize(CUSTOM_DEFINITION_HEADER_PACK)

# CUSTOM_DEFINITION
CUSTOM_DEFINITION = namedtuple('CUSTOM_DEFINITON',
                               ['gate_name', 'type', 'num_qubits'
                                'num_clbits', 'custom_definition', 'size'])
CUSTOM_DEFINITION_PACK = '!32s1cII?Q'
CUSTOM_DEFINITION_SIZE = struct.calcsize(CUSTOM_DEFINITION_PACK)


# REGISTER binary format
REGISTER = namedtuple('REGISTER', ['type', 'size', 'name'])
REGISTER_PACK = '!1cI10s'
REGISTER_SIZE = struct.calcsize(REGISTER_PACK)

# INSTRUCTION binary format
INSTRUCTION = namedtuple('INSTRUCTION', ['name', 'num_parameters', 'num_qargs',
                                         'num_cargs', 'has_condition',
                                         'condition_register', 'value'])
INSTRUCTION_PACK = '!32sHII?10sq'
INSTRUCTION_SIZE = struct.calcsize(INSTRUCTION_PACK)
# Instruction argument format
INSTRUCTION_ARG = namedtuple('INSTRUCTION_ARG', ['type', 'size', 'name'])
INSTRUCTION_ARG_PACK = '!1cI10s'
INSTRUCTION_ARG_SIZE = struct.calcsize(INSTRUCTION_ARG_PACK)
# INSTRUCTION parameter format
INSTRUCTION_PARAM = namedtuple('INSTRUCTION_PARAM', ['type', 'size'])
INSTRUCTION_PARAM_PACK = '!1cQ'
INSTRUCTION_PARAM_SIZE = struct.calcsize(INSTRUCTION_PARAM_PACK)
# PARAMETER
PARAMETER = namedtuple('PARAMETER', ['name', 'uuid'])
PARAMETER_PACK = '!32s16s'
PARAMETER_SIZE = struct.calcsize(PARAMETER_PACK)


def _read_header(file_obj):
    header_raw = struct.unpack(HEADER_PACK, file_obj.read(HEADER_SIZE))
    header = HEADER._make(header_raw)
    metadata_raw = file_obj.read(header[4])
    metadata = json.loads(metadata_raw)
    return header, metadata


def _read_registers(file_obj, num_registers):
    registers = {'q': {}, 'c': {}}
    for _reg in range(num_registers):
        register_raw = file_obj.read(REGISTER_SIZE)
        register = struct.unpack(REGISTER_PACK, register_raw)
        name = register[2].decode('utf8').rstrip('\x00')
        if register[0].decode('utf8') == 'q':
            registers['q'][name] = QuantumRegister(register[1], name)
        else:
            registers['c'][name] = ClassicalRegister(register[1], name)
    return registers


def _read_instruction(file_obj, circuit, registers, custom_instructions):
    instruction_raw = file_obj.read(INSTRUCTION_SIZE)
    instruction = struct.unpack(INSTRUCTION_PACK, instruction_raw)
    qargs = []
    cargs = []
    params = []
    gate_name = instruction[0].decode('utf8').rstrip('\x00')
    num_qargs = instruction[2]
    num_cargs = instruction[3]
    num_params = instruction[1]
    has_condition = instruction[4]
    condition_register = instruction[5].decode('utf8').rstrip('\x00')
    condition_value = instruction[6]
    condition_tuple = None
    if has_condition:
        condition_tuple = (registers['c'][condition_register], condition_value)
    # Load Arguments
    for _qarg in range(num_qargs):
        qarg_raw = file_obj.read(INSTRUCTION_ARG_SIZE)
        qarg = struct.unpack(INSTRUCTION_ARG_PACK, qarg_raw)
        if qarg[0].decode('utf8').rstrip('\x00') == 'c':
            raise TypeError('Invalid input carg prior to all qargs')
        name = qarg[2].decode('utf8').rstrip('\x00')
        qargs.append(registers['q'][name][qarg[1]])
    for _carg in range(num_cargs):
        carg_raw = file_obj.read(INSTRUCTION_ARG_SIZE)
        carg = struct.unpack(INSTRUCTION_ARG_PACK, carg_raw)
        if carg[0].decode('utf8').rstrip('\x00') == 'q':
            raise TypeError('Invalid input qarg after all qargs')
        name = carg[2].decode('utf8').rstrip('\x00')
        cargs.append(registers['c'][name][carg[1]])
    # Load Parameters
    for _param in range(num_params):
        param_raw = file_obj.read(INSTRUCTION_PARAM_SIZE)
        param = struct.unpack(INSTRUCTION_PARAM_PACK, param_raw)
        data = file_obj.read(param[1])
        type_str = param[0].decode('utf8')
        param = None
        if type_str == 'i':
            param = struct.unpack('<q', data)[0]
        elif type_str == 'f':
            param = struct.unpack('<d', data)[0]
        elif type_str == 'n':
            container = io.BytesIO()
            container.write(data)
            container.seek(0)
            param = np.load(container)
        elif type_str == 'p':
            param_raw = struct.unpack(PARAMETER_PACK, data)
            name = param_raw[0].decode('utf8').rstrip('\x00')
            param_uuid = uuid.UUID(bytes=param_raw[1])
            param = Parameter.__new__(Parameter, name, uuid=param_uuid)
            param.__init__(name)
        else:
            raise TypeError("Invalid parameter type: %s" % type_str)
        params.append(param)
    # Load Gate object
    gate_class = None
    if gate_name in ('Gate', 'Instruction'):
        inst_obj = _parse_custom_instruction(custom_instructions, gate_name,
                                             params)
        inst_obj.condition = condition_tuple
        circuit._append(inst_obj, qargs, cargs)
        return
    elif hasattr(library, gate_name):
        gate_class = getattr(library, gate_name)
    elif hasattr(circuit_mod, gate_name):
        gate_class = getattr(circuit_mod, gate_name)
    elif hasattr(extensions, gate_name):
        gate_class = getattr(extensions, gate_name)
    elif hasattr(quantum_initializer, gate_name):
        gate_class = getattr(quantum_initializer, gate_name)
    elif gate_name in custom_instructions:
        inst_obj = _parse_custom_instruction(custom_instructions, gate_name,
                                             params)
        inst_obj.condition = condition_tuple
        circuit._append(inst_obj, qargs, cargs)
        return
    else:
        raise AttributeError("Invalid instruction type: %s" % gate_name)
    if gate_name == 'Barrier':
        params = [len(qargs)]
    gate = gate_class(*params)
    gate.condition = condition_tuple
    circuit._append(gate, qargs, cargs)


def _parse_custom_instruction(custom_instructions, gate_name, params):
    (type_str, num_qubits, num_clbits,
     definition) = custom_instructions[gate_name]
    if type_str == 'i':
        inst_obj = Instruction(gate_name, num_qubits, num_clbits, params)
        if definition:
            inst_obj.definition = definition
    elif type_str == 'g':
        inst_obj = Gate(gate_name, num_qubits, params)
        inst_obj.definition = definition
    else:
        raise ValueError("Invalid custom instruction type '%s'" % type_str)
    return inst_obj


def _read_custom_instructions(file_obj):
    custom_instructions = {}
    custom_definition_header_raw = file_obj.read(CUSTOM_DEFINITION_HEADER_SIZE)
    custom_definition_header = struct.unpack(CUSTOM_DEFINITION_HEADER_PACK,
                                             custom_definition_header_raw)
    if custom_definition_header[0] > 0:
        for _ in range(custom_definition_header[0]):
            custom_definition_raw = file_obj.read(CUSTOM_DEFINITION_SIZE)
            custom_definition = struct.unpack(CUSTOM_DEFINITION_PACK,
                                              custom_definition_raw)
            (name, type_str, num_qubits,
             num_clbits, has_custom_definition, size) = custom_definition
            name = name.decode('utf8').rstrip('\x00')
            type_str = type_str.decode('utf8')
            definition_circuit = None
            if has_custom_definition:
                definition_buffer = io.BytesIO(file_obj.read(size))
                definition_circuit = _read_circuit(definition_buffer)
            custom_instructions[name] = (type_str, num_qubits, num_clbits,
                                         definition_circuit)
    return custom_instructions


def _write_instruction(file_obj, instruction_tuple, custom_instructions):
    gate_class_name = instruction_tuple[0].__class__.__name__
    if ((not hasattr(library, gate_class_name) and
         not hasattr(circuit_mod, gate_class_name) and
         not hasattr(extensions, gate_class_name) and
         not hasattr(quantum_initializer, gate_class_name)) or
            gate_class_name == 'Gate' or gate_class_name == 'Instruction'):
        if instruction_tuple[0].name not in custom_instructions:
            custom_instructions[
                instruction_tuple[0].name] = instruction_tuple[0]
        gate_class_name = instruction_tuple[0].name

    has_condition = False
    condition_register = ''.encode('utf8')
    condition_value = 0
    if instruction_tuple[0].condition:
        has_condition = True
        condition_register = instruction_tuple[0].condition[0].name.encode(
            'utf8')
        condition_value = instruction_tuple[0].condition[1]

    gate_class_name = gate_class_name.encode('utf8')
    instruction_raw = struct.pack(INSTRUCTION_PACK, gate_class_name,
                                  len(instruction_tuple[0].params),
                                  instruction_tuple[0].num_qubits,
                                  instruction_tuple[0].num_clbits,
                                  has_condition, condition_register,
                                  condition_value)
    file_obj.write(instruction_raw)
    # Encode instruciton args
    for qbit in instruction_tuple[1]:
        instruction_arg_raw = struct.pack(INSTRUCTION_ARG_PACK,
                                          'q'.encode('utf8'),
                                          qbit.index,
                                          qbit.register.name.encode('utf8'))
        file_obj.write(instruction_arg_raw)
    for clbit in instruction_tuple[2]:
        instruction_arg_raw = struct.pack(INSTRUCTION_ARG_PACK,
                                          'c'.encode('utf8'),
                                          clbit.index,
                                          clbit.register.name.encode('utf8'))
        file_obj.write(instruction_arg_raw)
    # Encode instruction params
    for param in instruction_tuple[0].params:
        container = io.BytesIO()
        if isinstance(param, int):
            type_key = 'i'
            data = struct.pack('<q', param)
            size = struct.calcsize('<q')
        elif isinstance(param, float):
            type_key = 'f'
            data = struct.pack('<d', param)
            size = struct.calcsize('<d')
        elif isinstance(param, Parameter):
            type_key = 'p'
            data = struct.pack(PARAMETER_PACK, param._name.encode('utf8'),
                               param._uuid.bytes)
            size = PARAMETER_SIZE
        elif isinstance(param, (np.integer, np.floating, np.ndarray)):
            type_key = 'n'
            np.save(container, param)
            container.seek(0)
            data = container.read()
            size = len(data)
        else:
            raise TypeError("Invalid parameter type %s for gate %s," % (
                instruction_tuple[0], type(param)))
        instruction_param_raw = struct.pack(INSTRUCTION_PARAM_PACK,
                                            type_key.encode('utf8'), size)
        file_obj.write(instruction_param_raw)
        file_obj.write(data)
        container.close()


def _write_custom_instruction(file_obj, name, instruction):
    if isinstance(instruction, Gate):
        type_str = 'g'.encode('utf8')
    else:
        type_str = 'i'.encode('utf8')
    has_definition = False
    size = 0
    data = None
    num_qubits = instruction.num_qubits
    num_clbits = instruction.num_clbits
    if instruction.definition:
        has_definition = True
        definition_buffer = io.BytesIO()
        _write_circuit(definition_buffer, instruction.definition)
        definition_buffer.seek(0)
        data = definition_buffer.read()
        definition_buffer.close()
        size = len(data)
    custom_instruction_raw = struct.pack(CUSTOM_DEFINITION_PACK,
                                         name.encode('utf8'), type_str,
                                         num_qubits, num_clbits,
                                         has_definition, size)
    file_obj.write(custom_instruction_raw)
    if data:
        file_obj.write(data)


def dump(file_obj, circuits):
    """Write QPY binary data to a file

    This function is used to save a circuit to a file for later use or transfer
    between machines. The output QPY file is forward compatible and can be loaded
    with future versions of Qiskit. For example:

    .. code-block:: python

        from qiskit.circuit import QuantumCircuit
        from qiskit.circuit import qpy_serialization

        qc = QuantumCircuit(2, name='Bell', metadata={'test': True})
        qc.h(0)
        qc.cx(0, 1)
        qc.measure_all()

    from this you can write the qpy data to a file:

    .. code-block:: python

        with open('bell.qpy', 'wb') as fd:
            qpy_serialization.dump(fd, qc)

    or a gzip compressed filed:

    .. code-block:: python

        import gzip

        with gzip.open('bell.qpy.gz', 'wb') as fd:
            qpy_serialization.dump(fd, qc)

    Which will save the qpy serialized circuit to the provided file.

    Args:
        file_obj (file): The file like object to write the QPY data too
        circuits (list or QuantumCircuit): The quantum circuit object(s) to
            store in the specified file like object. This can either be a
            single QuantumCircuit object or a list of QuantumCircuits.
    """
    if isinstance(circuits, QuantumCircuit):
        circuits = [circuits]
    version_parts = [int(x) for x in __version__.split('.')[0:3]]
    header = struct.pack(FILE_HEADER_PACK, 'QISKIT'.encode('utf8'), 1,
                         version_parts[0], version_parts[1], version_parts[2],
                         len(circuits))
    file_obj.write(header)
    for circuit in circuits:
        _write_circuit(file_obj, circuit)


def _write_circuit(file_obj, circuit):
    metadata_raw = json.dumps(circuit.metadata,
                              separators=(',', ':')).encode('utf8')
    metadata_size = len(metadata_raw)
    num_registers = len(circuit.qregs) + len(circuit.cregs)
    num_instructions = len(circuit)
    header_raw = HEADER(name=circuit.name.encode('utf8'),
                        global_phase=circuit.global_phase,
                        num_qubits=circuit.num_qubits,
                        num_clbits=circuit.num_clbits,
                        metadata_size=metadata_size,
                        num_registers=num_registers,
                        num_instructions=num_instructions)
    header = struct.pack(HEADER_PACK, *header_raw)
    file_obj.write(header)
    file_obj.write(metadata_raw)
    if num_registers > 0:
        for reg in circuit.qregs:
            file_obj.write(struct.pack(REGISTER_PACK, 'q'.encode('utf8'),
                                       reg.size, reg.name.encode('utf8')))
        for reg in circuit.cregs:
            file_obj.write(struct.pack(REGISTER_PACK, 'c'.encode('utf8'),
                                       reg.size, reg.name.encode('utf8')))
    instruction_buffer = io.BytesIO()
    custom_instructions = {}
    for instruction in circuit.data:
        _write_instruction(instruction_buffer, instruction,
                           custom_instructions)
    file_obj.write(struct.pack(CUSTOM_DEFINITION_HEADER_PACK,
                               len(custom_instructions)))

    for name, instruction in custom_instructions.items():
        _write_custom_instruction(file_obj, name, instruction)

    instruction_buffer.seek(0)
    file_obj.write(instruction_buffer.read())
    instruction_buffer.close()


def load(file_obj):
    """Load a QPY binary file

    This function is used to load a serialized QPY circuit file and create
    :class:`~qiskit.circuit.QuantumCircuit` objects from its contents.
    For example:

    .. code-block:: python

        from qiskit.circuit import qpy_serialization

        with open('bell.qpy', 'rb') as fd:
            circuits = qpy_serialization.load(fd)

    or with a gzip compressed file:

    .. code-block:: python

        import gzip
        from qiskit.circuit import qpy_serialization

        with gzip.open('bell.qpy.gz', 'rb') as fd:
            circuits = qpy_serialization.load(fd)

    which will read the contents of the qpy and return a list of
    :class:`~qiskit.circuit.QuantumCircuit` objects from the file.

    Args:
        file_obj (File): A file like object that contains the QPY binary
            data for a circuit
    Returns:
        list: A list of the QuantumCircuit objects from the QPY data. A list
            is always returned, even if there is only 1 circuit in the QPY
            data.
    Raises:
        QiskitError: if ``file_obj`` is not a valid QPY file
    """
    file_header_raw = file_obj.read(FILE_HEADER_SIZE)
    file_header = struct.unpack(FILE_HEADER_PACK, file_header_raw)
    if file_header[0].decode('utf8') != 'QISKIT':
        raise QiskitError('Input file is not a valid QPY file')
    version_parts = [int(x) for x in __version__.split('.')[0:3]]
    header_version_parts = [file_header[2], file_header[3], file_header[4]]
    if version_parts[0] < header_version_parts[0] or (
            version_parts[0] == header_version_parts[0] and
            header_version_parts[1] > version_parts[1]) or (
                version_parts[0] == header_version_parts[0] and
                header_version_parts[1] == version_parts[1] and
                header_version_parts[2] > version_parts[2]):
        warnings.warn('The qiskit version used to generate the provided QPY '
                      'file, %s, is newer than the current qiskit version %s. '
                      'This may result in an error if the QPY file uses '
                      'instructions not present in this current qiskit '
                      'version' % ('.'.join(header_version_parts),
                                   __version__))
    circuits = []
    for _ in range(file_header[5]):
        circuits.append(_read_circuit(file_obj))
    return circuits


def _read_circuit(file_obj):
    header, metadata = _read_header(file_obj)
    registers = {}
    if header[5] > 0:
        circ = QuantumCircuit(name=header[0].decode('utf8').rstrip('\x00'),
                              global_phase=header[1],
                              metadata=metadata)
        registers = _read_registers(file_obj, header[5])
        for qreg in registers['q'].values():
            circ.add_register(qreg)
        for creg in registers['c'].values():
            circ.add_register(creg)
    else:
        circ = QuantumCircuit(header[2], header[3],
                              name=header[0].decode('utf8').rstrip('\x00'),
                              global_phase=header[1],
                              metadata=metadata)
    custom_instructions = _read_custom_instructions(file_obj)
    for _instruction in range(header[6]):
        _read_instruction(file_obj, circ, registers, custom_instructions)

    return circ
