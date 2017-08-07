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
controlled-Y gate.
"""
from qiskit import QuantumCircuit
from qiskit import Gate
from qiskit import CompositeGate
from qiskit.extensions.standard import header


class CyGate(Gate):
    """controlled-Y gate."""

    def __init__(self, ctl, tgt, circ=None):
        """Create new CY gate."""
        super(CyGate, self).__init__("cy", [], [ctl, tgt], circ)

    def qasm(self):
        """Return OPENQASM string."""
        ctl = self.arg[0]
        tgt = self.arg[1]
        return self._qasmif("cy %s[%d],%s[%d];" % (ctl[0].name, ctl[1],
                                                   tgt[0].name, tgt[1]))

    def inverse(self):
        """Invert this gate."""
        return self  # self-inverse

    def reapply(self, circ):
        """Reapply this gate to corresponding qubits in circ."""
        self._modifiers(circ.cy(self.arg[0], self.arg[1]))


def cy(self, ctl, tgt):
    """Apply CY to circuit."""
    self._check_qubit(ctl)
    self._check_qubit(tgt)
    self._check_dups([ctl, tgt])
    return self._attach(CyGate(ctl, tgt, self))


QuantumCircuit.cy = cy
CompositeGate.cy = cy
