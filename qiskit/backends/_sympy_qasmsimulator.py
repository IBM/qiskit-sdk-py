# -*- coding: utf-8 -*-
# pylint: disable=invalid-name

# Copyright 2017 IBM RESEARCH. All Rights Reserved.
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

"""Contains a (slow) python sympy-based simulator.

It simulates a qasm quantum circuit that has been compiled to run on the
simulator. It is exponential in the number of qubits.

We advise using the c++ simulator or online simulator for larger size systems.

The input is a qobj dictionary

and the output is a Results object

if shots = 1

    compiled_circuit['result']['data']['quantum_state']

and

    results['data']['classical_state']

where 'quantum_state' is a 2\ :sup:`n` complex numpy array representing the
quantum state vector and 'classical_state' is an integer representing
the state of the classical registors. Note the quantum state vector is in the symbolic form, e.g., E^(I*[pi])


if shots > 1

    results['data']["counts"] where this is dict {"0000" : 454}

The simulator is run using

.. code-block:: python

    QasmSimulator(compiled_circuit,shots,seed).run().

.. code-block:: guess

       compiled_circuit =
       {
        "header": {
        "number_of_qubits": 2, // int
        "number_of_clbits": 2, // int
        "qubit_labels": [["q", 0], ["v", 0]], // list[list[string, int]]
        "clbit_labels": [["c", 2]], // list[list[string, int]]
        }
        "operations": // list[map]
           [
               {
                   "name": , // required -- string
                   "params": , // optional -- list[double]
                   "qubits": , // required -- list[int]
                   "clbits": , // optional -- list[int]
                   "conditional":  // optional -- map
                       {
                           "type": , // string
                           "mask": , // hex string
                           "val":  , // bhex string
                       }
               },
           ]
       }

if shots = 1

.. code-block:: python

       result =
               {
               'data':
                   {
                   'quantum_state': array([ 1.+0.j,  0.+0.j,  0.+0.j,  0.+0.j]),
                   'classical_state': 0
                   'counts': {'0000': 1}
                   }
               'status': 'DONE'
               }

if shots > 1

.. code-block:: python

       result =
               {
               'data':
                   {
                   'counts': {'0000': 50, '1001': 44},
                   }
               'status': 'DONE'
               }




NOTE: Thanks to the lossless precision of sympy, the final amplitude vector, or the probability distribution, is precise.
We can directly sample from the probability distribution, rather than actually performing the multiple shots.
Besides, because the sympy computation is costly, we do only 1 shot even if multiple shots are specified.


"""
import uuid
import numpy as np
import random
from collections import Counter
import json
from ._simulatortools import single_gate_matrix
from ._simulatorerror import SimulatorError
from qiskit._result import Result
from qiskit.backends._basebackend import BaseBackend

from sympy.physics.quantum.qubit import Qubit
from sympy.physics.quantum.gate import H, X, Y, Z, S, T, CNOT, IdentityGate, OneQubitGate, UGate
from sympy.core.compatibility import is_sequence, u, unicode, range
from sympy.physics.quantum.qapply import qapply
from sympy.physics.quantum.represent import represent
from sympy import pprint, pretty, Matrix, Integer, I, pi, E, Pow, exp, log, Add, sqrt, Mul
from sympy.physics.quantum.qubit import IntQubit, matrix_to_qubit

from sympy.physics.quantum.qubit import measure_partial, qubit_to_matrix
from sympy import conjugate, N, re, im
from sympy.physics.quantum import TensorProduct

from sympy.physics.quantum.gate import u, H, X, Y, Z, S, T, CNOT, IdentityGate, OneQubitGate, TwoQubitGate, Gate, XGate, CGate, UGate
from sympy.physics.quantum.represent import represent

from sympy import pprint, pretty, symbols, Matrix, pi, E, I, cos, sin, N, exp, nsimplify



# TODO add ["status"] = 'DONE', 'ERROR' especitally for empty circuit error
# does not show up




class SympyQasmSimulator(BaseBackend):
    """Python implementation of a qasm simulator."""

    def __init__(self, configuration=None):
        """
        Args:
            configuration (dict): backend configuration
        """
        if configuration is None:
            self._configuration = {
                'name': 'local_sympy_qasm_simulator',
                'url': 'https://github.com/IBM/qiskit-sdk-py',
                'simulator': True,
                'local': True,
                'description': 'A python sympy-based simulator for qasm files',
                'coupling_map': 'all-to-all',
                'basis_gates': 'u1,u2,u3,cx,id'
            }
        else:
            self._configuration = configuration


    @staticmethod
    def _conjugate_square(com):
        return im(com)**2 + re(com)**2

    def _add_qasm_decision(self, qubit):
        """Apply the decision of measurement/reset qubit gate.

        qubit is the qubit that is measured/reset
        """
        probability_zero = 0
        random_number = random.random()
        vector_form = represent(self._quantum_state)
        for ii in range(1 << self._number_of_qubits):
            if ii & (1 << qubit) == 0:
                probability_zero += SympyQasmSimulator._conjugate_square(vector_form[ii,0]) # complex -> real!

        probability_zero_sym = nsimplify(probability_zero, tolerance=0.001) # guess the most close symbol form

        if random_number <= probability_zero: #
            outcome = '0'
            norm = sqrt(probability_zero_sym)
        else:
            outcome = '1'
            norm = sqrt(1-probability_zero_sym)
        return (outcome, norm)

    def _add_qasm_measure(self, qubit, cbit):
        """Apply the measurement qubit gate.

        qubit is the qubit measured.
        cbit is the classical bit the measurement is assigned to.
        """
        outcome, norm = self._add_qasm_decision(qubit)
        matrix_form = represent(self._quantum_state)

        for ii in range(1 << self._number_of_qubits):
            # update quantum state
            if (ii >> qubit) & 1 == int(outcome):
                matrix_form[ii,0] = matrix_form[ii,0]/norm #
            else:
                matrix_form[ii,0] = 0

        self._quantum_state = matrix_to_qubit(matrix_form)
        # update classical state
        bit = 1 << cbit
        self._classical_state = (self._classical_state & (~bit)) | (int(outcome) << cbit)

    def _add_qasm_reset(self, qubit):
        """Apply the reset to the qubit.

        This is done by doing a measruement and if 0 do nothing and
        if 1 flip the qubit.

        qubit is the qubit that is reset.
        """
        # TODO: slow, refactor later
        outcome, norm = self._add_qasm_decision(qubit)
        matrix_form_quantum_state = represent(self._quantum_state)
        matrix_form_temp = matrix_form_quantum_state[:,:]

        # self._quantum_state.fill(0.0)
        matrix_form_quantum_state = matrix_form_quantum_state - matrix_form_quantum_state

        # measurement
        for ii in range(1 << self._number_of_qubits):
            if (ii >> qubit) & 1 == int(outcome):
                matrix_form_temp[ii,0] = matrix_form_temp[ii,0]/norm
            else:
                matrix_form_temp[ii,0] = 0
        # reset
        if outcome == '1':
            for ii in range(1 << self._number_of_qubits):
                iip = (~ (1 << qubit)) & ii  # bit number qubit set to zero
                matrix_form_quantum_state[iip,0] += matrix_form_temp[ii,0]
        else:
            matrix_form_quantum_state = matrix_form_temp

        self._quantum_state = matrix_to_qubit(matrix_form_quantum_state)
        print(self._quantum_state)


    def run(self, q_job):
        """Run circuits in q_job"""
        # Generating a string id for the job
        job_id = str(uuid.uuid4())
        qobj = q_job.qobj
        result_list = []
        self._shots = qobj['config']['shots']
        for circuit in qobj['circuits']:
            result_list.append(self.run_circuit(circuit))
        return Result({'job_id': job_id, 'result': result_list, 'status': 'COMPLETED'},
                      qobj)

    def compute_distribution(self):
        matrix_form = represent(self._quantum_state)
        N = matrix_form.shape[0]
        list_form = [SympyQasmSimulator._conjugate_square(matrix_form[i,0]) for i in range(N)]
        return list_form



    #TODO:   5 test
    def run_circuit(self, circuit):
        """Run a circuit and return a single Result.

        Args:
            circuit (dict): JSON circuit from qobj circuits list

        Returns:
            A dictionary of results which looks something like::

                {
                "data":
                    {  #### DATA CAN BE A DIFFERENT DICTIONARY FOR EACH BACKEND ####
                    "counts": {’00000’: XXXX, ’00001’: XXXXX},
                    "time"  : xx.xxxxxxxx
                    },
                "status": --status (string)--
                }
        """
        ccircuit = circuit['compiled_circuit']
        self._number_of_qubits = ccircuit['header']['number_of_qubits']
        self._number_of_cbits = ccircuit['header']['number_of_clbits']
        self._quantum_state = 0
        self._classical_state = 0
        cl_reg_index = [] # starting bit index of classical register
        cl_reg_nbits = [] # number of bits in classical register
        cbit_index = 0
        for cl_reg in ccircuit['header']['clbit_labels']:
            cl_reg_nbits.append(cl_reg[1])
            cl_reg_index.append(cbit_index)
            cbit_index += cl_reg[1]
        if circuit['config']['seed'] is None:
            random.seed(random.getrandbits(32))
        else:
            random.seed(circuit['config']['seed'])

        outcomes = []
        for shot in range(self._shots):
            self._quantum_state = Qubit(*tuple([0]*self._number_of_qubits))
            self._classical_state = 0
            # Do each operation in this shot
            for operation in ccircuit['operations']:
                if 'conditional' in operation: # not related to sympy
                    mask = int(operation['conditional']['mask'], 16)
                    if mask > 0:
                        value = self._classical_state & mask
                        while (mask & 0x1) == 0:
                            mask >>= 1
                            value >>= 1
                        if value != int(operation['conditional']['val'], 16):
                            continue
                # Check if single  gate
                if operation['name'] in ['U', 'u1', 'u2', 'u3']:# get this done first
                    if 'params' in operation:
                        params = operation['params']
                    else:
                        params = None
                    qubit = operation['qubits'][0]
                    _sym_op = SympyQasmSimulator.get_sym_op(operation['name'].upper(), tuple([qubit]), operation['params'])
                    #print(represent(self._quantum_state))
                    #print(_sym_op)
                    self._quantum_state = qapply(_sym_op * self._quantum_state)
                    #print(represent(self._quantum_state))
                # Check if CX gate
                elif operation['name'] in ['id', 'u0']:
                    pass
                elif operation['name'] in ['CX', 'cx']:
                    qubit0 = operation['qubits'][0]
                    qubit1 = operation['qubits'][1]
                    _sym_op = SympyQasmSimulator.get_sym_op(operation['name'].upper(), tuple([qubit0, qubit1]), operation['params'])
                    self._quantum_state = qapply(_sym_op * self._quantum_state)
                # Check if measure
                elif operation['name'] == 'measure':#
                    qubit = operation['qubits'][0]
                    cbit = operation['clbits'][0]
                    self._add_qasm_measure(qubit, cbit)
                # Check if reset
                elif operation['name'] == 'reset': #
                    qubit = operation['qubits'][0]
                    self._add_qasm_reset(qubit)
                elif operation['name'] == 'barrier':
                    pass
                else:
                    backend = globals()['__configuration']['name']
                    err_msg = '{0} encountered unrecognized operation "{1}"'
                    raise SimulatorError(err_msg.format(backend,
                                                        operation['name']))

                    # Turn classical_state (int) into bit string
            outcomes.append(bin(self._classical_state)[2:].zfill(
                self._number_of_cbits))


        # Return the results
        counts = dict(Counter(outcomes))
        data = {'counts': self._format_result(
            counts, cl_reg_index, cl_reg_nbits)}

        if self._shots == 1:
            matrix_form = represent(self._quantum_state)
            N = matrix_form.shape[0]
            list_form = [matrix_form[i,0] for i in range(N)]

            data['quantum_state'] = np.asarray(list_form)# consistent with other backend. each element is symbolic!

            data['classical_state'] = self._classical_state, # integer, which can be converted to bin_string: "bin(x)"
        return {'data': data, 'status': 'DONE'}

    # array([ 0. +0.00000000e+00j,  0. +0.00000000e+00j,  1. -3.18258092e-15j,
    #     0. +0.00000000e+00j,  0. +0.00000000e+00j,  0. +0.00000000e+00j,
    #     0. +0.00000000e+00j,  0. +0.00000000e+00j])

    def _format_result(self, counts, cl_reg_index, cl_reg_nbits):
        """Format the result bit string.

        This formats the result bit strings such that spaces are inserted
        at register divisions.

        Args:
            counts : dictionary of counts e.g. {'1111': 1000, '0000':5}
        Returns:
            spaces inserted into dictionary keys at register boundries.
        """
        fcounts = {}
        for key, value in counts.items():
            new_key = [key[-cl_reg_nbits[0]:]]
            for index, nbits in zip(cl_reg_index[1:],
                                    cl_reg_nbits[1:]):
                new_key.insert(0, key[-(index+nbits):-index])
            fcounts[' '.join(new_key)] = value
        return fcounts

    # the following is the sympy implementations of various gates, including basic gates and ugates.
    @staticmethod
    def regulate(theta):
        error_margin = 0.01

        if abs(N(theta - pi)) < error_margin:
            return pi, True
        elif abs(N(theta - pi/2)) < error_margin:
            return pi/2, True
        elif abs(N(theta - pi/4)) < error_margin:
            return pi/4, True
        elif abs(N(theta- 2*pi)) < error_margin:
            return 2*pi, True
        else:
            return theta, theta == 0 # if theta ==0, we also think it is regular



    # extensible gate domain:
    class SDGGate(OneQubitGate):
        gate_name = u('SDG')
        def get_target_matrix(self, format='sympy'):
            return Matrix([[1, 0], [0, -I]])



    class TDGGate(OneQubitGate):
        gate_name = u('TDG')
        def get_target_matrix(self, format='sympy'):
            return Matrix([[1, 0], [0, exp(-I*pi/4)]])

    # follow the computation method in _simulatortools.py:
    # (theta, phi, lam) = single_gate_params(gate, params)
    # return np.array([[np.cos(theta/2.0),
    #                   -np.exp(1j*lam)*np.sin(theta/2.0)],
    #                  [np.exp(1j*phi)*np.sin(theta/2.0),
    #                   np.exp(1j*phi+1j*lam)*np.cos(theta/2.0)]])
    @staticmethod
    def compute_ugate_matrix(parafloatlist):
        theta = parafloatlist[0]
        phi = parafloatlist[1]
        lamb = parafloatlist[2]

        theta, theta_is_regular = SympyQasmSimulator.regulate(theta)
        phi, phi_is_regular = SympyQasmSimulator.regulate(phi)
        lamb, lamb_is_regular = SympyQasmSimulator.regulate(lamb)


        uMat = Matrix([[cos(theta/2), (-E**(I*lamb)) * sin(theta/2)],
                       [(E**(I*phi)) * sin(theta/2), (E**(I*(phi+lamb))) * cos(theta/2)]])

        if theta_is_regular and phi_is_regular and lamb_is_regular: # regular: we do not need concrete float value
            uMatNumeric = uMat
        else:
            uMatNumeric = uMat.evalf()
        return uMatNumeric

    @staticmethod
    def get_sym_op(name, qid_tuple, params=None):
        if name == 'ID':
            return IdentityGate(*qid_tuple) # de-tuple means unpacking
        elif name == 'X':
            return X(*qid_tuple)
        elif name == 'Y':
            return Y(*qid_tuple)
        elif name == 'Z':
            return Z(*qid_tuple)
        elif name == 'H':
            return H(*qid_tuple)
        elif name == 'S':
            return S(*qid_tuple)
        elif name == 'SDG':
            return SympyQasmSimulator.SDGGate(*qid_tuple)
        elif name == 'T':
            return T(*qid_tuple)
        elif name == 'TDG':
            return SympyQasmSimulator.TDGGate(*qid_tuple)
        elif name == 'CX' or name == 'CNOT':
            return CNOT(*qid_tuple)
        elif name == 'CY':
            return CGate(qid_tuple[0], Y(qid_tuple[1])) # qid_tuple: control target
        elif name == 'CZ':
            return CGate(qid_tuple[0], Z(qid_tuple[1])) # qid_tuple: control target
        elif name == 'CCX' or name == 'CCNOT' or name == 'TOFFOLI':
            return CGate((qid_tuple[0], qid_tuple[1]), X(qid_tuple[2])) # qid_tuple: control1, control2, target
        else: # U gate or CU gate
            if name.startswith('U') or name.startswith('CU'):
                parafloatlist = params

                if len(parafloatlist) == 1: # [theta=0, phi=0, lambda]
                    parafloatlist.insert(0, 0.0)
                    parafloatlist.insert(0, 0.0)
                elif len(parafloatlist) == 2: #[theta=pi/2, phi, lambda]
                    parafloatlist.insert(0, pi/2)
                elif len(parafloatlist) == 3: #[theta, phi, lambda]
                    pass
                else:
                    return NotImplemented

                uMat = SympyQasmSimulator.compute_ugate_matrix(parafloatlist)
                class UGatePeng(OneQubitGate):
                        gate_name = u('U')
                        def get_target_matrix(self, format='sympy'):
                            return uMat
                # the original UGate in sympy does not accept the matrix with numerical values
                if name.startswith('U'):
                    return UGatePeng(*qid_tuple) # the first arg of UGate should be a tuple of qubits to be applied to
                elif name.startswith('CU'): # additional treatment for CU1, CU2, CU3
                    return CGate(qid_tuple[0], UGatePeng(*qid_tuple[1:]))
            elif name == "MEASURE":
                return None # do nothing...
            else:
                raise Exception('Not supported')
