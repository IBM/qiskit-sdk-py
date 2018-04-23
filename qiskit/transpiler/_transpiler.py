# -*- coding: utf-8 -*-
# pylint: disable=redefined-builtin

# Copyright 2018 IBM RESEARCH. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =============================================================================

"""Tools for compiling a batch of quantum circuits."""
import logging

import random
import string
import copy

from qiskit._quantumcircuit import QuantumCircuit
from qiskit.dagcircuit import DAGCircuit
from qiskit.unroll import DagUnroller, DAGBackend, JsonBackend
from qiskit.mapper import (Coupling, optimize_1q_gates, coupling_list2dict, swap_mapper,
                           cx_cancellation, direction_mapper)
from qiskit.transpiler import PassManager, QISKitTranspilerError

logger = logging.getLogger(__name__)

COMPILE_CONFIG_DEFAULT = {
    'config': None,
    'basis_gates': None,
    'coupling_map': None,
    'initial_layout': None,
    'shots': 1024,
    'max_credits': 10,
    'seed': 1,
    'qobj_id': None,
    'hpc': None
}


def compile(circuits, backend, compile_config=None, pass_manager=None):
    """Compile a list of circuits into a qobj.

    Args:
        circuits (list[QuantumCircuit]): list of circuits
        backend (BaseBackend): a backend object to use as the default compiling
            option
        compile_config (dict or None): a dictionary of compile configurations.
            If `None`, the default compile configuration will be used.
        pass_manager (PassManager): a pass_manager for the transpiler stage,
            with a set of passes to run

    Returns:
        obj: the qobj to be run on the backends

    Raises:
        QISKitTranspilerError: in case of bad compile options, e.g. the hpc options.
    """
    if isinstance(circuits, QuantumCircuit):
        circuits = [circuits]

    compile_config = compile_config or {}
    compile_config = {**COMPILE_CONFIG_DEFAULT, **compile_config}
    config = compile_config['config']
    basis_gates = compile_config['basis_gates']
    coupling_map = compile_config['coupling_map']
    initial_layout = compile_config['initial_layout']
    shots = compile_config['shots']
    max_credits = compile_config['max_credits']
    seed = compile_config['seed']
    qobj_id = compile_config['qobj_id']
    hpc = compile_config['hpc']

    qobj = {}

    # step 1: populate the qobj-level `id`
    if not qobj_id:
        qobj_id = "".join([random.choice(string.ascii_letters + string.digits)
                           for n in range(30)])
    qobj['id'] = qobj_id

    # step 2: populate the qobj-level `config`
    backend_name = backend.configuration['name']
    qobj['config'] = {'max_credits': max_credits,
                      'shots': shots,
                      'backend_name': backend_name}

    if 'hpc' in backend_name:
        if hpc is None:
            logger.info('hpc simulator backend needs HPC parameters. Setting defaults '
                        'to multi_shot_optimization=True and omp_num_threads=16')
            hpc = {'multi_shot_optimization': True, 'omp_num_threads': 16}
        if not all(key in hpc for key in
                   ('multi_shot_optimization', 'omp_num_threads')):
            raise QISKitTranspilerError('Unknown HPC parameter format!')
        qobj['config']['hpc'] = hpc
    elif hpc is not None:
        logger.info('Ignoring HPC parameter: only available for hpc simulator backends.')
        hpc = None

    # step 3: populate the `circuits` in qobj, after compiling each circuit
    qobj['circuits'] = []

    if not basis_gates:
        basis_gates = backend.configuration.get('basis_gates')
        assert basis_gates, "basis_gates neither specified nor available from backend"
    elif len(basis_gates.split(',')) < 2:
        # catches deprecated basis specification like 'SU2+CNOT'
        logger.warning('encountered deprecated basis specification: '
                       '"%s" substituting u1,u2,u3,cx,id', str(basis_gates))
        basis_gates = 'u1,u2,u3,cx,id'

    if not coupling_map:
        coupling_map = backend.configuration.get('coupling_map')
        assert basis_gates, "coupling_map neither specified nor available from backend"

    for circuit in circuits:
        job = {}

        # step 1: populate the circuit-level `name`
        job["name"] = circuit.name

        # step 2: populate the circuit-level `config`
        if config is None:
            config = {}
        job["config"] = copy.deepcopy(config)
        # TODO: A better solution is to have options to enable/disable optimizations
        num_qubits = sum((len(qreg) for qreg in circuit.get_qregs().values()))
        if num_qubits == 1 or coupling_map == "all-to-all":
            coupling_map = None
        job["config"]["coupling_map"] = coupling_map
        job["config"]["basis_gates"] = basis_gates
        job["config"]["seed"] = seed

        # step 3: populate the circuit `instructions` after compilation
        # step 3a: circuit -> dag
        dag_circuit = DAGCircuit.fromQuantumCircuit(circuit)

        # step 3b: transpile (dag -> dag)
        dag_circuit, final_layout = transpile(
            dag_circuit,
            basis_gates=basis_gates,
            coupling_map=coupling_map,
            initial_layout=initial_layout,
            get_layout=True,
            pass_manager=pass_manager)
        # Map the layout to a format that can be json encoded
        list_layout = None
        if final_layout:
            list_layout = [[k, v] for k, v in final_layout.items()]
        job["config"]["layout"] = list_layout

        # step 3c: dag -> json
        # TODO: populate the Qobj object when Qobj class exists
        # the compiled circuit to be run saved as a dag
        # we assume that transpile() has already expanded gates
        # to the target basis, so we just need to generate json
        json_circuit = DagUnroller(dag_circuit, JsonBackend(dag_circuit.basis)).execute()
        job["compiled_circuit"] = json_circuit

        # set eval_symbols=True to evaluate each symbolic expression
        # TODO after transition to qobj, we can drop this
        job["compiled_circuit_qasm"] = dag_circuit.qasm(qeflag=True,
                                                        eval_symbols=True)

        # add job to the qobj
        qobj["circuits"].append(job)
    return qobj


def transpile(dag_circuit, basis_gates='u1,u2,u3,cx,id', coupling_map=None,
              initial_layout=None, get_layout=False, pass_manager=None, format='dag'):
    """Transcompile (transpile) a dag circuit to another dag circuit, through
    consecutive passes on the dag.

    Args:
        dag_circuit (DAGCircuit): dag circuit to transform via transpilation
        basis_gates (str): a comma seperated string and are the base gates,
                           which by default are: u1,u2,u3,cx,id
        coupling_map (list): A graph of coupling::

            [
             [control0(int), target0(int)],
             [control1(int), target1(int)],
            ]

            eg. [[0, 2], [1, 2], [1, 3], [3, 4]}

        initial_layout (dict): A mapping of qubit to qubit::

                              {
                                ("q", start(int)): ("q", final(int)),
                                ...
                              }
                              eg.
                              {
                                ("q", 0): ("q", 0),
                                ("q", 1): ("q", 1),
                                ("q", 2): ("q", 2),
                                ("q", 3): ("q", 3)
                              }
        get_layout (bool): flag for returning the layout.
        pass_manager (PassManager): if None, a default set of passes are run.
            Otherwise, the passes defined in it will run
        format (str): The target format of the compilation:
            {'dag', 'json', 'qasm'}

    Returns:
        object: If get_layout == False, the compiled circuit in the specified
            format. If get_layout == True, a tuple is returned, with the
            second element being the layout.

    Raises:
        QISKitTranspilerError: if the format is not valid.
    """
    final_layout = None
    if pass_manager:
        # run the passes specified by the pass manager
        for pass_ in pass_manager.passes():
            pass_.run(dag_circuit)

    else:
        # default set of passes
        # TODO: move each step here to a pass, and use a default passmanager below
        basis = basis_gates.split(',') if basis_gates else []
        dag_unroller = DagUnroller(dag_circuit, DAGBackend(basis))
        dag_circuit = dag_unroller.expand_gates()
        # if a coupling map is given compile to the map
        if coupling_map:
            logger.info("pre-mapping properties: %s",
                        dag_circuit.property_summary())
            # Insert swap gates
            coupling = Coupling(coupling_list2dict(coupling_map))
            logger.info("initial layout: %s", initial_layout)
            dag_circuit, final_layout = swap_mapper(
                dag_circuit, coupling, initial_layout, trials=20, seed=13)
            logger.info("final layout: %s", final_layout)
            # Expand swaps
            dag_unroller = DagUnroller(dag_circuit, DAGBackend(basis))
            dag_circuit = dag_unroller.expand_gates()
            # Change cx directions
            dag_circuit = direction_mapper(dag_circuit, coupling)
            # Simplify cx gates
            cx_cancellation(dag_circuit)
            # Simplify single qubit gates
            dag_circuit = optimize_1q_gates(dag_circuit)
            logger.info("post-mapping properties: %s",
                        dag_circuit.property_summary())

    # choose output format
    # TODO: do we need all of these formats, or just the dag?
    if format == 'dag':
        compiled_circuit = dag_circuit
    elif format == 'json':
        dag_unroller = DagUnroller(dag_circuit,
                                   JsonBackend(list(dag_circuit.basis.keys())))
        compiled_circuit = dag_unroller.execute()
    elif format == 'qasm':
        compiled_circuit = dag_circuit.qasm()
    else:
        raise QISKitTranspilerError('unrecognized circuit format')

    if get_layout:
        return compiled_circuit, final_layout
    return compiled_circuit
