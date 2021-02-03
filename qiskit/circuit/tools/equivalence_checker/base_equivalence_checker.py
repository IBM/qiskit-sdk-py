# This code is part of Qiskit.
#
# (C) Copyright IBM 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

from abc import ABC, abstractmethod
from inspect import signature
from time import time


class EquivalenceCheckerResult:
    """Model for Equivalence Checker Results.

    Attributes:
        success (bool): True if the equivalence check terminated without
            encountering an error.
        equivalent (bool): True if the circuits are equivalent, and False
            otherwise. Equals to None if `success` is False.
        error_msg (str): An error message, when failing to perform the
            check. Equals to None if `success` is True.
        time_taken (float): run time of the equivalence checker.
        Additional attributes can be added by the individual checkers.
    """
    
    def __init__(self, success, equivalent, error_msg):
        self.success = success
        self.equivalent = equivalent
        self.error_msg = error_msg

class BaseEquivalenceChecker(ABC):
    """Abstract circuit equivalence checker base class."""
    
    def __init__(self, name):
        self.name = name
    
    def run(self, circ1, circ2, **kwargs):
        """
        Check if the circuits are equivalent.

        Args:
            circ1, circ2 (QuantumCircuit): Circuits to check.

        Returns:
            EquivalenceCheckerResult: result of the equivalence check.
        """
        start = time()        
        res = self._run_checker(circ1, circ2, **kwargs)
        time_taken = time() - start
        res.time_taken = time_taken
        
        return res

    @abstractmethod
    def _run_checker(self, circ1, circ2, **kwargs):
        pass
