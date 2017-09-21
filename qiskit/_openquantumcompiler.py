import qiskit.qasm as qasm
import qiskit.unroll as unroll
import qiskit.mapper as mapper

import pdb
import os
import sys


def compile(qasm_circuit, basis_gates='u1,u2,u3,cx,id', coupling_map=None,
            initial_layout=None, silent=True, get_layout=False):
    """Compile the circuit.

    This builds the internal "to execute" list which is list of quantum
    circuits to run on different backends.

    Args:
        qasm_circuit (str): qasm text to compile
        silent (bool): is an option to print out the compiling information
            or not
        basis_gates (str): a comma seperated string and are the base gates,
                           which by default are: u1,u2,u3,cx,id
        coupling_map (dict): A directed graph of coupling::

            {
             control(int):
                 [
                     target1(int),
                     target2(int),
                     , ...
                 ],
                 ...
            }

            eg. {0: [2], 1: [2], 3: [2]}

        initial_layout (dict): A mapping of qubit to qubit::

                              {
                                ("q", strart(int)): ("q", final(int)),
                                ...
                              }
                              eg.
                              {
                                ("q", 0): ("q", 0),
                                ("q", 1): ("q", 1),
                                ("q", 2): ("q", 2),
                                ("q", 3): ("q", 3)
                              }

    Returns:
        Compiled DAGCircuit.
    """
    compiled_dag_circuit = _unroller_code(qasm_circuit,
                                          basis_gates=basis_gates)
    final_layout = None
    # if a coupling map is given compile to the map
    if coupling_map:
        if not silent:
            print("pre-mapping properties: %s"
                  % compiled_dag_circuit.property_summary())
        # Insert swap gates
        coupling = mapper.Coupling(coupling_map)
        if not silent:
            print("initial layout: %s" % initial_layout)
        compiled_dag_circuit, final_layout = mapper.swap_mapper(
            compiled_dag_circuit, coupling, initial_layout, trials=20, verbose=False)
        if not silent:
            print("final layout: %s" % final_layout)
        # Expand swaps
        compiled_dag_circuit = _unroller_code(compiled_dag_circuit.qasm())
        # Change cx directions
        compiled_dag_circuit = mapper.direction_mapper(compiled_dag_circuit, coupling)
        # Simplify cx gates
        mapper.cx_cancellation(compiled_dag_circuit)
        # Simplify single qubit gates
        compiled_dag_circuit = mapper.optimize_1q_gates(compiled_dag_circuit)
        if not silent:
            print("post-mapping properties: %s"
                  % compiled_dag_circuit.property_summary())
    if get_layout:
        return compiled_dag_circuit, final_layout
    else:
        return compiled_dag_circuit


def _unroller_code(qasm_circuit, basis_gates=None):
    """ Unroll the code.

    Circuit is the circuit to unroll using the DAG representation.
    This is an internal function.

    Args:
        qasm_circuit: a circuit representation as qasm text.
        basis_gates (str): a comma seperated string and are the base gates,
                           which by default are: u1,u2,u3,cx,id
    Return:
        dag_ciruit (dag object): a dag representation of the circuit
                                 unrolled to basis gates
    """
    if not basis_gates:
        basis_gates = "u1,u2,u3,cx,id"  # QE target basis
    program_node_circuit = qasm.Qasm(data=qasm_circuit).parse()
    unroller_circuit = unroll.Unroller(program_node_circuit,
                                       unroll.DAGBackend(
                                           basis_gates.split(",")))
    dag_circuit_unrolled = unroller_circuit.execute()
    return dag_circuit_unrolled


def load_unroll_qasm_file(filename, basis_gates='u1,u2,u3,cx,id'):
    """Load qasm file and return unrolled circuit

    Args: 
        filename (str): a string for the filename including its location.
        basis_gates (str): basis to unroll circuit to.
    Returns:
        Returns a unrolled QuantumCircuit object
    """
    # create Program object Node (AST)
    program_node_circuit = qasm.Qasm(filename=filename).parse() 
    unrolled_circuit = unroll.Unroller(program_node_circuit,
                                       unroll.CircuitBackend(
                                           basis_gates.split(",")))
    circuit_unrolled = unrolled_circuit.execute()
    return circuit_unrolled


def dag2json(dag_circuit, basis_gates='u1,u2,u3,cx,id'):
    """Make a Json representation of the circuit.

    Takes a circuit dag and returns json circuit obj. This is an internal
    function.

    Args:
        dag_ciruit (dag object): a dag representation of the circuit.
        basis_gates (str): a comma seperated string and are the base gates,
                               which by default are: u1,u2,u3,cx,id

    Returns:
        the json version of the dag
    """
    # TODO: Jay: I think this needs to become a method like .qasm() for the DAG.
    try:
        circuit_string = dag_circuit.qasm(qeflag=True)
    except TypeError:
        circuit_string = dag_circuit.qasm()
    unroller = unroll.Unroller(qasm.Qasm(data=circuit_string).parse(),
                               unroll.JsonBackend(basis_gates.split(",")))
    json_circuit = unroller.execute()
    return json_circuit
