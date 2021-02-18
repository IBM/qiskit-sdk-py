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

"""
Cities visualization
"""

import warnings

from qiskit.visualization.state_visualization import plot_state_city


def iplot_state_city(rho, figsize=None):
    """Create a cities representation.
    Graphical representation of the input array using a city style graph.
    Args:
        rho (Statevector or DensityMatrix or array): An N-qubit quantum state.
        figsize (tuple): The figure size in pixels.
    Returns:
        Figure: A matplotlib figure for the visualization
    Example:
        .. code-block::

            from qiskit import QuantumCircuit
            from qiskit.quantum_info import DensityMatrix
            from qiskit.visualization import iplot_state_city
            %matplotlib inline
            qc = QuantumCircuit(2)
            qc.h(0)
            qc.cx(0, 1)
            state = DensityMatrix.from_instruction(qc)
            iplot_state_city(state)
    """
    warnings.warn(
        "The iplot_state_city function is deprecated and will be "
        "removed in a future release. The hosted code this depended on no "
        "longer exists so this is falling back to use the matplotlib "
        "visualizations. qiskit.visualization.plot_state_city should be "
        "used directly moving forward.",
        DeprecationWarning,
        stacklevel=2,
    )
    fig = plot_state_city(rho, figsize=figsize)
    return fig
