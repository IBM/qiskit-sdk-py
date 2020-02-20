# -*- coding: utf-8 -*-

# This code is part of Qiskit.
#
# (C) Copyright IBM 2017, 2019.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""The ``instruction`` module holds the various ``Instruction`` s which are supported by
Qiskit Pulse. Instructions accept a list of operands unique to instructions of that type. Every
instruction includes at least one :py:class:`~qiskit.pulse.channels.Channel` as an operand
specifying where the instruction will be applied, and every instruction has either an explict
duration as one of its operands or an implicit duration of ``0``.

An instruction can be added to a :py:class:`~qiskit.pulse.Schedule`, which is a
sequence of scheduled Pulse ``Instruction`` s over many channels.
"""
from .instruction import Instruction
