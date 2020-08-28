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

"""Waveform generators.

A collection of functions that generate drawing object for input waveform type instructions.
See py:mod:`qiskit.visualization.pulse_v2.types` for the detail of input data.

In this module input data is `PulseInstruction`.

An end-user can write arbitrary functions that generate custom drawing objects.
Generators in this module are called with `formatter` and `device` kwargs.
These data provides stylesheet configuration and backend system configuration.

The format of generator is restricted to:

    ```python

    def my_object_generator(data: PulseInstruction,
                            formatter: Dict[str, Any],
                            device: DrawerBackendInfo) -> List[ElementaryData]:
        pass
    ```

Arbitrary generator function satisfying above format can be accepted.
Returned `ElementaryData` can be arbitrary subclass that is implemented in plotter API.
"""
import re
from fractions import Fraction
from typing import Dict, Any, List

import numpy as np

from qiskit import pulse
from qiskit.pulse import instructions
from qiskit.visualization.exceptions import VisualizationError
from qiskit.visualization.pulse_v2 import drawing_objects, types, device_info


def gen_filled_waveform_stepwise(data: types.PulseInstruction,
                                 formatter: Dict[str, Any],
                                 device: device_info.DrawerBackendInfo) \
        -> List[drawing_objects.FilledAreaData]:
    """Generate filled area object of waveform envelope.

    The curve of envelope is not interpolated and presented as stepwise function.

    Stylesheets:
        - The `fill_waveform` style is applied.

    Args:
        data: Waveform instruction data to draw.
        formatter: Dictionary of stylesheet settings.
        device: Backend configuration.

    Returns:
        List of `FilledAreaData` drawing objects.
    """
    fill_objs = []

    # generate waveform data
    parsed = _parse_waveform(data)
    channel = data.inst.channel
    resolution = formatter['general.vertical_resolution']

    # phase modulation
    if formatter['control.apply_phase_modulation']:
        ydata = np.asarray(parsed.yvals, dtype=np.complex) * np.exp(1j * data.frame.phase)
    else:
        ydata = np.asarray(parsed.yvals, dtype=np.complex)

    # stepwise interpolation
    xdata = np.concatenate((parsed.xvals, [parsed.xvals[-1] + 1]))
    ydata = np.repeat(ydata, 2)
    re_y = np.real(ydata)
    im_y = np.imag(ydata)
    time = np.concatenate(([xdata[0]], np.repeat(xdata[1:-1], 2), [xdata[-1]]))

    # setup style options
    style = {'alpha': formatter['alpha.fill_waveform'],
             'zorder': formatter['layer.fill_waveform'],
             'linewidth': formatter['line_width.fill_waveform'],
             'linestyle': formatter['line_style.fill_waveform']}

    color_code = types.ComplexColors(*formatter[_fill_waveform_color(channel)])

    # create real part
    if np.any(re_y):
        # data compression
        re_valid_inds = _find_consecutive_index(re_y, resolution)
        # stylesheet
        re_style = {'color': color_code.real}
        re_style.update(style)
        # metadata
        re_meta = {'data': 'real', 'qubit': device.get_qubit_index(channel) or 'N/A'}
        re_meta.update(parsed.meta)
        # active xy data
        re_xvals = time[re_valid_inds]
        re_yvals = re_y[re_valid_inds]

        # object
        real = drawing_objects.FilledAreaData(data_type=types.DrawingWaveform.REAL,
                                              channels=channel,
                                              x=re_xvals,
                                              y1=re_yvals,
                                              y2=np.zeros_like(re_xvals),
                                              meta=re_meta,
                                              styles=re_style)
        fill_objs.append(real)

    # create imaginary part
    if np.any(im_y):
        # data compression
        im_valid_inds = _find_consecutive_index(im_y, resolution)
        # stylesheet
        im_style = {'color': color_code.imaginary}
        im_style.update(style)
        # metadata
        im_meta = {'data': 'imag', 'qubit': device.get_qubit_index(channel) or 'N/A'}
        im_meta.update(parsed.meta)
        # active xy data
        im_xvals = time[im_valid_inds]
        im_yvals = im_y[im_valid_inds]

        # object
        imag = drawing_objects.FilledAreaData(data_type=types.DrawingWaveform.IMAG,
                                              channels=channel,
                                              x=im_xvals,
                                              y1=im_yvals,
                                              y2=np.zeros_like(im_xvals),
                                              meta=im_meta,
                                              styles=im_style)
        fill_objs.append(imag)

    return fill_objs


def gen_ibmq_latex_waveform_name(data: types.PulseInstruction,
                                 formatter: Dict[str, Any],
                                 device: device_info.DrawerBackendInfo) \
        -> List[drawing_objects.TextData]:
    """Generate formatted instruction name associated with the waveform.

    Channel name and id are removed and the rotation angle is expressed in units of pi.
    CR pulse name is also converted with the controlled rotation angle divided by 2.

    Note that in many scientific articles the controlled rotation angle implies
    the actual rotation angle, but in IQX backend the rotation angle represents
    the difference between rotation angles with different control qubit states.

    For example:
        - 'X90p_d0_abcdefg' is converted into 'X(\frac{\pi}{2})'
        - 'CR90p_u0_abcdefg` is converted into 'CR(\frac{\pi}{4})'

    Stylesheets:
        - The `annotate` style is applied.

    Notes:
        This generator can convert pulse names used in the IQX backends.
        If pulses are provided by the third party providers or the user defined,
        the generator output may be the as-is pulse name.

    Args:
        data: Waveform instruction data to draw.
        formatter: Dictionary of stylesheet settings.
        device: Backend configuration.

    Returns:
        List of `TextData` drawing objects.
    """
    style = {'zorder': formatter['layer.annotate'],
             'color': formatter['color.annotate'],
             'size': formatter['text_size.annotate'],
             'va': 'top',
             'ha': 'center'}

    if isinstance(data.inst, pulse.instructions.Acquire):
        systematic_name = 'Acquire'
        latex_name = None
    elif isinstance(data.inst.channel, pulse.channels.MeasureChannel):
        systematic_name = 'Measure'
        latex_name = None
    else:
        systematic_name = data.inst.pulse.name

        template = r'(?P<op>[A-Z]+)(?P<angle>[0-9]+)?(?P<sign>[pm])_(?P<ch>[dum])[0-9]+'
        match_result = re.match(template, systematic_name)
        if match_result is not None:
            match_dict = match_result.groupdict()
            sign = '' if match_dict['sign'] == 'p' else '-'
            if match_dict['op'] == 'CR':
                # cross resonance
                if match_dict['ch'] == 'u':
                    op_name = r'{\rm CR}'
                else:
                    op_name = r'\overline{\rm CR}'
                # IQX name def is not standard. Echo CR is annotated with pi/4 rather than pi/2
                angle_val = match_dict['angle']
                frac = Fraction(int(int(angle_val)/2), 180)
                if frac.numerator == 1:
                    angle = r'\frac{{\pi}}{{{}}}'.format(frac.denominator)
                else:
                    angle = r'\frac{{{}}}{{{}}}\pi'.format(frac.numerator, frac.denominator)
            else:
                # single qubit pulse
                op_name = r'{{\rm {}}}'.format(match_dict['op'])
                angle_val = match_dict['angle']
                if angle_val is None:
                    angle = r'\pi'
                else:
                    frac = Fraction(int(angle_val), 180)
                    if frac.numerator == 1:
                        angle = r'\frac{{\pi}}{{{}}}'.format(frac.denominator)
                    else:
                        angle = r'\frac{{{}}}{{{}}}\pi'.format(frac.numerator, frac.denominator)
            latex_name = r'{}({}{})'.format(op_name, sign, angle)
        else:
            latex_name = None

    text = drawing_objects.TextData(data_type=types.DrawingLabel.PULSE_NAME,
                                    channels=data.inst.channel,
                                    x=data.t0 + 0.5 * data.inst.duration,
                                    y=formatter['label_offset.pulse_name'],
                                    text=systematic_name,
                                    latex=latex_name,
                                    ignore_scaling=True,
                                    styles=style)

    return [text]


def _find_consecutive_index(data_array: np.ndarray, resolution: float) -> np.ndarray:
    """A helper function to return non-consecutive index from the given list.

    This drastically reduces memory footprint to represent a drawing object,
    especially for samples of very long flat-topped Gaussian pulses.
    Tiny value fluctuation smaller than `resolution` threshold is removed.

    Args:
        data_array: The array of numbers.
        resolution: Minimum resolution of sample values.

    Returns:
        The compressed data array.
    """
    try:
        vector = np.asarray(data_array, dtype=float)
        diff = np.diff(vector)
        diff[np.where(np.abs(diff) < resolution)] = 0
        # keep left and right edges
        consecutive_l = np.insert(diff.astype(bool), 0, True)
        consecutive_r = np.append(diff.astype(bool), True)
        return consecutive_l | consecutive_r

    except ValueError:
        return np.ones_like(data_array).astype(bool)


def _parse_waveform(data: types.PulseInstruction) -> types.ParsedInstruction:
    """A helper function that generates sample data array of the waveform with
    instruction meta data.

    Args:
        data: Instruction data set

    Raises:
        VisualizationError: When invalid instruction type is loaded.

    Returns:
        A data source to generate a drawing object.
    """
    inst = data.inst

    meta = dict()
    if isinstance(inst, instructions.Play):
        # pulse
        operand = inst.pulse
        if isinstance(operand, pulse.ParametricPulse):
            pulse_data = operand.get_waveform()
            meta.update(operand.parameters)
        else:
            pulse_data = operand
        xdata = np.arange(pulse_data.duration) + data.t0
        ydata = pulse_data.samples
    elif isinstance(inst, instructions.Delay):
        # delay
        xdata = np.arange(inst.duration) + data.t0
        ydata = np.zeros(inst.duration)
    elif isinstance(inst, instructions.Acquire):
        # acquire
        xdata = np.arange(inst.duration) + data.t0
        ydata = np.ones(inst.duration)
        acq_data = {'memory slot': inst.mem_slot.name,
                    'register slot': inst.reg_slot.name if inst.reg_slot else 'N/A',
                    'discriminator': inst.discriminator.name if inst.discriminator else 'N/A',
                    'kernel': inst.kernel.name if inst.kernel else 'N/A'}
        meta.update(acq_data)
    else:
        raise VisualizationError('Unsupported instruction {inst} by '
                                 'filled envelope.'.format(inst=inst.__class__.__name__))

    meta.update({'duration (cycle time)': inst.duration,
                 'duration (sec)': inst.duration * data.dt if data.dt else 'N/A',
                 't0 (cycle time)': data.t0,
                 't0 (sec)': data.t0 * data.dt if data.dt else 'N/A',
                 'phase': data.frame.phase,
                 'frequency': data.frame.freq,
                 'name': inst.name})

    return types.ParsedInstruction(xdata, ydata, meta)


def _fill_waveform_color(channel: pulse.channels.Channel) -> str:
    """A helper function that returns formatter key of the color code.

    Args:
        channel: Pulse channel object associated with the fill waveform.

    Raises:
        VisualizationError: When invalid channel is specified.

    Returns:
        A color code of real and imaginary part of the waveform.
    """
    if isinstance(channel, pulse.DriveChannel):
        return 'color.fill_waveform_d'

    if isinstance(channel, pulse.ControlChannel):
        return 'color.fill_waveform_u'

    if isinstance(channel, pulse.MeasureChannel):
        return 'color.fill_waveform_m'

    if isinstance(channel, pulse.AcquireChannel):
        return 'color.fill_waveform_a'

    if isinstance(channel, types.WaveformChannel):
        return 'color.fill_waveform_w'

    raise VisualizationError('Channel type %s is not supported.' % type(channel))
