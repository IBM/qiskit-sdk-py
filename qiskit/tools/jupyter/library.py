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
# pylint: disable=invalid-name, no-name-in-module

"""A circuit library widget module"""

import ipywidgets as wid
from IPython.display import display
import pygments
from pygments.formatters import HtmlFormatter
from qiskit import QuantumCircuit
from qiskit.qasm.pygments import QasmHTMLStyle, OpenQASMLexer


def circuit_data_table(circuit: QuantumCircuit) -> wid.HTML:
    """Create a HTML table widget for a given quantum circuit.

    Args:
        circuit: Input quantum circuit.

    Returns:
        Output widget.
    """

    ops = circuit.count_ops()

    num_cx = None
    if 'cx' in ops.keys():
        num_cx = ops['cx']

    html = "<table>"
    html += """<style>
table {
    font-family: "IBM Plex Sans", Arial, Helvetica, sans-serif;
    border-collapse: collapse;
    width: 100%;
    border-left: 2px solid #212121;
}

th {
    text-align: left;
    padding: 5px 5px 5px 5px;
    width: 100%;
    background-color: #3700BE;
    color: #fff;
    font-size: 18px;
    border-left: 2px solid #3700BE;
}

td {
    font-family: "IBM Plex Mono", monospace;
    text-align: left;
    padding: 5px 5px 5px 5px;
    width: 100%;
    font-size: 14px;
    font-weight: medium;
}

tr:nth-child(even) {background-color: #f6f6f6;}
</style>"""
    html += "<tr><th>{}</th><th></tr>".format(circuit.name)

    html += "<tr><td>Width</td><td>{}</td></tr>".format(circuit.width())
    html += "<tr><td>Depth</td><td>{}</td></tr>".format(circuit.depth())
    html += "<tr><td>Gate Count</td><td>{}</td></tr>".format(sum(ops.values()))
    html += "<tr><td>CX Count</td><td>{}</td></tr>".format(num_cx)
    html += "</table>"

    out_wid = wid.HTML(html)
    return out_wid


head_style = 'font-family: IBM Plex Sans, Arial, Helvetica, sans-serif;' \
             ' font-size: 28px; font-weight: medium;'

detail_label = wid.HTML("<p style='{}'>Circuit Details</p>".format(head_style),
                        layout=wid.Layout(margin='0px 0px 10px 0px'))


def details_widget(circuit: QuantumCircuit) -> wid.VBox:
    """Create a HTML table widget with header for a given quantum circuit.

    Args:
        circuit: Input quantum circuit.

    Returns:
        Output widget.
    """
    details = wid.VBox(children=[detail_label,
                                 circuit_data_table(circuit)],
                       layout=wid.Layout(width='30%',
                                         height='auto'))
    return details


def qasm_widget(circuit: QuantumCircuit) -> wid.VBox:
    """Generate a QASM widget with header for a quantum circuit.

    Args:
        circuit: Input quantum circuit.

    Returns:
        Output widget.

    """

    code = pygments.highlight(circuit.qasm(), OpenQASMLexer(),
                              HtmlFormatter())

    html_style = HtmlFormatter(style=QasmHTMLStyle).get_style_defs('.highlight')

    code_style = """
    <style>
     .highlight
                {
                    font-family:    monospace;
                    font-size: 14px;
                    line-height: 1.7em;
                }
    %s
    </style>
    """ % html_style

    out = wid.HTML(code_style+code,
                   layout=wid.Layout(max_height='500px',
                                     height='500px',
                                     overflow='hidden scroll'))

    out_label = wid.HTML("<p style='{}'>Circuit QASM</p>".format(head_style),
                         layout=wid.Layout(margin='0px 0px 10px 0px'))

    qasm = wid.VBox(children=[out_label, out],
                    layout=wid.Layout(height='510px', max_height='510px', width='70%',
                                      margin='0px 0px 0px 20px'))

    return qasm


def circuit_diagram_widget(circuit: QuantumCircuit) -> wid.VBox:
    """Create a circuit diagram widget.

    Args:
        circuit: Input quantum circuit.

    Returns:
        Output widget.
    """
    top_label = wid.HTML("<p style='{}'>Circuit Diagram</p>".format(head_style),
                         layout=wid.Layout(margin='0px 0px 10px 0px'))

    # The max circuit height corresponds to a 20Q circuit with flat
    # classical register.
    top_out = wid.Output(layout=wid.Layout(width='100%',
                                           height='auto',
                                           max_height='1000px',
                                           overflow='hidden scroll',))
    with top_out:
        display(circuit.draw(output='mpl'))

    top = wid.VBox(children=[top_label, top_out], layout=wid.Layout(width='100%', height='auto'))

    return top


# The seperator widget
sep = wid.HTML("<div style='border-left: 3px solid #212121;height: 475px;'></div>",
               layout=wid.Layout(height='500px',
                                 max_height='500px',
                                 margin='40px 0px 0px 20px'))


def circuit_library_widget(circuit: QuantumCircuit) -> None:
    """Create a circuit library widget.

    Args:
        circuit: Input quantum circuit.
    """
    bottom = wid.HBox(children=[details_widget(circuit),
                                sep,
                                qasm_widget(circuit)],
                      layout=wid.Layout(max_height='100%',
                                        height='100%'))

    top = circuit_diagram_widget(circuit)

    display(wid.VBox(children=[top, bottom],
                     layout=wid.Layout(width='100%',
                                       height='auto')))
