# -*- coding: utf-8 -*-

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

"""Snapshot generators.

A collection of functions that generate drawing object for input snapshot type instructions.
See py:mod:`qiskit.visualization.pulse_v2.types` for the detail of input data.

In this module input data is `SnapshotInstruction`.

An end-user can write arbitrary functions that generate custom drawing objects.
Generators in this module are called with `formatter` and `device` kwargs.
These data provides stylesheet configuration and backend system configuration.

The format of generator is restricted to:

    ```python

    def my_object_generator(data: SnapshotInstruction,
                            formatter: Dict[str, Any],
                            device: DrawerBackendInfo) -> List[ElementaryData]:
        pass
    ```

Arbitrary generator function satisfying above format can be accepted.
Returned `ElementaryData` can be arbitrary subclass that is implemented in plotter API.

"""
from typing import Dict, Any, List

from qiskit.visualization.pulse_v2 import drawing_objects, types, device_info


def gen_snapshot_name(data: types.SnapshotInstruction,
                      formatter: Dict[str, Any],
                      device: device_info.DrawerBackendInfo) \
        -> List[drawing_objects.TextData]:
    """Generate a snapshot name labels.

    Stylesheets:
        - The `snapshot` style is applied for snapshot symbol.
        - The `annotate` style is applied for label font size.

    Args:
        data: Snapshot instruction data to draw.
        formatter: Dictionary of stylesheet settings.
        device: Backend configuration.

    Returns:
        List of `TextData` drawing objects.
    """
    style = {'zorder': formatter['layer.snapshot'],
             'color': formatter['color.snapshot'],
             'size': formatter['text_size.annotate'],
             'va': 'bottom',
             'ha': 'center'}

    text = drawing_objects.TextData(data_type=types.DrawingLabel.SNAPSHOT,
                                    channels=data.inst.channel,
                                    xvals=[data.t0],
                                    yvals=[formatter['label_offset.snapshot']],
                                    text=data.inst.name,
                                    ignore_scaling=True,
                                    styles=style)

    return [text]


def gen_snapshot_symbol(data: types.SnapshotInstruction,
                        formatter: Dict[str, Any],
                        device: device_info.DrawerBackendInfo) \
        -> List[drawing_objects.TextData]:
    """Generate a snapshot symbol with instruction meta data from provided snapshot instruction.

    Stylesheets:
        - The `snapshot` style is applied for snapshot symbol.
        - The symbol type in unicode is specified in `formatter.unicode_symbol.snapshot`.
        - The symbol type in latex is specified in `formatter.latex_symbol.snapshot`.

    Args:
        data: Snapshot instruction data to draw.
        formatter: Dictionary of stylesheet settings.
        device: Backend configuration.

    Returns:
        List of `TextData` drawing objects.
    """
    style = {'zorder': formatter['layer.snapshot'],
             'color': formatter['color.snapshot'],
             'size': formatter['text_size.snapshot'],
             'va': 'bottom',
             'ha': 'center'}

    meta = {'snapshot type': data.inst.type,
            't0 (cycle time)': data.t0,
            't0 (sec)': data.t0 * data.dt if data.dt else 'N/A',
            'name': data.inst.name,
            'label': data.inst.label}

    text = drawing_objects.TextData(data_type=types.DrawingSymbol.SNAPSHOT,
                                    channels=data.inst.channel,
                                    xvals=[data.t0],
                                    yvals=[0],
                                    text=formatter['unicode_symbol.snapshot'],
                                    latex=formatter['latex_symbol.snapshot'],
                                    ignore_scaling=True,
                                    meta=meta,
                                    styles=style)

    return [text]
