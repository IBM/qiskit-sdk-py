# -*- coding: utf-8 -*-

# Copyright 2019, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""Assemble function for converting a list of circuits into a qobj"""
import uuid

import numpy
import sympy

from qiskit.circuit.quantumcircuit import QuantumCircuit
from qiskit.compiler.run_config import RunConfig
from qiskit.qobj import (QasmQobj, QobjExperimentHeader, QobjHeader,
                         QasmQobjInstruction, QasmQobjExperimentConfig, QasmQobjExperiment,
                         QasmQobjConfig)


def assemble_circuits(circuits, run_config=None, qobj_header=None, qobj_id=None):
    """Assembles a list of circuits into a qobj which can be run on the backend.

    Args:
        circuits (list[QuantumCircuits] or QuantumCircuit): circuits to assemble
        run_config (RunConfig): RunConfig object
        qobj_header (QobjHeader): header to pass to the results
        qobj_id (int): identifier for the generated qobj

    Returns:
        QasmQobj: the Qobj to be run on the backends
    """
    qobj_header = qobj_header or QobjHeader()
    run_config = run_config or RunConfig()
    if isinstance(circuits, QuantumCircuit):
        circuits = [circuits]

    userconfig = QasmQobjConfig(**run_config.to_dict())
    experiments = []
    max_n_qubits = 0
    max_memory_slots = 0
    for circuit in circuits:
        # header stuff
        n_qubits = 0
        memory_slots = 0
        qubit_labels = []
        clbit_labels = []

        qreg_sizes = []
        creg_sizes = []
        for qreg in circuit.qregs:
            qreg_sizes.append([qreg.name, qreg.size])
            for j in range(qreg.size):
                qubit_labels.append([qreg.name, j])
            n_qubits += qreg.size
        for creg in circuit.cregs:
            creg_sizes.append([creg.name, creg.size])
            for j in range(creg.size):
                clbit_labels.append([creg.name, j])
            memory_slots += creg.size

        # TODO: why do we need creq_sizes and qreg_sizes in header
        # TODO: we need to rethink memory_slots as they are tied to classical bit
        experimentheader = QobjExperimentHeader(qubit_labels=qubit_labels,
                                                n_qubits=n_qubits,
                                                qreg_sizes=qreg_sizes,
                                                clbit_labels=clbit_labels,
                                                memory_slots=memory_slots,
                                                creg_sizes=creg_sizes,
                                                name=circuit.name)
        # TODO: why do we need n_qubits and memory_slots in both the header and the config
        experimentconfig = QasmQobjExperimentConfig(n_qubits=n_qubits, memory_slots=memory_slots)

        # Convert conditionals from QASM-style (creg ?= int) to qobj-style
        # (register_bit ?= 1), by assuming device has unlimited register slots
        # (supported only for simulators). Map all measures to a register matching
        # their clbit_index, create a new register slot for every conditional gate
        # and add a bfunc to map the creg=val mask onto the gating register bit.

        is_conditional_experiment = any(op.control for (op, qargs, cargs) in circuit.data)
        max_conditional_idx = 0

        instructions = []
        for op_context in circuit.data:
            op = op_context[0]
            qargs = op_context[1]
            cargs = op_context[2]
            current_instruction = QasmQobjInstruction(name=op.name)
            if qargs:
                qubit_indices = [qubit_labels.index([qubit[0].name, qubit[1]])
                                 for qubit in qargs]
                current_instruction.qubits = qubit_indices
            if cargs:
                clbit_indices = [clbit_labels.index([clbit[0].name, clbit[1]])
                                 for clbit in cargs]
                current_instruction.memory = clbit_indices

                # If the experiment has conditional instructions, assume every
                # measurement result may be needed for a conditional gate.
                if op.name == "measure" and is_conditional_experiment:
                    current_instruction.register = clbit_indices

            if op.params:
                params = list(map(lambda x: x.evalf(), op.params))
                params = [sympy.matrix2numpy(x, dtype=complex)
                          if isinstance(x, sympy.Matrix) else x for x in params]
                if len(params) == 1 and isinstance(params[0], numpy.ndarray):
                    # TODO: Aer expects list of rows for unitary instruction params;
                    # change to matrix in Aer.
                    params = params[0]
                current_instruction.params = params
            # TODO: I really dont like this for snapshot. I also think we should change
            # type to snap_type
            if op.name == "snapshot":
                current_instruction.label = str(op.params[0])
                current_instruction.type = str(op.params[1])
            if op.name == 'unitary':
                if op._label:
                    current_instruction.label = op._label
            if op.control:
                # To convert to a qobj-style conditional, insert a bfunc prior
                # to the conditional instruction to map the creg ?= val condition
                # onto a gating register bit.
                mask = 0
                val = 0

                for clbit in clbit_labels:
                    if clbit[0] == op.control[0].name:
                        mask |= (1 << clbit_labels.index(clbit))
                        val |= (((op.control[1] >> clbit[1]) & 1) << clbit_labels.index(clbit))

                conditional_reg_idx = memory_slots + max_conditional_idx
                conversion_bfunc = QasmQobjInstruction(name='bfunc',
                                                       mask="0x%X" % mask,
                                                       relation='==',
                                                       val="0x%X" % val,
                                                       register=conditional_reg_idx)
                instructions.append(conversion_bfunc)

                current_instruction.conditional = conditional_reg_idx
                max_conditional_idx += 1

            instructions.append(current_instruction)

        experiments.append(QasmQobjExperiment(instructions=instructions, header=experimentheader,
                                              config=experimentconfig))
        if n_qubits > max_n_qubits:
            max_n_qubits = n_qubits
        if memory_slots > max_memory_slots:
            max_memory_slots = memory_slots

    userconfig.memory_slots = max_memory_slots
    userconfig.n_qubits = max_n_qubits

    return QasmQobj(qobj_id=qobj_id or str(uuid.uuid4()), config=userconfig,
                    experiments=experiments, header=qobj_header)
