# -*- coding: utf-8 -*-

# This code is part of Qiskit.
#
# (C) Copyright IBM 2018, 2020.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Feature maps."""

from .n_local import NLocal
from .two_local import TwoLocal
from .ry import RY
from .ryrz import RYRZ
from .data_mapping import self_product
from .pauli_expansion import PauliExpansion
from .pauli_z_expansion import PauliZExpansion
from .first_order_expansion import FirstOrderExpansion
from .second_order_expansion import SecondOrderExpansion

__all__ = [
    'self_product',
    'PauliExpansion',
    'PauliZExpansion',
    'FirstOrderExpansion',
    'SecondOrderExpansion',
]
