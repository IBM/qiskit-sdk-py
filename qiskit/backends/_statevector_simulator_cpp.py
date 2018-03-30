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
Interface to C++ quantum circuit simulator with realistic noise.
"""

import logging

from qiskit._result import Result
from ._qasm_simulator_cpp import QasmSimulatorCpp, run

logger = logging.getLogger(__name__)


class StatevectorSimulatorCpp(QasmSimulatorCpp):
    """C++ statevector simulator"""

    def __init__(self, configuration=None):
        super().__init__(configuration)
        self._configuration = configuration

        if not configuration:
            self._configuration = {
                'name': 'local_statevector_simulator_cpp',
                'url': 'https://github.com/QISKit/qiskit-sdk-py/src/cpp-simulator',
                'simulator': True,
                'local': True,
                'description': 'A C++ statevector simulator for qobj files',
                'coupling_map': 'all-to-all',
                "basis_gates": 'u1,u2,u3,cx,cz,id,x,y,z,h,s,sdg,t,tdg' +
                               'rzz,snapshot'
            }

    def run(self, q_job):
        """Run a QuantumJob on the the backend."""
        qobj = q_job.qobj
        final_state_key = 32767  # Key value for final state snapshot
        # Add final snapshots to circuits
        for circuit in qobj['circuits']:
            circuit['compiled_circuit']['operations'].append(
                {'name': 'snapshot', 'params': [final_state_key]})
        result = run(qobj, self._configuration['exe'])
        # Extract final state snapshot and move to 'quantum_state' data field
        for res in result['result']:
            snapshots = res['data']['snapshots']
            if str(final_state_key) in snapshots:
                final_state_key = str(final_state_key)
            # Pop off final snapshot added above
            final_state = snapshots.pop(final_state_key, None)
            final_state = final_state['quantum_state'][0]
            # Add final state to results data
            res['data']['quantum_state'] = final_state
            # Remove snapshot dict if empty
            if snapshots == {}:
                res['data'].pop('snapshots', None)
        return Result(result, qobj)
