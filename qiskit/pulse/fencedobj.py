# -*- coding: utf-8 -*-

# This code is part of Qiskit.
#
# (C) Copyright IBM 2017, 2018.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Fenced objects are wraps for raising CompilerError when they are modified."""

from .exceptions import CompilerError


class FencedObject():
    """ Given an instance and a list of attributes to fence, raises a CompilerError when one
    of these attributes is accessed."""

    def __init__(self, instance, attributes_to_fence):
        self._wrapped = instance
        self._attributes_to_fence = attributes_to_fence

    def __getattribute__(self, name):
        object.__getattribute__(self, '_check_if_fenced')(name)
        return getattr(object.__getattribute__(self, '_wrapped'), name)

    def __getitem__(self, key):
        object.__getattribute__(self, '_check_if_fenced')('__getitem__')
        return object.__getattribute__(self, '_wrapped')[key]

    def __setitem__(self, key, value):
        object.__getattribute__(self, '_check_if_fenced')('__setitem__')
        object.__getattribute__(self, '_wrapped')[key] = value

    def _check_if_fenced(self, name):
        """
        Checks if the attribute name is in the list of attributes to protect. If so, raises
        TranspilerError.

        Args:
            name (string): the attribute name to check

        Raises:
            TranspilerError: when name is the list of attributes to protect.
        """
        if name in object.__getattribute__(self, '_attributes_to_fence'):
            raise CompilerError("The fenced %s has the property %s protected" %
                                (type(object.__getattribute__(self, '_wrapped')), name))
