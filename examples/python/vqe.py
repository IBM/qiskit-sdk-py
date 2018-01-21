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

"""
Variational Quantum Eigensolver (VQE).
Generates many small circuits, thus good for profiling compiler overhead.
"""

import sys
import os
import numpy as np
from scipy import linalg as la
from functools import partial

# We don't know from where the user is running the example,
# so we need a relative position from this file path.
# TODO: Relative imports for intra-package imports are highly discouraged.
# http://stackoverflow.com/a/7506006
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from qiskit import QuantumProgram, QuantumCircuit
from qiskit import QuantumProgram
import Qconfig

# import optimization tools
from qiskit.tools.apps.optimization import trial_circuit_ryrz, SPSA_optimization, SPSA_calibration
from qiskit.tools.apps.optimization import Hamiltonian_from_file, make_Hamiltonian
from qiskit.tools.apps.optimization import eval_hamiltonian, group_paulis

# Ignore warnings due to chopping of small imaginary part of the energy 
import warnings
warnings.filterwarnings('ignore')

n=2
m=6
device='local_qiskit_simulator'

initial_theta=np.random.randn(2*n*m)
entangler_map={1: [0]} # the map of two-qubit gates with control at key and target at values
shots=1024
max_trials=100
ham_name=os.path.join(os.path.dirname(__file__),'H2/H2Equilibrium.txt')

# Exact Energy
pauli_list=Hamiltonian_from_file(ham_name)
H=make_Hamiltonian(pauli_list)
exact=np.amin(la.eig(H)[0]).real
print('The exact ground state energy is:')
print(exact)
pauli_list_grouped=group_paulis(pauli_list)

# Optimization
Q_program = QuantumProgram()
Q_program.set_api(Qconfig.APItoken,Qconfig.config["url"])
print (Q_program.get_backend_status(device))


def cost_function(Q_program,H,n,m,entangler_map,shots,device,theta):
    
    return eval_hamiltonian(Q_program,H,trial_circuit_ryrz(n,m,theta,entangler_map,None,False),shots,device).real

def optimize():
    initial_c=0.01
    target_update=2*np.pi*0.1
    save_step = 20
    
    if shots ==1:
        SPSA_params=SPSA_calibration(partial(cost_function,Q_program,H,n,m,entangler_map,
                                             shots,device),initial_theta,initial_c,target_update,25)
        output=SPSA_optimization(partial(cost_function,Q_program,H,n,m,entangler_map,shots,device),
                                 initial_theta,SPSA_params,max_trials,save_step,1);

    else:
        SPSA_params=SPSA_calibration(partial(cost_function,Q_program,pauli_list_grouped,n,m,entangler_map,
                                             shots,device),initial_theta,initial_c,target_update,25)
        output=SPSA_optimization(partial(cost_function,Q_program,pauli_list_grouped,n,m,entangler_map,shots,device),
                                 initial_theta,SPSA_params,max_trials,save_step,1);

optimize()
