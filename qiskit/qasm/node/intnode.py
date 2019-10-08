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

"""Node for an OPENQASM integer."""

import warnings
from sympy import N

from .node import Node


class Int(Node):
    """Node for an OPENQASM integer.

    This node has no children. The data is in the value field.
    """

    def __init__(self, id):
        """Create the integer node."""
        # pylint: disable=redefined-builtin
        super().__init__("int", None, None)
        self.value = id

    def to_string(self, indent):
        """Print with indent."""
        ind = indent * ' '
        print(ind, 'int', self.value)

    def qasm(self, prec=None):
        """Return the corresponding OPENQASM string."""

        if prec is not None:
            warnings.warn('Parameter \'prec\' is no longer used and is being deprecated.',
                          DeprecationWarning)

        return "%d" % self.value

    def latex(self, prec=None, nested_scope=None):
        """Return the corresponding math mode latex string."""

        if prec is not None:
            warnings.warn('Parameter \'prec\' is no longer used and is being deprecated.',
                          DeprecationWarning)
        if nested_scope is not None:
            warnings.warn('Parameter \'nested_scope\' is no longer used and is being deprecated.',
                          DeprecationWarning)

        return "%d" % self.value

    def sym(self, nested_scope=None):
        """Return the correspond symbolic number."""

        if nested_scope is not None:
            warnings.warn('Parameter \'nested_scope\' is no longer used and is being deprecated.',
                          DeprecationWarning)

        return N(self.value)

    def real(self, nested_scope=None):
        """Return the correspond floating point number."""

        if nested_scope is not None:
            warnings.warn('Parameter \'nested_scope\' is no longer used and is being deprecated.',
                          DeprecationWarning)

        return float(self.value)
