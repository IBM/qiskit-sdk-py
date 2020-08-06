# -*- coding: utf-8 -*-

# This code is part of Qiskit.
#
# (C) Copyright IBM 2017, 2020.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""
Symplectic Operators
"""

from qiskit._unittester import UnitTester

from .pauli_table import PauliTable
from .pauli_utils import pauli_basis
from .stabilizer_table import StabilizerTable
from .clifford import Clifford
from .sparse_pauli_op import SparsePauliOp

RUN_TESTS = UnitTester(__name__)
del UnitTester
