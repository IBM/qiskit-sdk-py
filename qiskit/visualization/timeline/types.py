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
ScheduledGate.__doc__ = 'Data to represent a scheduled gate instruction.'
ScheduledGate.t0.__doc__ = 'A time when the gate instruction is issued.'
ScheduledGate.operand.__doc__ = 'Gate instruction.'
ScheduledGate.duration.__doc__ = 'Duration of this gate.'
ScheduledGate.bits.__doc__ = 'All bits associated with this gate.'


GateLink = NamedTuple(
    'GateLink',
    [('t0', int),
     ('opname', str),
     ('bits', List[Union[circuit.Qubit, circuit.Clbit]])])
GateLink.__doc__ = 'Data to represent a link between bits during a gate.'
GateLink.t0.__doc__ = 'A time when the link is placed.'
GateLink.opname.__doc__ = 'Name of gate associated with this link.'
GateLink.bits.__doc__ = 'All bits associated with this link.'


Barrier = NamedTuple(
    'Barrier',
    [('t0', int),
     ('bits', List[Union[circuit.Qubit, circuit.Clbit]])])
Barrier.__doc__ = 'Data to represent a barrier instruction.'
Barrier.t0.__doc__ = 'A time when a barrier is placed.'
Barrier.bits.__doc__ = 'All bits associated with this barrier.'


class DrawingBox(Enum):
    """Box data type.

    SCHED_GATE: Box that represents occupation time by gate.
    TIMELINE: Box that represents time slot of a bit.
    """
    SCHED_GATE = 'Box.ScheduledGate'
    DELAY = 'Box.Delay'
    TIMELINE = 'Box.Timeline'


class DrawingLine(Enum):
    """Line data type.

    BARRIER: Line that represents barrier instruction.
    """
    BARRIER = 'Line.Barrier'
    BIT_LINK = 'Line.BitLink'


class DrawingSymbol(Enum):
    """Symbol data type.

    FRAME: Symbol that represents zero time frame change (Rz) instruction.
    """
    FRAME = 'Symbol.Frame'


class DrawingLabel(Enum):
    """Label data type.

    GATE_NAME: Label that represents name of gate.
    GATE_PARAM: Label that represents parameter of gate.
    BIT_NAME: Label that represents name of bit.
    """
    GATE_NAME = 'Label.Gate.Name'
    DELAY = 'Label.Delay'
    GATE_PARAM = 'Label.Gate.Param'
    BIT_NAME = 'Label.Bit.Name'


class AbstractCoordinate(Enum):
    """Abstract coordinate that the exact value depends on the user preference.

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
