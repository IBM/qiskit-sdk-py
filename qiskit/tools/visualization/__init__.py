# -*- coding: utf-8 -*-

# Copyright 2018, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""Main Qiskit visualization methods."""

import sys
from qiskit._util import _has_connection
from ._circuit_visualization import circuit_drawer, plot_circuit, generate_latex_source,\
    latex_circuit_drawer, matplotlib_circuit_drawer, _text_circuit_drawer, qx_color_scheme
from ._error import VisualizationError
from ._state_visualization import plot_bloch_vector
from ._dag_visualization import dag_drawer

INTERACTIVE = False
if ('ipykernel' in sys.modules) and ('spyder' not in sys.modules):
    if _has_connection('https://qvisualization.mybluemix.net/', 443):
        INTERACTIVE = True


def plot_state(rho, method='city', filename=None, options=None, mode=None):
    """Plot a quantum state.

    This function provides several methods to plot a quantum state. There are
    two rendering backends either done in python using matplotlib or using js
    in a jupyter notebook using an externally hosted graphing library. To use
    the js you need to be running in jupyter and have network connectivity to
    the external server where the js library is hosted.

    Args:
        rho (ndarray): statevector or density matrix representation of a
            quantum state
        method (str): The plotting method to use. Valid choices are:
        - 'city': Plots the cityscape, two 3d bargraphs of the mixed state
                  rho) of the quantum state. This is the default.
        - 'paulivec': Plot the paulivec representation, a bar graph of the
                      mixed state rho over the pauli matrices, of a quantum
                      state
        - 'qsphere': Plot the qsphere representation of the quantum state
        - 'bloch':  Plot the bloch vector for each qubit in the quantum state
        - 'wigner': Plot the equal angle slice spin Wigner function of an
                    arbitrary quantum state.
        filename (str): If using the `mpl` mode save the output visualization
            as an image file to this path
        options (dict): An dict with options for visualization in `interactive`
            mode. The valid fields are:
            - width (int):  graph horizontal size, must be specified with
                height to have an effect
            - height (integer): graph vertical size, must be specified with
                width to have an effect
            - slider (bool): activate slider (only used for the `paulivec`
                method)

        mode (str): The visualization mode to use, either `mpl` or
            `interactive`. Interactive requires running in jupyter and external
            network connectivity to work. By default this will use `mpl` unless
            you are running in jupyter and you have external connectivity.
    Raises:
        VisualizationError: If invalid mode is specified
    """
    if not mode:
        if INTERACTIVE:
            from .interactive._iplot_state import iplot_state
            iplot_state(rho, method=method, options=options)
        else:
            from ._state_visualization import plot_state as plot
            plot(rho, method=method, filename=filename)
    else:
        if mode == 'interactive':
            from .interactive._iplot_state import iplot_state
            iplot_state(rho, method=method, options=options)
        elif mode == 'mpl':
            from ._state_visualization import plot_state as plot
            plot(rho, method=method, filename=filename)
        else:
            raise VisualizationError(
                "Invalid mode: %s, valid choices are 'interactive' or 'mpl'")


def plot_histogram(data, number_to_keep=None, legend=None, options=None,
                   filename=None, mode=None):
    """Plot a histogram of the measurement counts

    There are two rendering backends either done in python using matplotlib or
    using js in a jupyter notebook using an externally hosted graphing library.
    To use the js you need to be running in jupyter and have network
    connectivity to the external server where the js library is hosted.

    Args:
        data (list or dict): This is either a list of dictionaries or a
            single dictionary containing the values to represent (ex
            {'001': 139})
        number_to_keep (int): DEPRECATED the number of terms to plot and rest
            is made into a single bar called other values
        legend(list): A list of strings to use for labels of the data.
            The number of entries must match the length of data (if data is a
            list or 1 if it's a dict)
        filename (str): If using the `mpl` mode save the output visualization
            as an image file to this path
        options (dict): An dict with options for use for the visualization.
            Valid keys are:
            - width (integer): graph horizontal size, must be specified with
              height to have an effect
            - height (integer): graph vertical size, must be specified with
              width to have an effect
            - number_to_keep (integer): groups max values
            - show_legend (bool): show legend of graph content
            - sort (string): Could be 'asc' or 'desc'
            - slider (bool): activate slider (`interactive` mode only)

        mode (str): The visualization mode to use, either `mpl` or
            `interactive`. Interactive requires running in jupyter and external
            network connectivity to work. By default this will use `mpl` unless
            you are running in jupyter and you have external connectivity.
    Raises:
        VisualizationError: If invalid mode is specified
    """

    if not mode:
        if INTERACTIVE:
            from .interactive._iplot_histogram import iplot_histogram
            iplot_histogram(data, number_to_keep=number_to_keep, legend=legend,
                            options=options)
        else:
            from ._counts_visualization import plot_histogram as plot
            plot(data, number_to_keep=number_to_keep, legend=legend,
                 options=options)
    else:
        if mode == 'interactive':
            from .interactive._iplot_histogram import iplot_histogram
            iplot_histogram(data, number_to_keep=number_to_keep, legend=legend,
                            options=options)
        elif mode == 'mpl':
            from ._counts_visualization import plot_histogram as plot
            plot(data, number_to_keep=number_to_keep, legend=legend,
                 options=options, filename=filename)
        else:
            raise VisualizationError(
                "Invalid mode: %s, valid choices are 'interactive' or 'mpl'")
