# -*- coding: utf-8 -*-

# Copyright 2018, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""A module of magic functions"""

import time
import threading
import types
from IPython.display import display                              # pylint: disable=import-error
from IPython.core.magic import line_magic, Magics, magics_class  # pylint: disable=import-error
import ipywidgets as widgets                                     # pylint: disable=import-error
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from qiskit import IBMQ


@magics_class
class BackendMonitor(Magics):
    """A class of status magic functions.
    """
    @line_magic
    def qiskit_backend_monitor(self, line='', cell=None):
        """A Jupyter magic function to monitor backends.
        """
        unique_hardware_backends = get_unique_backends()
        backend_title = widgets.HTML(value="<h2 style='color: #ffffff; background-color:#000000;padding-top: 1%; padding-bottom: 1%;padding-left: 1%; margin-top: 0px'>Backend Monitor</h2>",
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
                                     layout=widgets.Layout(margin='300px 0px 0px 0px'))

        backend_grid = GridBox_with_thread(children=[labels_widget] + oper_ord_backends,
                                           layout=widgets.Layout(
                                               grid_template_columns='100px '+'250px ' * len(unique_hardware_backends),
                                               grid_template_rows='auto',
                                               grid_gap='0px 25px')
                                          )

        backend_grid._backends = _backends
        backend_grid._update = types.MethodType(update_backend_info, backend_grid)

        backend_grid._thread = threading.Thread(
            target=backend_grid._update, args=())
        backend_grid._thread.start()

        back_monitor = widgets.VBox([backend_title, backend_grid])
        display(back_monitor)


class GridBox_with_thread(widgets.GridBox):
    """A GridBox that will close an attached thread
    """
    def __del__(self):
        """Object disposal"""
        if hasattr(self, '_thread'):
            self._thread.do_run = False
            self._thread.join()
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
        if n_qubits == 20 or n_qubits == 5:
            _fig_size = (3.5, 3.5)
        else:
            _fig_size = (3.5, 1.5)
        _cmap_fig = plot_coupling_map(backend,
                                      figsize=_fig_size,
                                      plot_directed=False,
                                      label_qubits=False,
                                      )
        display(_cmap_fig)
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

    out = widgets.VBox([name, cmap, qubit_count, pending, least_busy, is_oper, t1_widget, t2_widget],
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
    while getattr(my_thread, "do_run", True):
        if current_interval == interval or started is False:
            stati = [b.status() for b in self._backends]
            idx = list(range(len(self._backends)))
            pending = [s['pending_jobs'] for s in stati]

            least_pending_idx = [list(x) for x in zip(
                *sorted(zip(pending, idx), key=lambda pair: pair[0]))][1][0]

            for kk in idx:
                if kk == least_pending_idx:
                    self.children[kk +
                                  1].children[4].value = "<h5 style='color:#34bc6e'>True</h5>"
                else:
                    self.children[kk +
                                  1].children[4].value = "<h5 style='color:#dc267f'>False</h5>"

                self.children[kk+1].children[3].children[1].value = pending[kk]
                self.children[kk+1].children[3].children[1].max = max(
                    self.children[kk+1].children[3].children[1].max, pending[kk]+10)
                if stati[kk]['operational']:
                    self.children[kk +
                                  1].children[5].value = "<h5 style='color:#34bc6e'>True</h5>"
                else:
                    self.children[kk +
                                  1].children[5].value = "<h5 style='color:#dc267f'>False</h5>"

            started = True
            current_interval = 0
        time.sleep(1)
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


def plot_coupling_map(backend, figsize=(5, 5),
                      plot_directed=True,
                      label_qubits=True,
                      font_size=None):
    """Plots the coupling map of a device.
    """
    mpl_data = {}

    mpl_data['ibmq_20_tokyo'] = [[0, 3], [1, 3], [2, 3], [3, 3], [4, 3],
                                 [0, 2], [1, 2], [2, 2], [3, 2], [4, 2],
                                 [0, 1], [1, 1], [2, 1], [3, 1], [4, 1],
                                 [0, 0], [1, 0], [2, 0], [3, 0], [4, 0]]

    mpl_data['ibmq_16_melbourne'] = [[0, 1], [1, 1], [2, 1], [3, 1], [4, 1],
                                     [5, 1], [6, 1], [7, 0], [6, 0], [5, 0],
                                     [4, 0], [3, 0], [2, 0], [1, 0]]

    mpl_data['ibmq_16_rueschlikon'] = [[0, 0], [0, 1], [1, 1], [2, 1], [3, 1],
                                       [4, 1], [5, 1], [6, 1], [
                                           7, 1], [7, 0], [6, 0],
                                       [5, 0], [4, 0], [3, 0], [2, 0], [1, 0],
                                       ]

    mpl_data['ibmq_5_tenerife'] = [[0, 0], [0, 2], [1, 1], [2, 2], [2, 0]]

    mpl_data['ibmq_5_yorktown'] = mpl_data['ibmq_5_tenerife']

    config = backend.configuration()
    name = config['name']
    cmap = config['coupling_map']

    dep_names = {'ibmqx5': 'ibmq_16_rueschlikon',
                 'ibmqx4': 'ibmq_5_tenerife',
                 'ibmqx2': 'ibmq_5_yorktown'}

    if name in dep_names.keys():
        name = dep_names[name]

    fig, ax = plt.subplots(figsize=figsize)
    ax.axis('off')
    fig.tight_layout()

    if name in mpl_data.keys():
        mpl_data = mpl_data[name]
    else:
        return fig

    x_max = max([d[0] for d in mpl_data])
    y_max = max([d[1] for d in mpl_data])

    max_dim = max(figsize)

    # Add lines for couplings

    for edge in cmap:
        is_directed = False
        if not edge[::-1] in cmap:
            is_directed = True
        x_start = mpl_data[edge[0]][0]
        y_start = mpl_data[edge[0]][1]
        x_end = mpl_data[edge[1]][0]
        y_end = mpl_data[edge[1]][1]
        ax.add_artist(plt.Line2D([x_start, x_end], [y_start, y_end],
                                 color='#648fff', linewidth=3,
                                 zorder=0))
        if is_directed and plot_directed:
            dx = x_end-x_start
            dy = y_end-y_start
            ax.add_patch(mpatches.FancyArrow(x_start+dx*0.5,
                                             y_start+dy*0.5,
                                             dx*0.2,
                                             dy*0.2,
                                             head_width=0.2,
                                             length_includes_head=True,
                                             edgecolor=None,
                                             linewidth=0,
                                             facecolor='#648fff',
                                             zorder=1))

    if font_size is None:
        font_size = 2*max_dim

    # Add circles for qubits
    for kk, idx in enumerate(mpl_data):
        ax.add_artist(plt.Circle(idx, 0.2, color='#648fff', zorder=1))
        #ax.add_artist(plt.Circle(idx, 0.1, color='1'))
        if label_qubits:
            ax.text(*idx, s=str(kk),
                    horizontalalignment='center',
                    verticalalignment='center',
                    color='#ffffff', size=font_size, weight='bold')

    ax.set_xlim([-1, x_max+1])
    ax.set_ylim([-1, y_max+1])
    ax.set_aspect('equal', adjustable='datalim')
    ax.axis('off')
    fig.tight_layout()
    return fig
