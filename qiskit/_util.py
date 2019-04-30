# -*- coding: utf-8 -*-

# This code is part of Qiskit.
#
# (C) Copyright IBM 2017, 2019.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

# pylint: disable=wildcard-import,unused-wildcard-import

"""Compat shim for backwards compatability with qiskit.util."""

import warnings

from qiskit.util import *

warnings.warn('The qiskit._util module is deprecated and has been renamed '
              'qiskit.util. Please update your imports as qiskit._util will be'
              'removed in Qiskit Terra 0.9.', DeprecationWarning)
