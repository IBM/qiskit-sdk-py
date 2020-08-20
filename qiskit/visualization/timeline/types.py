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

"""
Special data types.
"""

from enum import Enum
from typing import NamedTuple, List, Union, NewType

from qiskit import circuit


ScheduledGate = NamedTuple(
    'ScheduledGate',
    [('t0', int),
     ('operand', circuit.Gate),
     ('duration', int),
     ('bits', List[Union[circuit.Qubit, circuit.Clbit]])])
ScheduledGate.__doc__ = 'A gate instruction with embedded time.'
ScheduledGate.t0.__doc__ = 'Time when the instruction is issued.'
ScheduledGate.operand.__doc__ = 'Gate object associated with the instruction.'
ScheduledGate.duration.__doc__ = 'Time duration of the instruction.'
ScheduledGate.bits.__doc__ = 'List of bit associated with the instruction.'


GateLink = NamedTuple(
    'GateLink',
    [('t0', int),
     ('operand', circuit.Gate),
     ('bits', List[Union[circuit.Qubit, circuit.Clbit]])])
GateLink.__doc__ = 'Dedicated object to represent a relationship between instructions.'
GateLink.t0.__doc__ = 'A position where the link is placed.'
GateLink.operand.__doc__ = 'Gate object associated with the link.'
GateLink.bits.__doc__ = 'List of bit associated with the instruction.'


Barrier = NamedTuple(
    'Barrier',
    [('t0', int),
     ('bits', List[Union[circuit.Qubit, circuit.Clbit]])])
Barrier.__doc__ = 'Dedicated object to represent a barrier instruction.'
Barrier.t0.__doc__ = 'A position where the barrier is placed.'
Barrier.bits.__doc__ = 'List of bit associated with the instruction.'


class DrawingBox(str, Enum):
    r"""Box data type.

    SCHED_GATE: Box that represents occupation time by gate.
    TIMELINE: Box that represents time slot of a bit.
    """
    SCHED_GATE = 'Box.ScheduledGate'
    DELAY = 'Box.Delay'
    TIMELINE = 'Box.Timeline'


class DrawingLine(str, Enum):
    r"""Line data type.

    BARRIER: Line that represents barrier instruction.
    """
    BARRIER = 'Line.Barrier'
    BIT_LINK = 'Line.BitLink'


class DrawingSymbol(str, Enum):
    r"""Symbol data type.

    FRAME: Symbol that represents zero time frame change (Rz) instruction.
    """
    FRAME = 'Symbol.Frame'


class DrawingLabel(str, Enum):
    r"""Label data type.

    GATE_NAME: Label that represents name of gate.
    GATE_PARAM: Label that represents parameter of gate.
    BIT_NAME: Label that represents name of bit.
    """
    GATE_NAME = 'Label.Gate.Name'
    DELAY = 'Label.Delay'
    GATE_PARAM = 'Label.Gate.Param'
    BIT_NAME = 'Label.Bit.Name'


class AbstractCoordinate(str, Enum):
    r"""Abstract coordinate that the exact value depends on the user preference.

    RIGHT: The horizontal coordinate at t0 shifted by the left margin.
    LEFT: The horizontal coordinate at tf shifted by the right margin.
    TOP: The vertical coordinate at the top of the canvas.
    BOTTOM: The vertical coordinate at the bottom of the canvas.
    """
    RIGHT = 'RIGHT'
    LEFT = 'LEFT'
    TOP = 'TOP'
    BOTTOM = 'BOTTOM'


Coordinate = NewType('Coordinate', Union[int, float, AbstractCoordinate])
Bits = NewType('Bits', Union[circuit.Qubit, circuit.Clbit])
