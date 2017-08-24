# -*- coding: utf-8 -*-

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

"""Contains functions used by the simulators.

Functions
    index2 -- Takes a bitstring k and inserts bits b1 as the i1th bit
    and b2 as the i2th bit

    enlarge_single_opt(opt, qubit, number_of_qubits) -- takes a single-qubit
    operator opt to a operator on n qubits

    enlarge_two_opt(opt, q0, q1, number_of_qubits) -- takes a two-qubit
    operator opt to a operator on n qubits

"""
import numpy as np


def index1(b, i, k):
    """Magic index1 function.

    Takes a bitstring k and inserts bit b as the ith bit,
    shifting bits >= i over to make room.
    """
    retval = k
    lowbits = k & ((1 << i) - 1)  # get the low i bits

    retval >>= i
    retval <<= 1

    retval |= b

    retval <<= i
    retval |= lowbits

    return retval


def index2(b1, i1, b2, i2, k):
    """Magic index1 function.

    Takes a bitstring k and inserts bits b1 as the i1th bit
    and b2 as the i2th bit
    """
    assert(i1 != i2)

    if i1 > i2:
        # insert as (i1-1)th bit, will be shifted left 1 by next line
        retval = index1(b1, i1-1, k)
        retval = index1(b2, i2, retval)
    else:  # i2>i1
        # insert as (i2-1)th bit, will be shifted left 1 by next line
        retval = index1(b2, i2-1, k)
        retval = index1(b1, i1, retval)
    return retval


def enlarge_single_opt(opt, qubit, number_of_qubits):
    """Enlarge single operator to n qubits.

    It is exponential in the number of qubits.

    Args:
        opt: the single-qubit opt.
        qubit: the qubit to apply it on counts from 0 and order
            is q_{n-1} ... otimes q_1 otimes q_0.
        number_of_qubits: the number of qubits in the system.
    """
    temp_1 = np.identity(2**(number_of_qubits-qubit-1), dtype=complex)
    temp_2 = np.identity(2**(qubit), dtype=complex)
    enlarge_opt = np.kron(temp_1, np.kron(opt, temp_2))
    return enlarge_opt


def enlarge_two_opt(opt, q0, q1, num):
    """Enlarge two-qubit operator to n qubits.

    It is exponential in the number of qubits.
    opt is the two-qubit gate
    q0 is the first qubit (control) counts from 0
    q1 is the second qubit (target)
    returns a complex numpy array
    number_of_qubits is the number of qubits in the system.
    """
    enlarge_opt = np.zeros([1 << (num), 1 << (num)])
    for i in range(1 << (num-2)):
        for j in range(2):
            for k in range(2):
                for jj in range(2):
                    for kk in range(2):
                        enlarge_opt[index2(j, q0, k, q1, i), index2(jj, q0, kk, q1, i)] = opt[j+2*k, jj+2*kk]
    return enlarge_opt


def single_gate_params(gate, params=None):
    """Apply a single-qubit gate to the qubit.

    Args:
        gate(str): the single-qubit gate name
        params(list): the operation parameters op['params']
    Returns:
        a tuple of U gate parameters (theta, phi, lam)
    """
    if gate == 'U' or gate == 'u3':
        return (params[0], params[1], params[2])
    elif gate == 'u2':
        return (np.pi/2, params[0], params[1])
    elif gate == 'u1':
        return (0., 0., params[0])
    elif gate == 'id':
        return (0., 0., 0.)


def single_gate_matrix(gate, params=None):
    """Get the matrix for a single qubit.

    Args:
        params(list): the operation parameters op['params']
    Returns:
        A numpy array representing the matrix
    """
    (theta, phi, lam) = single_gate_params(gate, params)
    return np.array([[np.cos(theta/2.0),
                      -np.exp(1j*lam)*np.sin(theta/2.0)],
                     [np.exp(1j*phi)*np.sin(theta/2.0),
                      np.exp(1j*phi+1j*lam)*np.cos(theta/2.0)]])
