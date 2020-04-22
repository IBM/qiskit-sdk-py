# -*- coding: utf-8 -*-

# This code is part of Qiskit.
#
# (C) Copyright IBM 2017.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""The standard gates moved to qiskit/circuit/gates."""

import warnings
from qiskit.circuit.library.standard_gates.u1 import Cu1Gate

warnings.warn('This module is deprecated. The Cu1Gate can now be found in u1.py',
              category=DeprecationWarning, stacklevel=2)

__all__ = ['Cu1Gate']
