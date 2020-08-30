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

# pylint: disable=invalid-name

"""
Core module of the pulse drawer.

This module provides the `DrawDataContainer` which is a collection of drawing objects
with additional information such as the modulation frequency and the time resolution.
In addition, this instance performs the simple data processing such as channel arrangement,
auto scaling of channels, and truncation of long pulses when a program is loaded.

This class may be initialized with backend instance which plays the schedule,
then a program is loaded and channel information is updated according to the preference:

    ```python
    ddc = DrawDataContainer(backend)
    ddc.load_program(sched)
    ddc.update_channel_property(visible_channels=[DriveChannel(0), DriveChannel(1)])
    ```

If the `DrawDataContainer` is initialized without backend information, the output shows
the time in units of system cycle time `dt` and the frequencies are initialized to zero.

This module is expected to be used by the pulse drawer interface and not exposed to users.

The `DrawDataContainer` takes a schedule of pulse waveform data and converts it into
a set of drawing objects, then a plotter interface takes the drawing objects
from the container to call the plotter's API. The visualization of drawing objects can be
customized with the stylesheet. The generated drawing objects can be accessed from

    ```python
    ddc.drawings
    ```

This module can be commonly used among different plotters. If the plotter supports
dynamic update of drawings, the channel data can be updated with new preference:

    ```python
    ddc.update_channel_property(visible_channels=[DriveChannel(0)])
    ```
In this example, `DriveChannel(1)` will be removed from the output.
"""

from functools import partial
from itertools import chain
from typing import Union, List, Tuple, Iterator, Optional
from copy import deepcopy
from collections import defaultdict

import numpy as np

from qiskit import pulse
from qiskit.visualization.exceptions import VisualizationError
from qiskit.visualization.pulse_v2 import events, types, drawing_objects, device_info
from qiskit.visualization.pulse_v2.stylesheet import QiskitPulseStyle


class DrawerCanvas:
    """Collection of `Chart` and configuration data.

    Pulse channels are associated with some `Chart` instance and
    drawing data object is stored in the `Chart` instance.

    Device, stylesheet, and some user generators are stored in the `DrawingCanvas`
    and the `Chart` instances are also attached to the `DrawerCanvas` as children.
    Global configurations are accessed by those children to modify appearance of `Chart` output.
    """

    def __init__(self,
                 stylesheet: QiskitPulseStyle,
                 device: device_info.DrawerBackendInfo):
        """Create new data container with backend system information.

        Args:
            stylesheet: Stylesheet to decide appearance of output image.
            device: Backend information to run the program.
        """
        # stylesheet
        self.formatter = stylesheet.formatter
        self.generator = stylesheet.generator
        self.layout = stylesheet.layout

        # device info
        self.device = device

        # chart
        self.charts = []

        # visible controls
        self.disable_chans = set()
        self.disable_types = set()

        # data scaling
        self.chan_scales = dict()

        # global time
        self._time_range = (0, 0)
        self._time_breaks = []

    @property
    def time_range(self):
        """Return current time range to draw."""
        return self._time_range

    @time_range.setter
    def time_range(self, new_range: Tuple[int, int]):
        """Update time range to draw and update child charts."""
        self._time_range = new_range
        for chart in self.charts:
            chart.update()

    @property
    def time_breaks(self):
        """Return time breaks with time range."""
        return self._time_breaks

    @time_breaks.setter
    def time_breaks(self, new_breaks: List[Tuple[int, int]]):
        """Set new time breaks."""
        self._time_breaks = sorted(new_breaks, key=lambda x: x[0])

    def load_program(self, program: Union[pulse.Waveform, pulse.ParametricPulse, pulse.Schedule]):
        """Load a program to draw.

        Args:
            program: `Waveform`, `ParametricPulse`, or `Schedule` to draw.

        Raises:
            VisualizationError: When input program is invalid data format.
        """
        if isinstance(program, pulse.Schedule):
            self._schedule_loader(program)
        elif isinstance(program, (pulse.Waveform, pulse.ParametricPulse)):
            self._waveform_loader(program)
        else:
            raise VisualizationError('Data type %s is not supported.' % type(program))

        # update time range
        self.set_time_range(0, program.duration)

    def _waveform_loader(self, program: Union[pulse.Waveform, pulse.ParametricPulse]):
        """Load Waveform instance.

        This function is sub-routine of py:method:`load_program`.

        Args:
            program: `Waveform` to draw.
        """
        chart = Chart(parent=self)

        # add waveform data
        fake_inst = pulse.Play(program, types.WaveformChannel())
        inst_data = types.PulseInstruction(t0=0,
                                           dt=self.device.dt,
                                           frame=types.PhaseFreqTuple(phase=0, freq=0),
                                           inst=fake_inst)
        for gen in self.generator['waveform']:
            obj_generator = partial(func=gen,
                                    formatter=self.formatter,
                                    device=self.device)
            for data in obj_generator(inst_data):
                chart.add_data(data)

        self.charts.append(chart)

    def _schedule_loader(self, program: pulse.Schedule):
        """Load Schedule instance.

        This function is sub-routine of py:method:`load_program`.

        Args:
            program: `Schedule` to draw.
        """
        # initialize scale values
        self.chan_scales = {chan: 1.0 for chan in program.channels}

        # create charts
        mapper = self.layout['chart_channel_map']
        for name, chans in mapper(channels=program.channels,
                                  formatter=self.formatter,
                                  device=self.device):
            chart = Chart(parent=self, name=name)

            # add standard pulse instructions
            for chan in chans:
                chart.load_program(program=program, chan=chan)

            # add barriers
            barrier_sched = program.filter(instruction_types=[pulse.instructions.RelativeBarrier],
                                           channels=chans)
            for t0, _ in barrier_sched.instructions:
                inst_data = types.BarrierInstruction(t0, self.device.dt, chans)
                for gen in self.generator['barrier']:
                    obj_generator = partial(func=gen,
                                            formatter=self.formatter,
                                            device=self.device)
                    for data in obj_generator(inst_data):
                        chart.add_data(data)

            self.charts.append(chart)

        # create snapshot chart
        snapshot_chart = Chart(parent=self, name='snapshot')

        snapshot_sched = program.filter(instruction_types=[pulse.instructions.Snapshot])
        for t0, inst in snapshot_sched.instructions:
            inst_data = types.SnapshotInstruction(t0, self.device.dt, inst.label, inst.channels)
            for gen in self.generator['snapshot']:
                obj_generator = partial(func=gen,
                                        formatter=self.formatter,
                                        device=self.device)
                for data in obj_generator(inst_data):
                    snapshot_chart.add_data(data)
        self.charts.append(snapshot_chart)

        # calculate axis break
        self.time_breaks = self._calculate_axis_break(program)

    def _calculate_axis_break(self, program: pulse.Schedule) -> List[Tuple[int, int]]:
        """A helper function to calculate axis break of long pulse sequence.

        Args:
            program: A schedule to calculate axis break.
        """
        axis_breaks = []

        edges = set()
        for t0, t1 in chain.from_iterable(program.timeslots.values()):
            if t1 - t0 > 0:
                edges.add(t0)
                edges.add(t1)
        edges = sorted(edges)

        for t0, t1 in zip(edges[:-1], edges[1:]):
            if t1 - t0 > self.formatter['axis_break.length']:
                t_l = t0 + 0.5 * self.formatter['axis_break.max_length']
                t_r = t1 - 0.5 * self.formatter['axis_break.max_length']
                axis_breaks.append((t_l, t_r))

        return axis_breaks

    def set_time_range(self,
                       t_start: Union[int, float],
                       t_end: Union[int, float],
                       seconds: bool = True):
        """Set time range to draw.

        All child chart instances are updated when time range is updated.

        Args:
            t_start: Left boundary of drawing in units of cycle time or real time.
            t_end: Right boundary of drawing in units of cycle time or real time.
            seconds: Set `True` if times are given in SI unit rather than dt.

        Raises:
            VisualizationError: When times are given in float without specifying dt.
        """
        # convert into nearest cycle time
        if seconds:
            if self.device.dt is not None:
                t_start = int(np.round(t_start / self.device.dt))
                t_end = int(np.round(t_end / self.device.dt))
            else:
                raise VisualizationError('Setting time range with SI units requires '
                                         'backend `dt` information.')
        self.time_range = (t_start, t_end)

    def set_disable_channel(self,
                            channel: pulse.channels.Channel,
                            remove: bool = True):
        """Interface method to control visibility of pulse channels.

        Specified object in the blocked list will not be shown.

        Args:
            channel: A pulse channel object to disable.
            remove: Set `True` to disable, set `False` to enable.
        """
        if remove:
            self.disable_chans.add(channel)
        else:
            self.disable_chans.discard(channel)

    def set_disable_type(self,
                         data_type: types.DataTypes,
                         remove: bool = True):
        """Interface method to control visibility of data types.

        Specified object in the blocked list will not be shown.

        Args:
            data_type: A drawing object data type to disable.
            remove: Set `True` to disable, set `False` to enable.
        """
        if remove:
            self.disable_types.add(data_type)
        else:
            self.disable_types.discard(data_type)


class Chart:
    """A collection of drawing object to be shown in the same line.

    Multiple pulse channels can be assigned to a single `Chart`.
    The parent `DrawerCanvas` should be specified to refer to the current user preference.

    The vertical value of each `Chart` should be in the range [-1, 1].
    This truncation should be performed in the plotter interface.
    """
    # unique index of chart
    chart_index = 0

    def __init__(self, parent: DrawerCanvas, name: Optional[str] = None):
        """Create new chart.

        Args:
            parent: `DrawerCanvas` that this `Chart` instance belongs to.
            name: Name of this `Chart` instance.
        """
        self._parent = parent

        self._waveform_collections = dict()
        self._misc_collections = dict()

        self._output_dataset = dict()

        self.index = self._cls_index()
        self.name = name or ''
        self.channels = set()

        self.vmax = 0
        self.vmin = 0
        self.scale = 1.0

        self._increment_cls_index()

    def add_data(self, data: drawing_objects.ElementaryData):
        """Add drawing object to collections.

        If the given object already exists in the collections,
        this interface replaces the old object instead of adding new entry.

        Args:
            data: New drawing object to add.
        """
        if isinstance(data.data_type, types.DrawingWaveform):
            self._waveform_collections[data.data_key] = data
        else:
            self._misc_collections[data.data_key] = data

    def load_program(self,
                     program: pulse.Schedule,
                     chan: pulse.channels.Channel):
        """Load pulse schedule.

        This method internally generates `ChannelEvents` to parse the program
        for the specified pulse channel. This method is called once

        Args:
            program: Pulse schedule to load.
            chan: A pulse channels associated with this instance.
        """
        chan_events = events.ChannelEvents.load_program(program, chan)
        chan_events.config(dt=self._parent.device.dt,
                           init_frequency=self._parent.device.get_channel_frequency(chan),
                           init_phase=0)

        # create objects associated with waveform
        waveforms = chan_events.get_waveforms()
        for gen in self._parent.generator['waveform']:
            obj_generator = partial(func=gen,
                                    formatter=self._parent.formatter,
                                    device=self._parent.device)
            drawings = [obj_generator(waveform) for waveform in waveforms]
            for data in list(chain.from_iterable(drawings)):
                self.add_data(data)

        # create objects associated with frame change
        frames = chan_events.get_frame_changes()
        for gen in self._parent.generator['frame']:
            obj_generator = partial(func=gen,
                                    formatter=self._parent.formatter,
                                    device=self._parent.device)
            drawings = [obj_generator(frame) for frame in frames]
            for data in list(chain.from_iterable(drawings)):
                self.add_data(data)

        self.channels.add(chan)

    def update(self):
        """Update vertical data range and scaling factor of this chart.

        Those parameters are updated based on current time range in the parent canvas.
        """
        self._output_dataset.clear()

        # assume no abstract coordinate in waveform data
        for key, data in self._waveform_collections.items():
            # truncate
            trunc_x, trunc_y = self._truncate_data(xvals=data.xvals,
                                                   yvals=data.yvals)
            # no available data points
            if trunc_x.size == 0 or trunc_y.size == 0:
                continue

            # update y range
            scale = min(self._parent.chan_scales.get(chan, 1.0) for chan in data.channels)
            self.vmax = max(scale * np.max(trunc_y),
                            self.vmax,
                            self._parent.formatter['channel_scaling.pos_spacing'])
            self.vmin = min(scale * np.min(trunc_y),
                            self.vmin,
                            self._parent.formatter['channel_scaling.neg_spacing'])

            # generate new data
            new_data = deepcopy(data)
            new_data.xvals = trunc_x
            new_data.yvals = trunc_y

            self._output_dataset[key] = new_data

        # calculate chart level scaling factor
        if self._parent.formatter['control.auto_chart_scaling']:
            self.scale = max(1.0 / (max(abs(self.vmax), abs(self.vmin))),
                             self._parent.formatter['general.max_scale'])
        else:
            self.scale = 1.0

        # regenerate chart axis objects, this may include updated scaling value
        chart_axis = types.ChartAxis(name=self.name, scale=self.scale, channels=self.channels)
        for gen in self._parent.generator['chart']:
            obj_generator = partial(func=gen,
                                    formatter=self._parent.formatter,
                                    device=self._parent.device)
            for data in obj_generator(chart_axis):
                self.add_data(data)

        # update other data
        for key, data in self._misc_collections.items():
            # truncate
            trunc_x, trunc_y = self._truncate_data(xvals=self._bind_coordinate(data.xvals),
                                                   yvals=self._bind_coordinate(data.yvals))
            # no available data points
            if trunc_x.size == 0 and trunc_y.size == 0:
                continue

            # generate new data
            new_data = deepcopy(data)
            new_data.xvals = trunc_x
            new_data.yvals = trunc_y

            self._output_dataset[key] = new_data

    @property
    def is_active(self):
        """Check if there is any active waveform data in this entry."""
        for data in self._output_dataset.values():
            if isinstance(data.data_type, types.DrawingWaveform) and self._check_visible(data):
                return True
        return False

    @property
    def collections(self) -> Iterator[Tuple[str, drawing_objects.ElementaryData]]:
        """Return currently active entries from drawing data collection.

        The object is returned with unique name as a key of an object handler.
        When the horizontal coordinate contains `AbstractCoordinate`,
        the value is substituted by current time range preference.
        """
        for name, data in self._output_dataset.items():
            # prepare unique name
            unique_id = 'chart{ind:d}_{key}'.format(ind=self.index, key=name)
            if self._check_visible(data):
                yield unique_id, data

    def _bind_coordinate(self, vals: Iterator[types.Coordinate]) -> np.ndarray:
        """A helper function to bind actual coordinate to `AbstractCoordinate`.

        Args:
            vals: Sequence of coordinate object associated with a drawing object.
        """
        def substitute(val: types.Coordinate):
            if val == types.AbstractCoordinate.LEFT:
                return self._parent.time_range[0]
            if val == types.AbstractCoordinate.RIGHT:
                return self._parent.time_range[1]
            if val == types.AbstractCoordinate.TOP:
                return self.vmax
            if val == types.AbstractCoordinate.BOTTOM:
                return self.vmin
            raise VisualizationError('Coordinate {name} is not supported.'.format(name=val))

        try:
            return np.asarray(vals, dtype=float)
        except ValueError:
            return np.asarray(list(map(substitute, vals)), dtype=float)

    def _truncate_data(self,
                       xvals: np.ndarray,
                       yvals: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """A helper function to remove data points according to time breaks.

        Args:
            xvals: Time points.
            yvals: Data points.
        """
        t0, t1 = self._parent.time_breaks
        time_breaks = [(-np.inf, t0)] + self._parent.time_breaks + [(t1, np.inf)]

        trunc_xvals = [xvals]
        trunc_yvals = [yvals]
        for t0, t1 in time_breaks:
            sub_xs = trunc_xvals.pop()
            sub_ys = trunc_yvals.pop()
            trunc_inds = np.where((sub_xs > t0) & (sub_xs < t1), True, False)
            # no overlap
            if not np.any(trunc_inds):
                trunc_xvals.append(sub_xs)
                trunc_yvals.append(sub_ys)
                continue
            # all data points are truncated
            if np.all(trunc_inds):
                return np.array([]), np.array([])

            # add left side
            ind_l = np.where(sub_xs < t0, True, False)
            if np.any(ind_l):
                trunc_xvals.append(np.append(sub_xs[ind_l], t0))
                trunc_yvals.append(np.append(sub_ys[ind_l], np.interp(t0, sub_xs, sub_ys)))

            # add right side
            ind_r = np.where(sub_xs > t1, True, False)
            if np.any(ind_r):
                trunc_xvals.append(np.insert(sub_xs[ind_r], 0, t1))
                trunc_yvals.append(np.insert(sub_ys[ind_r], 0, np.interp(t1, sub_xs, sub_ys)))

        return np.concatenate(trunc_xvals), np.concatenate(trunc_yvals)

    def _check_visible(self, data: drawing_objects.ElementaryData) -> bool:
        """A helper function to check if the data is visible.

        Args:
            data: Drawing object to test.
        """
        is_active_type = data.data_type in self._parent.disable_types
        is_active_chan = any(chan not in self._parent.disable_chans for chan in data.channels)
        if not (is_active_type and is_active_chan):
            return False

        return True

    @classmethod
    def _increment_cls_index(cls):
        """Increment counter of the chart."""
        cls.chart_index += 1

    @classmethod
    def _cls_index(cls):
        """Return counter index of the chart."""
        return cls.chart_index
