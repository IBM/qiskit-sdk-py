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

"""Powell optimizer."""

from collections.abc import Sequence
from typing import Any, Dict, Optional, Union

from scipy.optimize import Bounds, minimize

from .optimizer import Optimizer, OptimizerSupportLevel


class ScipyMinimizer(Optimizer):
    """
    Optimizer using scipy.optimize.minimize.

    For further detail, please refer to
    See https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.minimize.html
    """

    def __init__(
        self,
        method: str,
        options: Optional[Dict[str, Any]] = None,
        max_evals_grouped: int = 1,
        **kwargs,
    ):
        """
        Args:
        """
        # pylint: disable=super-init-not-called
        self.method = method
        if method in {"L-BFGS-B", "TNC", "SLSQP", "Powell", "trust-constr"}:
            self._bounds_support_level = OptimizerSupportLevel.supported
        else:
            self._bounds_support_level = OptimizerSupportLevel.ignored

        if method in {
            "CG",
            "BFGS",
            "Newton-CG",
            "L-BFGS-B",
            "TNC",
            "SLSQP",
            "dogleg",
            "trust-ncg",
            "trust-krylov",
            "trust-exact",
            "trust-constr",
        }:
            self._gradient_support_level = OptimizerSupportLevel.supported
        else:
            self._gradient_support_level = OptimizerSupportLevel.ignored

        self._initial_point_support_level = OptimizerSupportLevel.required

        self.options = options
        self.max_evals_grouped = max_evals_grouped
        self._kwargs = kwargs

    def get_support_level(self):
        """ Return support level dictionary """
        return {
            "gradient": self._gradient_support_level,
            "bounds": self._bounds_support_level,
            "initial_point": self._initial_point_support_level,
        }

    def optimize(
        self,
        num_vars,
        objective_function,
        gradient_function=None,
        variable_bounds: Optional[Union[Sequence, Bounds]] = None,
        initial_point=None,
    ):
        self._validate_optimize_input(
            num_vars, gradient_function, variable_bounds, initial_point
        )

        res = minimize(
            fun=objective_function,
            x0=initial_point,
            method=self.method,
            jac=gradient_function,
            bounds=variable_bounds,
            options=self.options,
            **self._kwargs,
        )
        return res.x, res.fun, res.nfev
