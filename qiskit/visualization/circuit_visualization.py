# -*- coding: utf-8 -*-

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
Module for the primary interface to the circuit drawers.

This module contains the end user facing API for drawing quantum circuits.
There are 3 available drawer backends available:

 0. Ascii art
 1. LaTeX
 2. Matplotlib

This provides a single function entrypoint to drawing a circuit object with
any of the backends.
"""

import errno
import logging
import os
import subprocess
import tempfile
from warnings import warn

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from qiskit import user_config
from qiskit.visualization import exceptions
from qiskit.visualization import latex as _latex
from qiskit.visualization import text as _text
from qiskit.visualization import utils
from qiskit.visualization import matplotlib as _matplotlib

logger = logging.getLogger(__name__)


def circuit_drawer(circuit,
                   scale=0.7,
                   filename=None,
                   style=None,
                   output=None,
                   interactive=False,
                   line_length=None,
                   plot_barriers=True,
                   reverse_bits=False,
                   justify=None,
                   vertical_compression='medium',
                   idle_wires=True,
                   with_layout=True,
                   fold=None,
                   ax=None,
                   initial_value=False):
    """Draw a quantum circuit to different formats (set by output parameter):

    **text**: ASCII art TextDrawing that can be printed in the console.

    **latex**: high-quality images compiled via latex.

    **latex_source**: raw uncompiled latex output.

    **matplotlib**: images with color rendered purely in Python.

    Args:
        circuit (QuantumCircuit): the quantum circuit to draw
        scale (float): scale of image to draw (shrink if < 1)
        filename (str): file path to save image to
        style (dict or str): dictionary of style or file name of style file.
            This option is only used by the ``mpl`` output type. If a str is
            passed in that is the path to a json file which contains that will
            be open, parsed, and then used just as the input dict. See:
            :ref:`Style Dict Doc <style-dict-doc>` for more information on the
            contents.
        output (str): Select the output method to use for drawing the circuit.
            Valid choices are ``text``, ``latex``, ``latex_source``, ``mpl``.
            By default the `'text`' drawer is used unless a user config file
            has an alternative backend set as the default. If the output kwarg
            is set, that backend will always be used over the default in a user
            config file.
        interactive (bool): when set true show the circuit in a new window
            (for `mpl` this depends on the matplotlib backend being used
            supporting this). Note when used with either the `text` or the
            `latex_source` output type this has no effect and will be silently
            ignored.
        line_length (int): Deprecated, see `fold` which supersedes this option.
            Sets the length of the lines generated by `text` output type.
            This useful when the drawing does not fit in the console. If None
            (default), it will try to guess the console width using
            ``shutil.get_terminal_size()``. However, if you're running in
            jupyter the default line length is set to 80 characters. If you
            don't want pagination at all, set ``line_length=-1``.
        reverse_bits (bool): When set to True reverse the bit order inside
            registers for the output visualization.
        plot_barriers (bool): Enable/disable drawing barriers in the output
            circuit. Defaults to True.
        justify (string): Options are ``left``, ``right`` or ``none``, if
            anything else is supplied it defaults to left justified. It refers
            to where gates should be placed in the output circuit if there is
            an option. ``none`` results in each gate being placed in its own
            column.
        vertical_compression (string): ``high``, ``medium`` or ``low``. It
            merges the lines generated by the ``text`` output so the drawing
            will take less vertical room.  Default is ``medium``. Only used by
            the ``text`` output, will be silently ignored otherwise.
        idle_wires (bool): Include idle wires (wires with no circuit elements)
            in output visualization. Default is True.
        with_layout (bool): Include layout information, with labels on the
            physical layout. Default is True.
        fold (int): Sets pagination. It can be disabled using -1.
            In `text`, sets the length of the lines. This useful when the
            drawing does not fit in the console. If None (default), it will try
            to guess the console width using ``shutil.get_terminal_size()``.
            However, if running in jupyter, the default line length is set to
            80 characters. In ``mpl`` it is the number of (visual) layers before
            folding. Default is 25.
        ax (matplotlib.axes.Axes): An optional Axes object to be used for
            the visualization output. If none is specified a new matplotlib
            Figure will be created and used. Additionally, if specified there
            will be no returned Figure since it is redundant. This is only used
            when the ``output`` kwarg is set to use the ``mpl`` backend. It
            will be silently ignored with all other outputs.
        initial_value (bool): Optional. Adds |0> in the beginning of the line.
            Only used by the ``text``, ``latex`` and ``latex_source`` outputs.
            Default: ``False``.
    Returns:
        :class:`PIL.Image` or :class:`matplotlib.figure` or :class:`str` or
        :class:`TextDrawing`:

        * `PIL.Image` (output='latex')
            an in-memory representation of the image of the circuit diagram.
        * `matplotlib.figure.Figure` (output='mpl')
            a matplotlib figure object for the circuit diagram.
        * `str` (output='latex_source')
            The LaTeX source code for visualizing the circuit diagram.
        * `TextDrawing` (output='text')
            A drawing that can be printed as ascii art

    Raises:
        VisualizationError: when an invalid output method is selected
        ImportError: when the output methods requires non-installed libraries.

    .. _style-dict-doc:

    **Style Dict Details**

    The style dict kwarg contains numerous options that define the style of the
    output circuit visualization. The style dict is only used by the ``mpl``
    output. The options available in the style dict are defined below:

    Args:
        textcolor (str): The color code to use for text. Defaults to
            `'#000000'`
        subtextcolor (str): The color code to use for subtext. Defaults to
            `'#000000'`
        linecolor (str): The color code to use for lines. Defaults to
            `'#000000'`
        creglinecolor (str): The color code to use for classical register
            lines. Defaults to `'#778899'`
        gatetextcolor (str): The color code to use for gate text. Defaults to
            `'#000000'`
        gatefacecolor (str): The color code to use for gates. Defaults to
            `'#ffffff'`
        barrierfacecolor (str): The color code to use for barriers. Defaults to
            `'#bdbdbd'`
        backgroundcolor (str): The color code to use for the background.
            Defaults to `'#ffffff'`
        fontsize (int): The font size to use for text. Defaults to 13
        subfontsize (int): The font size to use for subtext. Defaults to 8
        displaytext (dict): A dictionary of the text to use for each element
            type in the output visualization. The default values are::

                {
                    'id': 'id',
                    'u0': 'U_0',
                    'u1': 'U_1',
                    'u2': 'U_2',
                    'u3': 'U_3',
                    'x': 'X',
                    'y': 'Y',
                    'z': 'Z',
                    'h': 'H',
                    's': 'S',
                    'sdg': 'S^\\dagger',
                    't': 'T',
                    'tdg': 'T^\\dagger',
                    'rx': 'R_x',
                    'ry': 'R_y',
                    'rz': 'R_z',
                    'reset': '\\left|0\\right\\rangle'
                }

            You must specify all the necessary values if using this. There is
            no provision for passing an incomplete dict in.
        displaycolor (dict):
            The color codes to use for each circuit element. The default values are::

                {
                    'id': '#F0E442',
                    'u0': '#E7AB3B',
                    'u1': '#E7AB3B',
                    'u2': '#E7AB3B',
                    'u3': '#E7AB3B',
                    'x': '#58C698',
                    'y': '#58C698',
                    'z': '#58C698',
                    'h': '#70B7EB',
                    's': '#E0722D',
                    'sdg': '#E0722D',
                    't': '#E0722D',
                    'tdg': '#E0722D',
                    'rx': '#ffffff',
                    'ry': '#ffffff',
                    'rz': '#ffffff',
                    'reset': '#D188B4',
                    'target': '#70B7EB',
                    'meas': '#D188B4'
                }

           Also, just like  `displaytext` there is no provision for an
           incomplete dict passed in.

        latexdrawerstyle (bool): When set to True enable latex mode which will
            draw gates like the `latex` output modes.
        usepiformat (bool): When set to True use radians for output
        fold (int): The number of circuit elements to fold the circuit at.
            Defaults to 20
        cregbundle (bool): If set True bundle classical registers
        showindex (bool): If set True draw an index.
        compress (bool): If set True draw a compressed circuit
        figwidth (int): The maximum width (in inches) for the output figure.
        dpi (int): The DPI to use for the output image. Defaults to 150
        margin (list): A list of margin values to adjust spacing around output
            image. Takes a list of 4 ints: [x left, x right, y bottom, y top].
        creglinestyle (str): The style of line to use for classical registers.
            Choices are `'solid'`, `'doublet'`, or any valid matplotlib
            `linestyle` kwarg value. Defaults to `doublet`

    Example:
        .. jupyter-execute::

            from qiskit import QuantumRegister, ClassicalRegister, QuantumCircuit
            from qiskit.tools.visualization import circuit_drawer
            q = QuantumRegister(1)
            c = ClassicalRegister(1)
            qc = QuantumCircuit(q, c)
            qc.h(q)
            qc.measure(q, c)
            circuit_drawer(qc)
    """
    image = None
    config = user_config.get_config()
    # Get default from config file else use text
    default_output = 'text'
    if config:
        default_output = config.get('circuit_drawer', 'text')
        if default_output == 'auto':
            if _matplotlib.HAS_MATPLOTLIB:
                default_output = 'mpl'
            else:
                default_output = 'text'
    if output is None:
        output = default_output

    if output == 'text':
        return _text_circuit_drawer(circuit, filename=filename,
                                    line_length=line_length,
                                    reverse_bits=reverse_bits,
                                    plot_barriers=plot_barriers,
                                    justify=justify,
                                    vertical_compression=vertical_compression,
                                    idle_wires=idle_wires,
                                    with_layout=with_layout,
                                    fold=fold,
                                    initial_value=initial_value)
    elif output == 'latex':
        image = _latex_circuit_drawer(circuit, scale=scale,
                                      filename=filename, style=style,
                                      plot_barriers=plot_barriers,
                                      reverse_bits=reverse_bits,
                                      justify=justify,
                                      idle_wires=idle_wires,
                                      with_layout=with_layout,
                                      initial_value=initial_value)
    elif output == 'latex_source':
        return _generate_latex_source(circuit,
                                      filename=filename, scale=scale,
                                      style=style,
                                      plot_barriers=plot_barriers,
                                      reverse_bits=reverse_bits,
                                      justify=justify,
                                      idle_wires=idle_wires,
                                      with_layout=with_layout,
                                      initial_value=initial_value)
    elif output == 'mpl':
        image = _matplotlib_circuit_drawer(circuit, scale=scale,
                                           filename=filename, style=style,
                                           plot_barriers=plot_barriers,
                                           reverse_bits=reverse_bits,
                                           justify=justify,
                                           idle_wires=idle_wires,
                                           with_layout=with_layout,
                                           fold=fold,
                                           ax=ax)
    else:
        raise exceptions.VisualizationError(
            'Invalid output type %s selected. The only valid choices '
            'are latex, latex_source, text, and mpl' % output)
    if image and interactive:
        image.show()
    return image


# -----------------------------------------------------------------------------
# Plot style sheet option
# -----------------------------------------------------------------------------
def qx_color_scheme():
    """Return default style for matplotlib_circuit_drawer (IBM QX style)."""
    warn('The qx_color_scheme function is deprecated as of 0.11, and '
         'will be removed no earlier than 3 months after that release '
         'date.', DeprecationWarning, stacklevel=2)
    return {
        "comment": "Style file for matplotlib_circuit_drawer (IBM QX Composer style)",
        "textcolor": "#000000",
        "gatetextcolor": "#000000",
        "subtextcolor": "#000000",
        "linecolor": "#000000",
        "creglinecolor": "#b9b9b9",
        "gatefacecolor": "#ffffff",
        "barrierfacecolor": "#bdbdbd",
        "backgroundcolor": "#ffffff",
        "fold": 20,
        "fontsize": 13,
        "subfontsize": 8,
        "figwidth": -1,
        "dpi": 150,
        "displaytext": {
            "id": "id",
            "u0": "U_0",
            "u1": "U_1",
            "u2": "U_2",
            "u3": "U_3",
            "x": "X",
            "y": "Y",
            "z": "Z",
            "h": "H",
            "s": "S",
            "sdg": "S^\\dagger",
            "t": "T",
            "tdg": "T^\\dagger",
            "rx": "R_x",
            "ry": "R_y",
            "rz": "R_z",
            "reset": "\\left|0\\right\\rangle"
        },
        "displaycolor": {
            "id": "#ffca64",
            "u0": "#f69458",
            "u1": "#f69458",
            "u2": "#f69458",
            "u3": "#f69458",
            "x": "#a6ce38",
            "y": "#a6ce38",
            "z": "#a6ce38",
            "h": "#00bff2",
            "s": "#00bff2",
            "sdg": "#00bff2",
            "t": "#ff6666",
            "tdg": "#ff6666",
            "rx": "#ffca64",
            "ry": "#ffca64",
            "rz": "#ffca64",
            "reset": "#d7ddda",
            "target": "#00bff2",
            "meas": "#f070aa"
        },
        "latexdrawerstyle": True,
        "usepiformat": False,
        "cregbundle": False,
        "showindex": False,
        "compress": True,
        "margin": [2.0, 0.0, 0.0, 0.3],
        "creglinestyle": "solid",
        "reversebits": False
    }


# -----------------------------------------------------------------------------
# _text_circuit_drawer
# -----------------------------------------------------------------------------


def _text_circuit_drawer(circuit, filename=None, line_length=None, reverse_bits=False,
                         plot_barriers=True, justify=None, vertical_compression='high',
                         idle_wires=True, with_layout=True, fold=None, initial_value=True):
    """Draws a circuit using ascii art.

    Args:
        circuit (QuantumCircuit): Input circuit
        filename (str): optional filename to write the result
        line_length (int): Deprecated. See `fold`.
        reverse_bits (bool): Rearrange the bits in reverse order.
        plot_barriers (bool): Draws the barriers when they are there.
        justify (str) : `left`, `right` or `none`. Defaults to `left`. Says how
                        the circuit should be justified.
        vertical_compression (string): `high`, `medium`, or `low`. It merges the
            lines so the drawing will take less vertical room. Default is `high`.
        idle_wires (bool): Include idle wires. Default is True.
        with_layout (bool): Include layout information, with labels on the physical
            layout. Default: True
        fold (int): Optional. Breaks the circuit drawing to this length. This
                    useful when the drawing does not fit in the console. If
                    None (default), it will try to guess the console width using
                    `shutil.get_terminal_size()`. If you don't want pagination
                   at all, set `fold=-1`.
        initial_value (bool): Optional. Adds |0> in the beginning of the line. Default: `True`.
    Returns:
        TextDrawing: An instances that, when printed, draws the circuit in ascii art.
    """
    qregs, cregs, ops = utils._get_layered_instructions(circuit,
                                                        reverse_bits=reverse_bits,
                                                        justify=justify,
                                                        idle_wires=idle_wires)
    if with_layout:
        layout = circuit._layout
    else:
        layout = None
    if line_length:
        warn('The parameter "line_length" is being replaced by "fold"', DeprecationWarning, 3)
        fold = line_length
    text_drawing = _text.TextDrawing(qregs, cregs, ops, layout=layout, initial_value=initial_value)
    text_drawing.plotbarriers = plot_barriers
    text_drawing.line_length = fold
    text_drawing.vertical_compression = vertical_compression

    if filename:
        text_drawing.dump(filename)
    return text_drawing


# -----------------------------------------------------------------------------
# latex_circuit_drawer
# -----------------------------------------------------------------------------


def _latex_circuit_drawer(circuit,
                          scale=0.7,
                          filename=None,
                          style=None,
                          plot_barriers=True,
                          reverse_bits=False,
                          justify=None,
                          idle_wires=True,
                          with_layout=True,
                          initial_value=False):
    """Draw a quantum circuit based on latex (Qcircuit package)

    Requires version >=2.6.0 of the qcircuit LaTeX package.

    Args:
        circuit (QuantumCircuit): a quantum circuit
        scale (float): scaling factor
        filename (str): file path to save image to
        style (dict or str): dictionary of style or file name of style file
        reverse_bits (bool): When set to True reverse the bit order inside
            registers for the output visualization.
        plot_barriers (bool): Enable/disable drawing barriers in the output
            circuit. Defaults to True.
        justify (str) : `left`, `right` or `none`. Defaults to `left`. Says how
                        the circuit should be justified.
        idle_wires (bool): Include idle wires. Default is True.
        with_layout (bool): Include layout information, with labels on the physical
            layout. Default: True
        initial_value (bool): Optional. Adds |0> in the beginning of the line. Default: `False`.

    Returns:
        PIL.Image: an in-memory representation of the circuit diagram

    Raises:
        OSError: usually indicates that ```pdflatex``` or ```pdftocairo``` is
                 missing.
        CalledProcessError: usually points errors during diagram creation.
        ImportError: if pillow is not installed
    """
    tmpfilename = 'circuit'
    with tempfile.TemporaryDirectory() as tmpdirname:
        tmppath = os.path.join(tmpdirname, tmpfilename + '.tex')
        _generate_latex_source(circuit, filename=tmppath,
                               scale=scale, style=style,
                               plot_barriers=plot_barriers,
                               reverse_bits=reverse_bits, justify=justify,
                               idle_wires=idle_wires, with_layout=with_layout,
                               initial_value=initial_value)
        try:

            subprocess.run(["pdflatex", "-halt-on-error",
                            "-output-directory={}".format(tmpdirname),
                            "{}".format(tmpfilename + '.tex')],
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                           check=True)
        except OSError as ex:
            if ex.errno == errno.ENOENT:
                logger.warning('WARNING: Unable to compile latex. '
                               'Is `pdflatex` installed? '
                               'Skipping latex circuit drawing...')
            raise
        except subprocess.CalledProcessError as ex:
            with open('latex_error.log', 'wb') as error_file:
                error_file.write(ex.stdout)
            logger.warning('WARNING Unable to compile latex. '
                           'The output from the pdflatex command can '
                           'be found in latex_error.log')
            raise
        else:
            if not HAS_PIL:
                raise ImportError('The latex drawer needs pillow installed. '
                                  'Run "pip install pillow" before using the '
                                  'latex drawer.')
            try:
                base = os.path.join(tmpdirname, tmpfilename)
                subprocess.run(["pdftocairo", "-singlefile", "-png", "-q",
                                base + '.pdf', base], check=True)
                image = Image.open(base + '.png')
                image = utils._trim(image)
                os.remove(base + '.png')
                if filename:
                    image.save(filename, 'PNG')
            except (OSError, subprocess.CalledProcessError) as ex:
                logger.warning('WARNING: Unable to convert pdf to image. '
                               'Is `poppler` installed? '
                               'Skipping circuit drawing...')
                raise
        return image


def _generate_latex_source(circuit, filename=None,
                           scale=0.7, style=None, reverse_bits=False,
                           plot_barriers=True, justify=None, idle_wires=True,
                           with_layout=True, initial_value=False):
    """Convert QuantumCircuit to LaTeX string.

    Args:
        circuit (QuantumCircuit): input circuit
        scale (float): image scaling
        filename (str): optional filename to write latex
        style (dict or str): dictionary of style or file name of style file
        reverse_bits (bool): When set to True reverse the bit order inside
            registers for the output visualization.
        plot_barriers (bool): Enable/disable drawing barriers in the output
            circuit. Defaults to True.
        justify (str) : `left`, `right` or `none`. Defaults to `left`. Says how
                        the circuit should be justified.
        idle_wires (bool): Include idle wires. Default is True.
        with_layout (bool): Include layout information, with labels on the physical
            layout. Default: True
        initial_value (bool): Optional. Adds |0> in the beginning of the line. Default: `False`.

    Returns:
        str: Latex string appropriate for writing to file.
    """
    qregs, cregs, ops = utils._get_layered_instructions(circuit,
                                                        reverse_bits=reverse_bits,
                                                        justify=justify, idle_wires=idle_wires)
    if with_layout:
        layout = circuit._layout
    else:
        layout = None

    qcimg = _latex.QCircuitImage(qregs, cregs, ops, scale, style=style,
                                 plot_barriers=plot_barriers,
                                 reverse_bits=reverse_bits, layout=layout,
                                 initial_value=initial_value)
    latex = qcimg.latex()
    if filename:
        with open(filename, 'w') as latex_file:
            latex_file.write(latex)

    return latex


# -----------------------------------------------------------------------------
# matplotlib_circuit_drawer
# -----------------------------------------------------------------------------


def _matplotlib_circuit_drawer(circuit,
                               scale=0.7,
                               filename=None,
                               style=None,
                               plot_barriers=True,
                               reverse_bits=False,
                               justify=None,
                               idle_wires=True,
                               with_layout=True,
                               fold=None,
                               ax=None):
    """Draw a quantum circuit based on matplotlib.
    If `%matplotlib inline` is invoked in a Jupyter notebook, it visualizes a circuit inline.
    We recommend `%config InlineBackend.figure_format = 'svg'` for the inline visualization.

    Args:
        circuit (QuantumCircuit): a quantum circuit
        scale (float): scaling factor
        filename (str): file path to save image to
        style (dict or str): dictionary of style or file name of style file
        reverse_bits (bool): When set to True reverse the bit order inside
            registers for the output visualization.
        plot_barriers (bool): Enable/disable drawing barriers in the output
            circuit. Defaults to True.
        justify (str): `left`, `right` or `none`. Defaults to `left`. Says how
            the circuit should be justified.
        idle_wires (bool): Include idle wires. Default is True.
        with_layout (bool): Include layout information, with labels on the physical
            layout. Default: True.
        fold (int): amount ops allowed before folding. Default is 25.
        ax (matplotlib.axes.Axes): An optional Axes object to be used for
            the visualization output. If none is specified a new matplotlib
            Figure will be created and used. Additionally, if specified there
            will be no returned Figure since it is redundant.

    Returns:
        matplotlib.figure: a matplotlib figure object for the circuit diagram
            if the ``ax`` kwarg is not set.
    """

    qregs, cregs, ops = utils._get_layered_instructions(circuit,
                                                        reverse_bits=reverse_bits,
                                                        justify=justify,
                                                        idle_wires=idle_wires)
    if with_layout:
        layout = circuit._layout
    else:
        layout = None

    if fold is None:
        fold = 25

    qcd = _matplotlib.MatplotlibDrawer(qregs, cregs, ops, scale=scale, style=style,
                                       plot_barriers=plot_barriers,
                                       reverse_bits=reverse_bits, layout=layout,
                                       fold=fold, ax=ax)
    return qcd.draw(filename)
