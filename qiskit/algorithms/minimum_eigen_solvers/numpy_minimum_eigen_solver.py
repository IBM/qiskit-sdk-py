# This code is part of Qiskit.
#
# (C) Copyright IBM 2020.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""The Numpy Minimum Eigensolver algorithm."""

from typing import List, Optional, Union, Callable
import logging
import numpy as np

from qiskit.opflow import OperatorBase
from ..eigen_solvers.numpy_eigen_solver import NumPyEigensolver
from .minimum_eigen_solver import MinimumEigensolver, MinimumEigensolverResult

logger = logging.getLogger(__name__)


class NumPyMinimumEigensolver(MinimumEigensolver):
    """
    The Numpy Minimum Eigensolver algorithm.
    """

    def __init__(
        self,
        filter_criterion: Callable[
            [Union[List, np.ndarray], float, Optional[List[float]]], bool
        ] = None,
    ) -> None:
        """
        Args:
            filter_criterion: callable that allows to filter eigenvalues/eigenstates. The minimum
                eigensolver is only searching over feasible states and returns an eigenstate that
                has the smallest eigenvalue among feasible states. The callable has the signature
                `filter(eigenstate, eigenvalue, aux_values)` and must return a boolean to indicate
                whether to consider this value or not. If there is no
                feasible element, the result can even be empty.
        """
        self._ces = NumPyEigensolver(filter_criterion=filter_criterion)
        self._ret = MinimumEigensolverResult()

    @property
    def filter_criterion(
        self,
    ) -> Optional[Callable[[Union[List, np.ndarray], float, Optional[List[float]]], bool]]:
        """ returns the filter criterion if set """
        return self._ces.filter_criterion

    @filter_criterion.setter
    def filter_criterion(
        self,
        filter_criterion: Optional[
            Callable[[Union[List, np.ndarray], float, Optional[List[float]]], bool]
        ],
    ) -> None:
        """ set the filter criterion """
        self._ces.filter_criterion = filter_criterion

    @classmethod
    def supports_aux_operators(cls) -> bool:
        return NumPyEigensolver.supports_aux_operators()

    def compute_minimum_eigenvalue(
        self, operator: OperatorBase, aux_operators: Optional[List[Optional[OperatorBase]]] = None
    ) -> MinimumEigensolverResult:
        super().compute_minimum_eigenvalue(operator, aux_operators)
        result_ces = self._ces.compute_eigenvalues(operator, aux_operators)
        self._ret = MinimumEigensolverResult()
        if result_ces.eigenvalues is not None and len(result_ces.eigenvalues) > 0:
            self._ret.eigenvalue = result_ces.eigenvalues[0]
            self._ret.eigenstate = result_ces.eigenstates[0]
            if result_ces.aux_operator_eigenvalues:
                self._ret.aux_operator_eigenvalues = result_ces.aux_operator_eigenvalues[0]

        logger.debug("MinimumEigensolver:\n%s", self._ret)

        return self._ret
