# -*- coding: utf-8 -*-

# Copyright 2019, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""
Helper module for simplified Qiskit usage.

In general we recommend using the SDK modules directly. However, to get something
running quickly we have provided this wrapper module.
"""
import warnings
import logging

from qiskit.compiler import transpile, assemble

logger = logging.getLogger(__name__)


def execute(experiments, backend,
            basis_gates=None, coupling_map=None,  # circuit transpile options
            backend_properties=None, initial_layout=None,
            seed_transpiler=None, optimization_level=None, pass_manager=None,
            qobj_id=None, qobj_header=None, shots=1024,  # common run options
            memory=False, max_credits=10, seed_simulator=None,
            default_qubit_los=None, default_meas_los=None,  # schedule run options
            schedule_los=None, meas_level=2, meas_return='avg',
            memory_slots=None, memory_slot_size=100, rep_time=None,
            seed=None, seed_mapper=None,  # deprecated
            config=None, circuits=None,
            **run_config):
    """Execute a list of circuits or pulse schedules on a backend.

    The execution is asynchronous, and a handle to a job instance is returned.

    Args:
        experiments (QuantumCircuit or list[QuantumCircuit] or Schedule or list[Schedule]):
            Circuit(s) or pulse schedule(s) to execute

        backend (BaseBackend):
            Backend to execute circuits on.
            Transpiler options are automatically grabbed from
            backend.configuration() and backend.properties().
            If any other option is explicitly set (e.g. coupling_map), it
            will override the backend's.

        basis_gates (list[str]):
            List of basis gate names to unroll to.
            e.g:
                ['u1', 'u2', 'u3', 'cx']
            If None, do not unroll.

        coupling_map (CouplingMap or list):
            Coupling map (perhaps custom) to target in mapping.
            Multiple formats are supported:
            a. CouplingMap instance

            b. list
                Must be given as an adjacency matrix, where each entry
                specifies all two-qubit interactions supported by backend
                e.g:
                    [[0, 1], [0, 3], [1, 2], [1, 5], [2, 5], [4, 1], [5, 3]]

        backend_properties (BackendProperties):
            Properties returned by a backend, including information on gate
            errors, readout errors, qubit coherence times, etc. For a backend
            that provides this information, it can be obtained with:
            ``backend.properties()``

        initial_layout (Layout or dict or list):
            Initial position of virtual qubits on physical qubits.
            If this layout makes the circuit compatible with the coupling_map
            constraints, it will be used.
            The final layout is not guaranteed to be the same, as the transpiler
            may permute qubits through swaps or other means.

            Multiple formats are supported:
            a. Layout instance

            b. dict
                virtual to physical:
                    {qr[0]: 0,
                     qr[1]: 3,
                     qr[2]: 5}

                physical to virtual:
                    {0: qr[0],
                     3: qr[1],
                     5: qr[2]}

            c. list
                virtual to physical:
                    [0, 3, 5]  # virtual qubits are ordered (in addition to named)

                physical to virtual:
                    [qr[0], None, None, qr[1], None, qr[2]]

        seed_transpiler (int):
            Sets random seed for the stochastic parts of the transpiler

        optimization_level (int):
            How much optimization to perform on the circuits.
            Higher levels generate more optimized circuits,
            at the expense of longer transpilation time.
                0: no optimization
                1: light optimization
                2: heavy optimization

        pass_manager (PassManager):
            The pass manager to use during transpilation. If this arg is present,
            auto-selection of pass manager based on the transpile options will be
            turned off and this pass manager will be used directly.

        qobj_id (str):
            String identifier to annotate the Qobj

        qobj_header (QobjHeader or dict):
            User input that will be inserted in Qobj header, and will also be
            copied to the corresponding Result header. Headers do not affect the run.

        shots (int):
            Number of repetitions of each circuit, for sampling. Default: 2014

        memory (bool):
            If True, per-shot measurement bitstrings are returned as well
            (provided the backend supports it). For OpenPulse jobs, only
            measurement level 2 supports this option. Default: False

        max_credits (int):
            Maximum credits to spend on job. Default: 10

        seed_simulator (int):
            Random seed to control sampling, for when backend is a simulator

        default_qubit_los (list):
            List of default qubit lo frequencies

        default_meas_los (list):
            List of default meas lo frequencies

        schedule_los (None or list[Union[Dict[OutputChannel, float], LoConfig]] or
                      Union[Dict[OutputChannel, float], LoConfig]):
            Experiment LO configurations

        meas_level (int):
            Set the appropriate level of the measurement output for pulse experiments.

        meas_return (str):
            Level of measurement data for the backend to return
            For `meas_level` 0 and 1:
                "single" returns information from every shot.
                "avg" returns average measurement output (averaged over number of shots).

        memory_slots (int):
            Number of classical memory slots used in this job.

        memory_slot_size (int):
            Size of each memory slot if the output is Level 0.

        rep_time (int): repetition time of the experiment in μs.
            The delay between experiments will be rep_time.
            Must be from the list provided by the device.

        seed (int):
            DEPRECATED in 0.8: use ``seed_simulator`` kwarg instead

        seed_mapper (int):
            DEPRECATED in 0.8: use ``seed_transpiler`` kwarg instead

        config (dict):
            DEPRECATED in 0.8: use run_config instead

        circuits (QuantumCircuit or list[QuantumCircuit]):
            DEPRECATED in 0.8: use ``experiments`` kwarg instead.

        run_config (dict):
            Extra arguments used to configure the run (e.g. for Aer configurable backends)
            Refer to the backend documentation for details on these arguments
            Note: for now, these keyword arguments will both be copied to the
            Qobj config, and passed to backend.run()

    Returns:
        BaseJob: returns job instance derived from BaseJob

    Raises:
        QiskitError: if the execution cannot be interpreted as either circuits or schedules
    """
    if circuits is not None:
        experiments = circuits
        warnings.warn("the `circuits` arg in `execute()` has been deprecated. "
                      "please use `experiments`, which can handle both circuit "
                      "and pulse Schedules", DeprecationWarning)

    # transpiling the circuits using given transpile options
    experiments = transpile(experiments,
                            basis_gates=basis_gates,
                            coupling_map=coupling_map,
                            backend_properties=backend_properties,
                            initial_layout=initial_layout,
                            seed_transpiler=seed_transpiler,
                            optimization_level=optimization_level,
                            backend=backend,
                            pass_manager=pass_manager,
                            seed_mapper=seed_mapper,  # deprecated
                            )

    # assembling the circuits into a qobj to be run on the backend
    qobj = assemble(experiments,
                    qobj_id=qobj_id,
                    qobj_header=qobj_header,
                    shots=shots,
                    memory=memory,
                    max_credits=max_credits,
                    seed_simulator=seed_simulator,
                    default_qubit_los=default_qubit_los,
                    default_meas_los=default_meas_los,
                    schedule_los=schedule_los,
                    meas_level=meas_level,
                    meas_return=meas_return,
                    memory_slots=memory_slots,
                    memory_slot_size=memory_slot_size,
                    rep_time=rep_time,
                    backend=backend,
                    config=config,  # deprecated
                    seed=seed,  # deprecated
                    run_config=run_config
                    )

    # executing the circuits on the backend and returning the job
    return backend.run(qobj, **run_config)
