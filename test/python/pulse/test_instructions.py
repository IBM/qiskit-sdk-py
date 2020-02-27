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

# pylint: disable=invalid-name,unexpected-keyword-arg

"""Unit tests for pulse instructions."""

from qiskit.pulse import ShiftPhase, DriveChannel
from qiskit.test import QiskitTestCase


class TestShiftPhase(QiskitTestCase):
    """Test the instruction construction."""

    def test_default(self):
        """Test basic ShiftPhase."""
        fc_command = ShiftPhase(1.57, DriveChannel(0))

        self.assertEqual(fc_command.phase, 1.57)
        self.assertEqual(fc_command.duration, 0)
        self.assertTrue(fc_command.name.startswith('fc'))
