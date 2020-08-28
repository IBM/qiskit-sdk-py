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

"""Chart axis generators.

A collection of functions that generate drawing object for input chart axis.
See py:mod:`qiskit.visualization.pulse_v2.types` for the detail of input data.

In this module input data is `ChartAxis`.

An end-user can write arbitrary functions that generate custom drawing objects.
Generators in this module are called with `formatter` and `device` kwargs.
These data provides stylesheet configuration and backend system configuration.

The format of generator is restricted to:

    ```python

    def my_object_generator(data: ChartAxis,
                            formatter: Dict[str, Any],
                            device: DrawerBackendInfo) -> List[ElementaryData]:
        pass
    ```

Arbitrary generator function satisfying above format can be accepted.
Returned `ElementaryData` can be arbitrary subclass that is implemented in plotter API.

"""
from typing import Dict, Any, List

from qiskit.visualization.pulse_v2 import drawing_objects, types, device_info


def gen_baseline(data: types.ChartAxis,
                 formatter: Dict[str, Any],
                 device: device_info.DrawerBackendInfo) \
        -> List[drawing_objects.LineData]:
    """Generate baseline associated with the chart.

    Stylesheets:
        - The `baseline` style is applied.

    Args:
        data: Chart axis data to draw.
        formatter: Dictionary of stylesheet settings.
        device: Backend configuration.

    Returns:
        List of `LineData` drawing objects.
    """
    style = {'alpha': formatter['alpha.baseline'],
             'zorder': formatter['layer.baseline'],
             'linewidth': formatter['line_width.baseline'],
             'linestyle': formatter['line_style.baseline'],
             'color': formatter['color.baseline']}

    baseline = drawing_objects.LineData(data_type=types.DrawingLine.BASELINE,
                                        channels=data.channel,
                                        x=[types.AbstractCoordinate.LEFT,
                                           types.AbstractCoordinate.RIGHT],
                                        y=[0, 0],
                                        ignore_scaling=True,
                                        styles=style)

    return [baseline]


def gen_chart_name(data: types.ChartAxis,
                   formatter: Dict[str, Any],
                   device: device_info.DrawerBackendInfo) \
        -> List[drawing_objects.TextData]:
    """Generate chart name.

    Stylesheets:
        - The `axis_label` style is applied.

    Args:
        data: Chart axis data to draw.
        formatter: Dictionary of stylesheet settings.
        device: Backend configuration.

    Returns:
        List of `TextData` drawing objects.
    """
    style = {'zorder': formatter['layer.axis_label'],
             'color': formatter['color.axis_label'],
             'size': formatter['text_size.axis_label'],
             'va': 'center',
             'ha': 'right'}

    text = drawing_objects.TextData(data_type=types.DrawingLabel.CH_NAME,
                                    channels=data.channel,
                                    x=types.AbstractCoordinate.LEFT,
                                    y=0,
                                    text=data.name,
                                    ignore_scaling=True,
                                    styles=style)

    return [text]
