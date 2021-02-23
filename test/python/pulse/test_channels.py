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

"""Test cases for the pulse channel group."""

import unittest

from qiskit.circuit import Parameter
from qiskit.pulse.channels import (AcquireChannel, Channel, DriveChannel, Frame,
                                   ControlChannel, MeasureChannel, MemorySlot,
                                   PulseChannel, RegisterSlot, SnapshotChannel)
from qiskit.test import QiskitTestCase


class TestChannel(QiskitTestCase):
    """Test base channel."""

    def test_cannot_be_instantiated(self):
        """Test base channel cannot be instantiated."""
        with self.assertRaises(NotImplementedError):
            Channel(0)


class TestPulseChannel(QiskitTestCase):
    """Test base pulse channel."""

    def test_cannot_be_instantiated(self):
        """Test base pulse channel cannot be instantiated."""
        with self.assertRaises(NotImplementedError):
            PulseChannel(0)


class TestAcquireChannel(QiskitTestCase):
    """AcquireChannel tests."""

    def test_default(self):
        """Test default acquire channel.
        """
        acquire_channel = AcquireChannel(123)

        self.assertEqual(acquire_channel.index, 123)
        self.assertEqual(acquire_channel.name, 'a123')

    def test_channel_hash(self):
        """Test hashing for acquire channel.
        """
        acq_channel_1 = AcquireChannel(123)
        acq_channel_2 = AcquireChannel(123)

        hash_1 = hash(acq_channel_1)
        hash_2 = hash(acq_channel_2)

        self.assertEqual(hash_1, hash_2)


class TestMemorySlot(QiskitTestCase):
    """AcquireChannel tests."""

    def test_default(self):
        """Test default memory slot.
        """
        memory_slot = MemorySlot(123)

        self.assertEqual(memory_slot.index, 123)
        self.assertEqual(memory_slot.name, 'm123')


class TestRegisterSlot(QiskitTestCase):
    """RegisterSlot tests."""

    def test_default(self):
        """Test default register slot.
        """
        register_slot = RegisterSlot(123)

        self.assertEqual(register_slot.index, 123)
        self.assertEqual(register_slot.name, 'c123')


class TestSnapshotChannel(QiskitTestCase):
    """SnapshotChannel tests."""

    def test_default(self):
        """Test default snapshot channel.
        """
        snapshot_channel = SnapshotChannel()

        self.assertEqual(snapshot_channel.index, 0)
        self.assertEqual(snapshot_channel.name, 's0')


class TestDriveChannel(QiskitTestCase):
    """DriveChannel tests."""

    def test_default(self):
        """Test default drive channel.
        """
        drive_channel = DriveChannel(123)

        self.assertEqual(drive_channel.index, 123)
        self.assertEqual(drive_channel.name, 'd123')


class TestControlChannel(QiskitTestCase):
    """ControlChannel tests."""

    def test_default(self):
        """Test default control channel.
        """
        control_channel = ControlChannel(123)

        self.assertEqual(control_channel.index, 123)
        self.assertEqual(control_channel.name, 'u123')


class TestMeasureChannel(QiskitTestCase):
    """MeasureChannel tests."""

    def test_default(self):
        """Test default measure channel.
        """
        measure_channel = MeasureChannel(123)

        self.assertEqual(measure_channel.index, 123)
        self.assertEqual(measure_channel.name, 'm123')


class TestFrame(QiskitTestCase):
    """Frame tests."""

    def test_default(self):
        """Test default Frame."""
        frame = Frame(123, [DriveChannel(1), ControlChannel(0), ControlChannel(0)])

        self.assertEqual(frame.index, 123)
        self.assertEqual(frame.name, 'f123')
        self.assertEqual(frame.channels, {DriveChannel(1), ControlChannel(0)})

    def test_parameters(self):
        """Test that parameters are properly registered."""
        f0 = Parameter('name')
        d0 = DriveChannel(Parameter('d0'))
        u0 = ControlChannel(Parameter('u0'))
        frame = Frame(f0, [d0, u0])

        self.assertEqual(len(frame.parameters), 3)

    def test_assign_parameter(self):
        """Test that parameter assignment works."""

        # Test that assignment works when there is a parameter coupling
        # between the frame index and an index of a sub-channels.
        f0 = Parameter('name')
        d0 = DriveChannel(f0)
        frame = Frame(f0, [d0, ControlChannel(4)])

        self.assertEqual(frame.index.name, 'name')
        self.assertEqual(frame.channels, {d0, ControlChannel(4)})

        new_frame = frame.assign(f0, 123)
        self.assertEqual(new_frame.index, 123)
        self.assertEqual(new_frame.channels, {DriveChannel(123), ControlChannel(4)})

        # Test that assignment works when there are multiple parameters.
        p0 = Parameter('p0')
        p1 = Parameter('p1')
        d0 = DriveChannel(p1)
        frame = Frame(p0, [d0, ControlChannel(4)])

        self.assertEqual(frame.index.name, 'p0')
        self.assertEqual(frame.channels, {d0, ControlChannel(4)})

        new_frame = frame.assign(p0, 123)
        self.assertEqual(new_frame.index, 123)
        self.assertEqual(new_frame.channels, {DriveChannel(p1), ControlChannel(4)})

        new_frame = new_frame.assign_parameters({p1: 234})
        self.assertEqual(new_frame.index, 123)
        self.assertEqual(new_frame.channels, {DriveChannel(234), ControlChannel(4)})

        # Test multi-parameter assignment
        p0 = Parameter('p0')
        p1 = Parameter('p1')
        p2 = Parameter('p2')
        p3 = Parameter('p3')
        frame = Frame(p0, [DriveChannel(p1), ControlChannel(p2), ControlChannel(p3)])
        self.assertEqual(frame.index, p0)
        frame = frame.assign(p0, 12)
        self.assertEqual(frame.index, 12)

        frame = frame.assign_parameters({p0: 12, p1: 34, p2: 2})
        self.assertEqual(frame.channels, {ControlChannel(p3), ControlChannel(2), DriveChannel(34)})

        # Test parameter assignment with math
        frame = Frame(p0, [DriveChannel(p0), ControlChannel(p0 + 1)])
        frame = frame.assign_parameters({p0: 12})
        self.assertEqual(frame.index, 12)
        self.assertEqual(frame.channels, {ControlChannel(13), DriveChannel(12)})


if __name__ == '__main__':
    unittest.main()
