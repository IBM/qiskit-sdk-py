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


"""Tests pulse function samplers."""

import numpy as np

from qiskit.test import QiskitTestCase
from qiskit.pulse import library
from qiskit.pulse.exceptions import PulseError
import qiskit.pulse.library.samplers as samplers


def linear(times: np.ndarray, m: float, b: float = 0.1) -> np.ndarray:
    """Linear test function
    Args:
        times: Input times.
        m: Slope.
        b: Intercept
    Returns:
        np.ndarray
    """
    return m*times+b


class TestSampler(QiskitTestCase):
    """Test continuous pulse function samplers."""

    def test_left_sampler(self):
        """Test left sampler."""
        m = 0.1
        b = 0.1
        duration = 2
        left_linear_pulse_fun = samplers.left(linear)
        reference = np.array([0.1, 0.2], dtype=np.complex)

        pulse = left_linear_pulse_fun(duration, m=m, b=b)
        self.assertIsInstance(pulse, library.Waveform)
        np.testing.assert_array_almost_equal(pulse.samples, reference)

    def test_right_sampler(self):
        """Test right sampler."""
        m = 0.1
        b = 0.1
        duration = 2
        right_linear_pulse_fun = samplers.right(linear)
        reference = np.array([0.2, 0.3], dtype=np.complex)

        pulse = right_linear_pulse_fun(duration, m=m, b=b)
        self.assertIsInstance(pulse, library.Waveform)
        np.testing.assert_array_almost_equal(pulse.samples, reference)

    def test_midpoint_sampler(self):
        """Test midpoint sampler."""
        m = 0.1
        b = 0.1
        duration = 2
        midpoint_linear_pulse_fun = samplers.midpoint(linear)
        reference = np.array([0.15, 0.25], dtype=np.complex)

        pulse = midpoint_linear_pulse_fun(duration, m=m, b=b)
        self.assertIsInstance(pulse, library.Waveform)
        np.testing.assert_array_almost_equal(pulse.samples, reference)

    def test_sampler_name(self):
        """Test that sampler setting of pulse name works."""
        m = 0.1
        b = 0.1
        duration = 2
        left_linear_pulse_fun = samplers.left(linear)

        pulse = left_linear_pulse_fun(duration, m=m, b=b, name='test')
        self.assertIsInstance(pulse, library.Waveform)
        self.assertEqual(pulse.name, 'test')

    def test_default_arg_sampler(self):
        """Test that default arguments work with sampler."""
        m = 0.1
        duration = 2
        left_linear_pulse_fun = samplers.left(linear)
        reference = np.array([0.1, 0.2], dtype=np.complex)

        pulse = left_linear_pulse_fun(duration, m=m)
        self.assertIsInstance(pulse, library.Waveform)
        np.testing.assert_array_almost_equal(pulse.samples, reference)

    def test_samplers_with_non_integer_float_duration(self):
        """Test samplers with float type duration."""
        m = 0.1
        b = 0.1
        duration = 2.01

        # right sampler
        right_linear_pulse_fun = samplers.right(linear)
        with self.assertRaises(PulseError):
            right_linear_pulse_fun(duration, m=m, b=b)

        # left sampler
        left_linear_pulse_fun = samplers.left(linear)
        with self.assertRaises(PulseError):
            left_linear_pulse_fun(duration, m=m, b=b)

        # midpoint sampler
        midpoint_linear_pulse_fun = samplers.midpoint(linear)
        with self.assertRaises(PulseError):
            midpoint_linear_pulse_fun(duration, m=m, b=b)

    def test_samplers_with_integer_float_duration(self):
        """Test samplers with float type duration."""
        m = 0.1
        b = 0.1
        duration = 2.00

        # right sampler
        right_linear_pulse_fun = samplers.right(linear)
        # no error
        right_linear_pulse_fun(duration, m=m, b=b)

        # left sampler
        left_linear_pulse_fun = samplers.left(linear)
        # no error
        left_linear_pulse_fun(duration, m=m, b=b)

        # midpoint sampler
        midpoint_linear_pulse_fun = samplers.midpoint(linear)
        # no error
        midpoint_linear_pulse_fun(duration, m=m, b=b)
