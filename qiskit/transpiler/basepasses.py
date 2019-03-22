# -*- coding: utf-8 -*-

# Copyright 2018, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""This module implements the base pass."""

from abc import abstractmethod
from collections.abc import Hashable
from inspect import signature
from .propertyset import PropertySet


class MetaPass(type):
    """
    Enforces the creation of some fields in the pass
    while allowing passes to override __init__
    """

    def __call__(cls, *args, **kwargs):
        pass_instance = type.__call__(cls, *args, **kwargs)
        pass_instance._hash = hash(MetaPass._freeze_init_parameters(cls, args, kwargs))
        return pass_instance

    @staticmethod
    def _freeze_init_parameters(class_, args, kwargs):
        self_guard = object()
        init_signature = signature(class_.__init__)
        bound_signature = init_signature.bind(self_guard, *args, **kwargs)
        arguments = [('class_.__name__', class_.__name__)]
        for name, value in bound_signature.arguments.items():
            if value == self_guard:
                continue
            if isinstance(value, Hashable):
                arguments.append((name, type(value), value))
            else:
                arguments.append((name, type(value), repr(value)))
        return frozenset(arguments)


class BasePass(metaclass=MetaPass):
    """Base class for transpiler passes."""

    def __init__(self):
        self.requires = []  # List of passes that requires
        self.preserves = []  # List of passes that preserves
        self._hash = None

    def __hash__(self):
        return self._hash

    def __eq__(self, other):
        return hash(self) == hash(other)

    def name(self):
        """ The name of the pass. """
        return self.__class__.__name__

    @abstractmethod
    def run(self, dag, property_set):
        """
        Run a pass on the DAGCircuit. This is implemented by the pass developer.
        Args:
            dag (DAGCircuit): the dag on which the pass is run.
            property_set (PropertySet): the shared memory to communicate with other passes.
        Raises:
            NotImplementedError: when this is left unimplemented for a pass.
        """
        raise NotImplementedError

    @property
    def is_transformation_pass(self):
        """ If the pass is a TransformationPass, that means that the pass can manipulate the DAG,
        but cannot modify the property set (but it can be read). """
        return isinstance(self, TransformationPass)

    @property
    def is_analysis_pass(self):
        """ If the pass is an AnalysisPass, that means that the pass can analyze the DAG and write
        the results of that analysis in the property set. Modifications on the DAG are not allowed
        by this kind of pass. """
        return isinstance(self, AnalysisPass)


class AnalysisPass(BasePass):  # pylint: disable=abstract-method
    """ An analysis pass: change property set, not DAG. """
    pass


class TransformationPass(BasePass):  # pylint: disable=abstract-method
    """ A transformation pass: change DAG, not property set. """
    pass
