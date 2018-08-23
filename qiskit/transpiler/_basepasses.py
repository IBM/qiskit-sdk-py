# -*- coding: utf-8 -*-

# Copyright 2018, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""This module implements the base pass."""

from abc import ABC, abstractmethod
from collections import OrderedDict


class BasePass(ABC):
    """Base class for transpiler passes."""

    requires = []  # List of passes that requires
    preserves = []  # List of passes that preserves

    @property
    def name(self):
        return self.__class__.__name__

    def __init__(self, *args, **kwargs):
        self._hash = hash(self.name + str(sorted(args)) + str(OrderedDict(kwargs)))
        self.idempotence = True
        self.ignore_requires = False
        self.ignore_preserves = False
        super().__init__()

    def __eq__(self, other):
        return self._hash == hash(other)

    def __hash__(self):
        return self._hash

    def set(self, idempotence=None,
            ignore_requires=None,
            ignore_preserves=None):
        """
        Sets a pass. `pass_.set(arg=value) equivalent to `pass_.arg = value`
        Args:
            idempotence (bool): Set idempotence for this pass.
            ignore_requires (bool): Set if the requires field should be ignored for this pass.
            ignore_preserves (bool): Set if the preserves field should be ignored for this pass
        """
        if idempotence is not None:
            self.idempotence = idempotence

        if ignore_requires is not None:
            self.ignore_requires = ignore_requires

        if ignore_preserves is not None:
            self.ignore_preserves = ignore_preserves

    @abstractmethod
    def run(self, dag, property_set=None):
        """
        Run a pass on the DAGCircuit. This is implemented by the pass developer.
        Args:
            dag:
            property_set:
        Raises:
            NotImplementedError
        """
        raise NotImplementedError


class AnalysisPass(BasePass):
    """ An analysis pass: change property set, not DAG. """
    pass


class TransformationPass(BasePass):
    """ A transformation pass: change DAG, not property set. """
    pass
