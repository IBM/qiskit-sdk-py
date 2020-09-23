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

r"""
A collection of functions that decide layout of figure.

Those functions are assigned to the `layout` key of the stylesheet.
User can change the layout of the output image by writing own function.
"""

from typing import List, Tuple
import numpy as np
from qiskit import circuit
from qiskit.visualization.exceptions import VisualizationError
from qiskit.visualization.timeline import types


def qreg_creg_ascending(bits: List[types.Bits]) -> List[types.Bits]:
    """Sort bits by ascending order.

    Bit order becomes Q0, Q1, ..., Cl0, Cl1, ...

    Args:
        bits: List of bits to sort.
    """
    qregs = []
    cregs = []

    for bit in bits:
        if isinstance(bit, circuit.Qubit):
            qregs.append(bit)
        elif isinstance(bit, circuit.Clbit):
            cregs.append(bit)
        else:
            VisualizationError('Unknown bit {bit} is provided.'.format(bit=bit))

    qregs = sorted(qregs, key=lambda x: x.index, reverse=False)
    cregs = sorted(cregs, key=lambda x: x.index, reverse=False)

    return qregs + cregs


def qreg_creg_descending(bits: List[types.Bits]) -> List[types.Bits]:
    """Sort bits by descending order.

    Bit order becomes Q_N, Q_N-1, ..., Cl_N, Cl_N-1, ...

    Args:
        bits: List of bits to sort.
    """
    qregs = []
    cregs = []

    for bit in bits:
        if isinstance(bit, circuit.Qubit):
            qregs.append(bit)
        elif isinstance(bit, circuit.Clbit):
            cregs.append(bit)
        else:
            VisualizationError('Unknown bit {bit} is provided.'.format(bit=bit))

    qregs = sorted(qregs, key=lambda x: x.index, reverse=True)
    cregs = sorted(cregs, key=lambda x: x.index, reverse=True)

    return qregs + cregs


def time_map_in_dt(time_window: Tuple[int, int]) -> types.HorizontalAxis:
    """Layout function for the horizontal axis formatting.

    Generate equispaced 6 horizontal axis ticks.

    Args:
        time_window: Left and right edge of this graph.

    Returns:
        Axis formatter object.
    """
    # shift time axis
    t0, t1 = time_window

    # axis label
    axis_loc = np.linspace(max(t0, 0), t1, 6)
    axis_label = axis_loc.copy()

    # consider time resolution
    label = 'System cycle time (dt)'

    formatted_label = ['{val:.0f}'.format(val=val) for val in axis_label]

    return types.HorizontalAxis(
        window=(t0, t1),
        axis_map=dict(zip(axis_loc, formatted_label)),
        label=label
    )
