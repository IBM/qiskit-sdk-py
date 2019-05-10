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

"""Converter Test."""

import numpy as np

from qiskit.test import QiskitTestCase
from qiskit.qobj import (PulseQobjInstruction, PulseQobjExperimentConfig, PulseLibraryItem,
                         QobjMeasurementOption)
from qiskit.qobj.converters import (InstructionToQobjConverter, QobjToInstructionConverter,
                                    LoConfigConverter)
from qiskit.pulse.instructions import (SetPhase, ShiftPhase, SetFrequency, ShiftFrequency, Play,
                                       Delay, Acquire, Snapshot)
from qiskit.pulse.channels import (DriveChannel, ControlChannel, MeasureChannel, AcquireChannel,
                                   MemorySlot, RegisterSlot)
from qiskit.pulse.library import Waveform, Gaussian, GaussianSquare, Constant, Drag
from qiskit.pulse.schedule import ParameterizedSchedule, Schedule
from qiskit.pulse import LoConfig, Kernel, Discriminator


class TestInstructionToQobjConverter(QiskitTestCase):
    """Pulse converter tests."""

    def test_drive_instruction(self):
        """Test converted qobj from Play."""
        converter = InstructionToQobjConverter(PulseQobjInstruction, meas_level=2)
        instruction = Play(Waveform(np.arange(0, 0.01), name='linear'), DriveChannel(0))
        valid_qobj = PulseQobjInstruction(
            name='linear',
            ch='d0',
            t0=0)
        self.assertEqual(converter(0, instruction), valid_qobj)

    def test_gaussian_pulse_instruction(self):
        """Test that parametric pulses are correctly converted to PulseQobjInstructions."""
        converter = InstructionToQobjConverter(PulseQobjInstruction, meas_level=2)
        instruction = Play(Gaussian(duration=25, sigma=15, amp=-0.5 + 0.2j), DriveChannel(0))
        valid_qobj = PulseQobjInstruction(
            name='parametric_pulse',
            pulse_shape='gaussian',
            ch='d0',
            t0=0,
            parameters={'duration': 25, 'sigma': 15, 'amp': -0.5 + 0.2j})
        self.assertEqual(converter(0, instruction), valid_qobj)

    def test_gaussian_square_pulse_instruction(self):
        """Test that parametric pulses are correctly converted to PulseQobjInstructions."""
        converter = InstructionToQobjConverter(PulseQobjInstruction, meas_level=2)
        instruction = Play(GaussianSquare(duration=1500, sigma=15, amp=-0.5 + 0.2j, width=1300),
                           MeasureChannel(1))

        valid_qobj = PulseQobjInstruction(
            name='parametric_pulse',
            pulse_shape='gaussian_square',
            ch='m1',
            t0=10,
            parameters={'duration': 1500, 'sigma': 15, 'amp': -0.5 + 0.2j, 'width': 1300})
        self.assertEqual(converter(10, instruction), valid_qobj)

    def test_constant_pulse_instruction(self):
        """Test that parametric pulses are correctly converted to PulseQobjInstructions."""
        converter = InstructionToQobjConverter(PulseQobjInstruction, meas_level=2)
        instruction = Play(Constant(duration=25, amp=1), ControlChannel(2))

        valid_qobj = PulseQobjInstruction(
            name='parametric_pulse',
            pulse_shape='constant',
            ch='u2',
            t0=20,
            parameters={'duration': 25, 'amp': 1})
        self.assertEqual(converter(20, instruction), valid_qobj)

    def test_drag_pulse_instruction(self):
        """Test that parametric pulses are correctly converted to PulseQobjInstructions."""
        converter = InstructionToQobjConverter(PulseQobjInstruction, meas_level=2)
        instruction = Play(Drag(duration=25, sigma=15, amp=-0.5 + 0.2j, beta=0.5), DriveChannel(0))

        valid_qobj = PulseQobjInstruction(
            name='parametric_pulse',
            pulse_shape='drag',
            ch='d0',
            t0=30,
            parameters={'duration': 25, 'sigma': 15, 'amp': -0.5 + 0.2j, 'beta': 0.5})
        self.assertEqual(converter(30, instruction), valid_qobj)

    def test_frame_change(self):
        """Test converted qobj from ShiftPhase."""
        converter = InstructionToQobjConverter(PulseQobjInstruction, meas_level=2)
        valid_qobj = PulseQobjInstruction(
            name='fc',
            ch='d0',
            t0=0,
            phase=0.1
        )
        instruction = ShiftPhase(0.1, DriveChannel(0))
        self.assertEqual(converter(0, instruction), valid_qobj)

    def test_set_phase(self):
        """Test converted qobj from ShiftPhase."""
        converter = InstructionToQobjConverter(PulseQobjInstruction, meas_level=2)
        instruction = SetPhase(3.14, DriveChannel(0))

        valid_qobj = PulseQobjInstruction(
            name='setp',
            ch='d0',
            t0=0,
            phase=3.14
        )

        self.assertEqual(converter(0, instruction), valid_qobj)

    def test_set_frequency(self):
        """Test converted qobj from SetFrequency."""
        converter = InstructionToQobjConverter(PulseQobjInstruction, meas_level=2)
        instruction = SetFrequency(8.0e9, DriveChannel(0))

        valid_qobj = PulseQobjInstruction(
            name='setf',
            ch='d0',
            t0=0,
            frequency=8.0
        )

        self.assertEqual(converter(0, instruction), valid_qobj)

    def test_shift_frequency(self):
        """Test converted qobj from ShiftFrequency."""
        converter = InstructionToQobjConverter(PulseQobjInstruction, meas_level=2)
        instruction = ShiftFrequency(8.0e9, DriveChannel(0))

        valid_qobj = PulseQobjInstruction(
            name='shiftf',
            ch='d0',
            t0=0,
            frequency=8.0
        )

        self.assertEqual(converter(0, instruction), valid_qobj)

    def test_acquire(self):
        """Test converted qobj from AcquireInstruction."""
        converter = InstructionToQobjConverter(PulseQobjInstruction, meas_level=2)
        instruction = Acquire(10, AcquireChannel(0), MemorySlot(0), RegisterSlot(0))
        valid_qobj = PulseQobjInstruction(
            name='acquire',
            t0=0,
            duration=10,
            qubits=[0],
            memory_slot=[0],
            register_slot=[0])
        self.assertEqual(converter(0, instruction), valid_qobj)

        # without register
        instruction = Acquire(10, AcquireChannel(0), MemorySlot(0))
        valid_qobj = PulseQobjInstruction(
            name='acquire',
            t0=0,
            duration=10,
            qubits=[0],
            memory_slot=[0])
        self.assertEqual(converter(0, instruction), valid_qobj)

    def test_snapshot(self):
        """Test converted qobj from Snapshot."""
        converter = InstructionToQobjConverter(PulseQobjInstruction, meas_level=2)
        instruction = Snapshot(label='label', snapshot_type='type')

        valid_qobj = PulseQobjInstruction(
            name='snapshot',
            t0=0,
            label='label',
            type='type'
        )

        self.assertEqual(converter(0, instruction), valid_qobj)


class TestQobjToInstructionConverter(QiskitTestCase):
    """Pulse converter tests."""

    def setUp(self):
        super().setUp()
        self.linear = Waveform(np.arange(0, 0.01), name='linear')
        self.pulse_library = [PulseLibraryItem(name=self.linear.name,
                                               samples=self.linear.samples.tolist())]

        self.converter = QobjToInstructionConverter(self.pulse_library, buffer=0)
        self.num_qubits = 2

    def test_drive_instruction(self):
        """Test converted qobj from PulseInstruction."""
        instruction = Play(self.linear, DriveChannel(0))
        qobj = PulseQobjInstruction(name='linear', ch='d0', t0=10)
        converted_instruction = self.converter(qobj)
        self.assertEqual(converted_instruction.instructions[0][-1], instruction)

    def test_parametric_pulses(self):
        """Test converted qobj from ParametricInstruction."""
        instruction = Play(Gaussian(duration=25, sigma=15, amp=-0.5 + 0.2j), DriveChannel(0))
        qobj = PulseQobjInstruction(
            name='parametric_pulse',
            pulse_shape='gaussian',
            ch='d0',
            t0=0,
            parameters={'duration': 25, 'sigma': 15, 'amp': -0.5 + 0.2j})
        converted_instruction = self.converter(qobj)
        self.assertEqual(converted_instruction.start_time, 0)
        self.assertEqual(converted_instruction.duration, 25)
        self.assertEqual(converted_instruction.instructions[0][-1], instruction)

    def test_frame_change(self):
        """Test converted qobj from ShiftPhase."""
        qobj = PulseQobjInstruction(name='fc', ch='m0', t0=0, phase=0.1)
        converted_instruction = self.converter(qobj)

        instruction = ShiftPhase(0.1, MeasureChannel(0))
        self.assertEqual(converted_instruction.start_time, 0)
        self.assertEqual(converted_instruction.duration, 0)
        self.assertEqual(converted_instruction.instructions[0][-1], instruction)

    def test_set_phase(self):
        """Test converted qobj from SetPhase."""
        qobj = PulseQobjInstruction(name='setp', ch='m0', t0=0, phase=3.14)
        converted_instruction = self.converter(qobj)

        instruction = SetPhase(3.14, MeasureChannel(0))
        self.assertEqual(converted_instruction.start_time, 0)
        self.assertEqual(converted_instruction.duration, 0)
        self.assertEqual(converted_instruction.instructions[0][-1], instruction)

    def test_set_frequency(self):
        """Test converted qobj from SetFrequency."""
        instruction = SetFrequency(8.0e9, DriveChannel(0))

        qobj = PulseQobjInstruction(name='setf', ch='d0', t0=0, frequency=8.0)
        converted_instruction = self.converter(qobj)

        self.assertEqual(converted_instruction.start_time, 0)
        self.assertEqual(converted_instruction.duration, 0)
        self.assertEqual(converted_instruction.instructions[0][-1], instruction)
        self.assertTrue('frequency' in qobj.to_dict())

    def test_shift_frequency(self):
        """Test converted qobj from ShiftFrequency."""
        instruction = ShiftFrequency(8.0e9, DriveChannel(0))

        qobj = PulseQobjInstruction(name='shiftf', ch='d0', t0=0, frequency=8.0)
        converted_instruction = self.converter(qobj)

        self.assertEqual(converted_instruction.start_time, 0)
        self.assertEqual(converted_instruction.duration, 0)
        self.assertEqual(converted_instruction.instructions[0][-1], instruction)
        self.assertTrue('frequency' in qobj.to_dict())

    def test_delay(self):
        """Test converted qobj from Delay."""
        instruction = Delay(10, DriveChannel(0))

        qobj = PulseQobjInstruction(name='delay', ch='d0', t0=0, duration=10)
        converted_instruction = self.converter(qobj)

        self.assertTrue('delay' in qobj.to_dict().values())
        self.assertEqual(converted_instruction.duration, instruction.duration)
        self.assertEqual(converted_instruction.instructions[0][-1], instruction)

    def test_acquire(self):
        """Test converted qobj from Acquire."""
        schedule = Schedule()
        for i in range(self.num_qubits):
            schedule |= Acquire(10, AcquireChannel(i), MemorySlot(i), RegisterSlot(i),
                                kernel=Kernel(name='test_kern', test_params='test'),
                                discriminator=Discriminator(name='test_disc',
                                                            test_params=1.0))

        qobj = PulseQobjInstruction(name='acquire', t0=0, duration=10, qubits=[0, 1],
                                    memory_slot=[0, 1], register_slot=[0, 1],
                                    kernels=[QobjMeasurementOption(
                                        name='test_kern', params={'test_params': 'test'})],
                                    discriminators=[QobjMeasurementOption(
                                        name='test_disc', params={'test_params': 1.0})])
        converted_instruction = self.converter(qobj)

        self.assertEqual(converted_instruction.start_time, 0)
        self.assertEqual(converted_instruction.duration, 10)
        self.assertEqual(converted_instruction.instructions[0][-1].duration, 10)
        self.assertEqual(converted_instruction.instructions[0][-1].kernel.params,
                         {'test_params': 'test'})
        self.assertEqual(converted_instruction.instructions[1][-1].channel, AcquireChannel(1))

    def test_snapshot(self):
        """Test converted qobj from SnapShot."""
        instruction = Snapshot(label='label', snapshot_type='type')
        shifted = instruction << 10

        qobj = PulseQobjInstruction(name='snapshot', t0=10, label='label', type='type')
        converted_instruction = self.converter(qobj)

        self.assertEqual(converted_instruction.start_time, shifted.start_time)
        self.assertEqual(converted_instruction.duration, shifted.duration)
        self.assertEqual(converted_instruction.instructions[0][-1], instruction)

    def test_parameterized_frame_change(self):
        """Test converted qobj from ShiftPhase."""
        instruction = ShiftPhase(4., MeasureChannel(0))
        shifted = instruction << 10

        qobj = PulseQobjInstruction(name='fc', ch='m0', t0=10, phase='P1**2')
        converted_instruction = self.converter(qobj)

        self.assertIsInstance(converted_instruction, ParameterizedSchedule)

        evaluated_instruction = converted_instruction.bind_parameters(2.)

<<<<<<< HEAD
        self.assertEqual(evaluated_instruction.start_time, shifted.start_time)
        self.assertEqual(evaluated_instruction.duration, shifted.duration)
        self.assertEqual(evaluated_instruction.instructions[0][-1], instruction)
=======
        self.assertEqual(evaluated_instruction.timeslots, instruction.timeslots)
        self.assertEqual(evaluated_instruction.instructions[0][-1].command, cmd)

    def test_parameterized_persistent_value(self):
        """Test converted qobj from PersistentValueInstruction."""
        cmd = PersistentValue(value=0.5+0.j)
        instruction = cmd(ControlChannel(1)) << 10

        qobj = PulseQobjInstruction(name='pv', ch='u1', t0=10, val='P1*cos(np.pi*P2)')
        converted_instruction = self.converter(qobj)

        self.assertIsInstance(converted_instruction, ParameterizedSchedule)

        evaluated_instruction = converted_instruction.bind_parameters(P1=0.5, P2=0.)

        self.assertEqual(evaluated_instruction.timeslots, instruction.timeslots)
        self.assertEqual(evaluated_instruction.instructions[0][-1].command, cmd)

    def test_expression_sanitizer(self):
        """Test math expression sanitization."""

        self.assertFalse(_is_math_expr_safe('INSERT INTO students VALUES (?,?)'))
        self.assertFalse(_is_math_expr_safe('import math'))
        self.assertFalse(_is_math_expr_safe('complex'))
        self.assertFalse(_is_math_expr_safe('__import__("os").system("clear")'))
        self.assertFalse(_is_math_expr_safe('eval("()._" + "_class_" + "_._" +'
                                            ' "_bases_" + "_[0]")'))
        self.assertFalse(_is_math_expr_safe('2***2'))
        self.assertFalse(_is_math_expr_safe('avdfd*3'))
        self.assertFalse(_is_math_expr_safe('Cos(1+2)'))
        self.assertFalse(_is_math_expr_safe('hello'))
        self.assertFalse(_is_math_expr_safe('hello_world'))
        self.assertFalse(_is_math_expr_safe('1_2'))
        self.assertFalse(_is_math_expr_safe('2+-2'))
        self.assertFalse(_is_math_expr_safe('print(1.0)'))
        self.assertFalse(_is_math_expr_safe('1.1.1.1'))
        self.assertFalse(_is_math_expr_safe('abc.1'))

        self.assertTrue(_is_math_expr_safe('1+1*2*3.2+8*cos(1)**2'))
        self.assertTrue(_is_math_expr_safe('pi*2'))
        self.assertTrue(_is_math_expr_safe('-P1*cos(P2)'))
        self.assertTrue(_is_math_expr_safe('-P1*P2*P3'))
        self.assertTrue(_is_math_expr_safe('-P1'))
        self.assertTrue(_is_math_expr_safe('-1.*P1'))
        self.assertTrue(_is_math_expr_safe('-1.*P1*P2'))
        self.assertTrue(_is_math_expr_safe('-(P1)'))
>>>>>>> c9c6d46ca... Update expression math sanitization (#2376)


class TestLoConverter(QiskitTestCase):
    """LO converter tests."""

    def test_qubit_los(self):
        """Test qubit channel configuration."""
        user_lo_config = LoConfig({DriveChannel(0): 1.3e9})
        converter = LoConfigConverter(PulseQobjExperimentConfig,
                                      [1.2e9], [3.4e9], [(0., 5e9)], [(0., 5e9)])

        valid_qobj = PulseQobjExperimentConfig(qubit_lo_freq=[1.3])

        self.assertEqual(converter(user_lo_config), valid_qobj)

    def test_meas_los(self):
        """Test measurement channel configuration."""
        user_lo_config = LoConfig({MeasureChannel(0): 3.5e9})
        converter = LoConfigConverter(PulseQobjExperimentConfig,
                                      [1.2e9], [3.4e9], [(0., 5e9)], [(0., 5e9)])

        valid_qobj = PulseQobjExperimentConfig(meas_lo_freq=[3.5])

        self.assertEqual(converter(user_lo_config), valid_qobj)
