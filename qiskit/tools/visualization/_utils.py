# -*- coding: utf-8 -*-

# Copyright 2018, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree

"""Common visualization utilities."""

import PIL


def _trim(image):
    """Trim a PIL image and remove white space."""
    background = PIL.Image.new(image.mode, image.size, image.getpixel((0, 0)))
    diff = PIL.ImageChops.difference(image, background)
    diff = PIL.ImageChops.add(diff, diff, 2.0, -100)
    bbox = diff.getbbox()
    if bbox:
        image = image.crop(bbox)
    return image

def _get_instructions(dag, reversebits=False):
    """
    Given a dag, return a tuple (qregs, cregs, ops) where
    qregs and cregs are the name of the quantum and classical
    registers in order (based on reversebits) and ops is a list
    of DAG nodes which type is "operation".
    Args:
        dag (DAGCircuit): From where the information is extracted.
        reversebits (bool): If true the order of the bits in the registers is reversed.
    Returns:
        Tuple(list,list,list): To be consumed by the visualizer directly.
    """
    ops = []
    for node_no in dag.node_nums_in_topological_order:
        node = dag.multi_graph.node[node_no]
        if node['type'] == 'op':
            ops.append(node)
    return dag.qregs, dag.cregs, ops