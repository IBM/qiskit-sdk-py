# -*- coding: utf-8 -*-

# Copyright 2018, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""A module for monitoring backends."""

import time
import threading
import types
from IPython.display import display                              # pylint: disable=import-error
from IPython.core.magic import line_magic, Magics, magics_class  # pylint: disable=import-error
from IPython.core import magic_arguments                         # pylint: disable=import-error
import ipywidgets as widgets                                     # pylint: disable=import-error
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from qiskit import IBMQ


@magics_class
class BackendOverview(Magics):
    """A class of status magic functions.
    """
    @line_magic
    @magic_arguments.magic_arguments()
    @magic_arguments.argument(
        '-i',
        '--interval',
        type=float,
        default=60,
        help='Interval for status check.'
    )
    def qiskit_backend_overview(self, line='', cell=None):  # pylint: disable=W0613
        """A Jupyter magic function to monitor backends.
        """
        args = magic_arguments.parse_argstring(
            self.qiskit_backend_overview, line)

        unique_hardware_backends = get_unique_backends()
        _value = "<h2 style ='color:#ffffff; background-color:#000000;"
        _value += "padding-top: 1%; padding-bottom: 1%;padding-left: 1%;"
        _value += "margin-top: 0px'>Backend Overview</h2>"
        backend_title = widgets.HTML(value=_value,
                                     layout=widgets.Layout(margin='0px 0px 0px 0px'))

        build_back_widgets = [backend_widget(b)
                              for b in unique_hardware_backends]

        _backends = []
        # Sort backends by operational or not
        oper_ord_backends = []
        for n, back in enumerate(unique_hardware_backends):
            if back.status()['operational']:
                oper_ord_backends = [build_back_widgets[n]] + oper_ord_backends
                _backends = [back] + _backends
            else:
                oper_ord_backends = oper_ord_backends + [build_back_widgets[n]]
                _backends = _backends + [back]

        qubit_label = widgets.Label(value='Num. Qubits')
        pend_label = widgets.Label(value='Pending Jobs')
        least_label = widgets.Label(value='Least Busy')
        oper_label = widgets.Label(
            value='Operational', layout=widgets.Layout(margin='5px 0px 0px 0px'))
        t1_label = widgets.Label(
            value='Avg. T1', layout=widgets.Layout(margin='10px 0px 0px 0px'))
        t2_label = widgets.Label(
            value='Avg. T2', layout=widgets.Layout(margin='10px 0px 0px 0px'))

        labels_widget = widgets.VBox([qubit_label, pend_label, least_label,
                                      oper_label, t1_label, t2_label],
                                     layout=widgets.Layout(margin='295px 0px 0px 0px',
                                                           min_width='100px'))

        backend_grid = GridBox_with_thread(children=oper_ord_backends,
                                           layout=widgets.Layout(
                                               grid_template_columns='250px ' *
                                               len(unique_hardware_backends),
                                               grid_template_rows='auto',
                                               grid_gap='0px 25px'))

        backend_grid._backends = _backends        # pylint: disable=W0201
        backend_grid._update = types.MethodType(  # pylint: disable=W0201
            update_backend_info, backend_grid)

        backend_grid._thread = threading.Thread(  # pylint: disable=W0201
            target=backend_grid._update, args=(args.interval,))
        backend_grid._thread.start()

        back_box = widgets.HBox([labels_widget, backend_grid])

        back_monitor = widgets.VBox([backend_title, back_box])
        display(back_monitor)


class GridBox_with_thread(widgets.GridBox):  # pylint: disable=invalid-name
    """A GridBox that will close an attached thread
    """
    def __del__(self):
        """Object disposal"""
        if hasattr(self, '_thread'):
            try:
                self._thread.do_run = False
                self._thread.join()
            except Exception:  # pylint: disable=W0703
                pass
        self.close()


def get_unique_backends():
    """Gets the unique backends that are loaded
    """
    backends = IBMQ.backends()
    unique_hardware_backends = []
    unique_names = []
    for back in backends:
        if back.name() not in unique_names and not back.configuration()['simulator']:
            unique_hardware_backends.append(back)
            unique_names.append(back.name())
    return unique_hardware_backends


def backend_widget(backend):
    """Creates a backend widget.
    """
    config = backend.configuration()
    props = backend.properties()

    name = widgets.HTML(value="<h4>{name}</h4>".format(name=backend.name()),
                        layout=widgets.Layout())

    n_qubits = config['n_qubits']

    qubit_count = widgets.HTML(value="<h5><b>{qubits}</b></h5>".format(qubits=n_qubits),
                               layout=widgets.Layout(justify_content='center'))

    cmap = widgets.Output(layout=widgets.Layout(min_width='250px', max_width='250px',
                                                max_height='250px',
                                                min_height='250px',
                                                justify_content='center',
                                                align_items='center',
                                                margin='0px 0px 0px 0px'))

    with cmap:
        _cmap_fig = plot_coupling_map(backend,
                                      plot_directed=False,
                                      label_qubits=False)
        if _cmap_fig is not None:
            display(_cmap_fig)
            # Prevents plot from showing up twice.
            plt.close(_cmap_fig)

    pending = generate_jobs_pending_widget()

    is_oper = widgets.HTML(value="<h5></h5>",
                           layout=widgets.Layout(justify_content='center'))

    least_busy = widgets.HTML(value="<h5></h5>",
                              layout=widgets.Layout(justify_content='center'))

    t1_units = props['qubits'][0]['T1']['unit']
    avg_t1 = round(sum([q['T1']['value']
                        for q in props['qubits']])/n_qubits, 1)
    t1_widget = widgets.HTML(value="<h5>{t1} {units}</h5>".format(t1=avg_t1, units=t1_units),
                             layout=widgets.Layout())

    t2_units = props['qubits'][0]['T2']['unit']
    avg_t2 = round(sum([q['T2']['value']
                        for q in props['qubits']])/n_qubits, 1)
    t2_widget = widgets.HTML(value="<h5>{t2} {units}</h5>".format(t2=avg_t2, units=t2_units),
                             layout=widgets.Layout())

    out = widgets.VBox([name, cmap, qubit_count, pending,
                        least_busy, is_oper, t1_widget, t2_widget],
                       layout=widgets.Layout(display='inline-flex',
                                             flex_flow='column',
                                             align_items='center'))

    out._is_alive = True
    return out


def update_backend_info(self, interval=60):
    """Updates the monitor info
    Called from another thread.
    """
    my_thread = threading.currentThread()
    current_interval = 0
    started = False
    all_dead = False
    stati = [None]*len(self._backends)
    while getattr(my_thread, "do_run", True) and not all_dead:
        if current_interval == interval or started is False:
            for ind, back in enumerate(self._backends):
                _value = self.children[ind].children[2].value
                _head = _value.split('<b>')[0]
                try:
                    _status = back.status()
                    stati[ind] = _status
                except Exception:  # pylint: disable=W0703
                    self.children[ind].children[2].value = _value.replace(
                        _head, "<h5 style='color:#ff5c49'>")
                    self.children[ind]._is_alive = False
                else:
                    self.children[ind]._is_alive = True
                    self.children[ind].children[2].value = _value.replace(
                        _head, "<h5>")

            idx = list(range(len(self._backends)))
            pending = [s['pending_jobs'] for s in stati]

            least_pending = [list(x) for x in zip(
                *sorted(zip(pending, idx), key=lambda pair: pair[0]))]

            # Make sure least pending is operational
            for lst_pend in least_pending:
                if stati[lst_pend[1]]['operational']:
                    least_pending_idx = lst_pend[1]
                    break

            for var in idx:
                if var == least_pending_idx:
                    self.children[var].children[4].value = "<h5 style='color:#34bc6e'>True</h5>"
                else:
                    self.children[var].children[4].value = "<h5 style='color:#dc267f'>False</h5>"

                self.children[var].children[3].children[1].value = pending[var]
                self.children[var].children[3].children[1].max = max(
                    self.children[var].children[3].children[1].max, pending[var]+10)
                if stati[var]['operational']:
                    self.children[var].children[5].value = "<h5 style='color:#34bc6e'>True</h5>"
                else:
                    self.children[var].children[5].value = "<h5 style='color:#dc267f'>False</h5>"

            started = True
            current_interval = 0
        time.sleep(1)
        all_dead = not any([wid._is_alive for wid in self.children])
        current_interval += 1


def generate_jobs_pending_widget():
    """Generates a jobs_pending progress bar widget.
    """
    pbar = widgets.IntProgress(
        value=0,
        min=0,
        max=50,
        description='',
        orientation='horizontal', layout=widgets.Layout(max_width='180px'))
    pbar.style.bar_color = '#71cddd'

    pbar_current = widgets.Label(
        value=str(pbar.value), layout=widgets.Layout(min_width='auto'))
    pbar_max = widgets.Label(
        value=str(pbar.max), layout=widgets.Layout(min_width='auto'))

    def _on_max_change(change):
        pbar_max.value = str(change['new'])

    def _on_val_change(change):
        pbar_current.value = str(change['new'])

    pbar.observe(_on_max_change, names='max')
    pbar.observe(_on_val_change, names='value')

    jobs_widget = widgets.HBox([pbar_current, pbar, pbar_max],
                               layout=widgets.Layout(max_width='250px',
                                                     min_width='250px',
                                                     justify_content='center'))

    return jobs_widget


class _GraphDist():
    """Transform the circles properly for non-square axes.
    """
    def __init__(self, size, ax, x=True):
        self.size = size
        self.ax = ax  # pylint: disable=invalid-name
        self.x = x

    @property
    def dist_real(self):
        """Compute distance.
        """
        x0, y0 = self.ax.transAxes.transform(  # pylint: disable=invalid-name
            (0, 0))
        x1, y1 = self.ax.transAxes.transform(  # pylint: disable=invalid-name
            (1, 1))
        value = x1 - x0 if self.x else y1 - y0
        return value

    @property
    def dist_abs(self):
        """Distance abs
        """
        bounds = self.ax.get_xlim() if self.x else self.ax.get_ylim()
        return bounds[0] - bounds[1]

    @property
    def value(self):
        """Return value.
        """
        return (self.size / self.dist_real) * self.dist_abs

    def __mul__(self, obj):
        return self.value * obj


def plot_coupling_map(backend, figsize=None,
                      plot_directed=False,
                      label_qubits=True,
                      qubit_size=24,
                      line_width=4,
                      font_size=12,
                      qubit_color=None,
                      line_color=None,
                      font_color='w'):
    """Plots the coupling map of a device.

    Args:
        backend (BaseBackend): A backend instance,
        figsize (tuple): Output figure size (wxh) in inches.
        plot_directed (bool): Plot directed coupling map.
        label_qubits (bool): Label the qubits.
        qubit_size (float): Size of qubit marker.
        line_width (float): Width of lines.
        font_size (int): Font size of qubit labels.
        qubit_color (list): A list of colors for the qubits
        line_color (list): A list of colors for each line from coupling_map.
        font_color (str): The font color for the qubit labels.

    Returns:
        Figure: A Matplotlib figure instance.
    """
    mpl_data = {}

    mpl_data['ibmq_20_tokyo'] = [[0, 0], [0, 1], [0, 2], [0, 3], [0, 4],
                                 [1, 0], [1, 1], [1, 2], [1, 3], [1, 4],
                                 [2, 0], [2, 1], [2, 2], [2, 3], [2, 4],
                                 [3, 0], [3, 1], [3, 2], [3, 3], [3, 4]]

    mpl_data['ibmq_16_melbourne'] = [[0, 0], [0, 1], [0, 2], [0, 3], [0, 4],
                                     [0, 5], [0, 6], [1, 7], [1, 6], [1, 5],
                                     [1, 4], [1, 3], [1, 2], [1, 1]]

    mpl_data['ibmq_16_rueschlikon'] = [[1, 0], [0, 0], [0, 1], [0, 2], [0, 3],
                                       [0, 4], [0, 5], [0, 6], [0, 7], [1, 7],
                                       [1, 6], [1, 5], [1, 4], [1, 3], [1, 2], [1, 1]]

    mpl_data['ibmq_5_tenerife'] = [[1, 0], [0, 1], [1, 1], [1, 2], [2, 1]]

    mpl_data['ibmq_5_yorktown'] = mpl_data['ibmq_5_tenerife']

    config = backend.configuration()
    name = config['name']
    cmap = config['coupling_map']

    dep_names = {'ibmqx5': 'ibmq_16_rueschlikon',
                 'ibmqx4': 'ibmq_5_tenerife',
                 'ibmqx2': 'ibmq_5_yorktown'}

    if name in dep_names.keys():
        name = dep_names[name]

    if name in mpl_data.keys():
        grid_data = mpl_data[name]
    else:
        return None

    x_max = max([d[1] for d in grid_data])
    y_max = max([d[0] for d in grid_data])
    max_dim = max(x_max, y_max)

    if figsize is None:
        if x_max/max_dim > 0.33 and y_max/max_dim > 0.33:
            figsize = (5, 5)
        else:
            figsize = (9, 3)

    fig, ax = plt.subplots(figsize=figsize)  # pylint: disable=invalid-name
    ax.axis('off')
    fig.tight_layout()

    # set coloring
    if qubit_color is None:
        qubit_color = ['#648fff']*config['n_qubits']
    if line_color is None:
        line_color = ['#648fff']*len(cmap)

    # Add lines for couplings
    for ind, edge in enumerate(cmap):
        is_symmetric = False
        if edge[::-1] in cmap:
            is_symmetric = True
        y_start = grid_data[edge[0]][0]
        x_start = grid_data[edge[0]][1]
        y_end = grid_data[edge[1]][0]
        x_end = grid_data[edge[1]][1]

        if is_symmetric:
            if y_start == y_end:
                x_end = (x_end - x_start)/2+x_start

            elif x_start == x_end:
                y_end = (y_end - y_start)/2+y_start

            else:
                x_end = (x_end - x_start)/2+x_start
                y_end = (y_end - y_start)/2+y_start
        ax.add_artist(plt.Line2D([x_start, x_end], [-y_start, -y_end],
                                 color=line_color[ind], linewidth=line_width,
                                 zorder=0))
        if plot_directed:
            dx = x_end-x_start  # pylint: disable=invalid-name
            dy = y_end-y_start  # pylint: disable=invalid-name
            if is_symmetric:
                x_arrow = x_start+dx*0.95
                y_arrow = -y_start-dy*0.95
                dx_arrow = dx*0.01
                dy_arrow = -dy*0.01
                head_width = 0.15
            else:
                x_arrow = x_start+dx*0.5
                y_arrow = -y_start-dy*0.5
                dx_arrow = dx*0.2
                dy_arrow = -dy*0.2
                head_width = 0.2
            ax.add_patch(mpatches.FancyArrow(x_arrow,
                                             y_arrow,
                                             dx_arrow,
                                             dy_arrow,
                                             head_width=head_width,
                                             length_includes_head=True,
                                             edgecolor=None,
                                             linewidth=0,
                                             facecolor=line_color[ind],
                                             zorder=1))

    # Add circles for qubits
    for var, idx in enumerate(grid_data):
        _idx = [idx[1], -idx[0]]
        width = _GraphDist(qubit_size, ax, True)
        height = _GraphDist(qubit_size, ax, False)
        ax.add_artist(mpatches.Ellipse(
            _idx, width, height, color=qubit_color[var], zorder=1))
        if label_qubits:
            ax.text(*_idx, s=str(var),
                    horizontalalignment='center',
                    verticalalignment='center',
                    color=font_color, size=font_size, weight='bold')
    ax.set_xlim([-1, x_max+1])
    ax.set_ylim([-(y_max+1), 1])
    plt.close(fig)
    return fig
