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

"""Parametric waveforms module. These are pulses which are described by a specified
parameterization.

If a backend supports parametric pulses, it will have the attribute
`backend.configuration().parametric_pulses`, which is a list of supported pulse shapes, such as
`['gaussian', 'gaussian_square', 'drag']`. A Pulse Schedule, using parametric pulses, which is
assembled for a backend which supports those pulses, will result in a Qobj which is dramatically
smaller than one which uses Waveforms.

This module can easily be extended to describe more pulse shapes. The new class should:
  - have a descriptive name
  - be a well known and/or well described formula (include the formula in the class docstring)
  - take some parameters (at least `duration`) and validate them, if necessary
  - implement a ``get_sample_pulse`` method which returns a corresponding Waveform in the case that
    it is assembled for a backend which does not support it. Ends are zeroed to avoid steep jumps at
    pulse edges. By default, the ends are defined such that ``f(-1), f(duration+1) = 0``.

The new pulse must then be registered by the assembler in
`qiskit/qobj/converters/pulse_instruction.py:ParametricPulseShapes`
by following the existing pattern:

    class ParametricPulseShapes(Enum):
        gaussian = pulse_lib.Gaussian
        ...
        new_supported_pulse_name = pulse_lib.YourPulseWaveformClass
"""
import warnings
from abc import abstractmethod
from typing import Any, Callable, Dict, Optional, Union
import math
import numpy as np

from qiskit.circuit.parameterexpression import ParameterExpression, ParameterValueType
from qiskit.pulse.exceptions import PulseError
from qiskit.pulse.library import continuous
from qiskit.pulse.library.discrete import gaussian, gaussian_square, drag, constant
from qiskit.pulse.library.pulse import Pulse
from qiskit.pulse.library.waveform import Waveform


class ParametricPulse(Pulse):
    """The abstract superclass for parametric pulses."""

    @abstractmethod
    def __init__(self, duration: int, name: Optional[str] = None):
        """Create a parametric pulse and validate the input parameters.

        Args:
            duration: Pulse length in terms of the the sampling period `dt`.
            name: Display name for this pulse envelope.
        """
        super().__init__(duration=duration, name=name)
        self.validate_parameters()

    @abstractmethod
    def get_waveform(self) -> Waveform:
        """Return a Waveform with samples filled according to the formula that the pulse
        represents and the parameter values it contains.
        """
        raise NotImplementedError

    def get_sample_pulse(self) -> Waveform:
        """Deprecated."""
        warnings.warn('`get_sample_pulse` has been deprecated. '
                      ' Use `get_waveform` instead.', DeprecationWarning)
        return self.get_waveform()

    @abstractmethod
    def validate_parameters(self) -> None:
        """
        Validate parameters.

        Raises:
            PulseError: If the parameters passed are not valid.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """Return a dictionary containing the pulse's parameters."""
        pass

    def is_parameterized(self) -> bool:
        return any(_is_parameterized(val) for val in self.parameters.values())

    def assign(self, parameter: ParameterExpression,
               value: ParameterValueType) -> 'ParametricPulse':
        """Assign one parameter to a value, which can either be numeric or another parameter
        expression.
        """
        return self.assign_parameters({parameter: value})

    def assign_parameters(self,
                          value_dict: Dict[ParameterExpression, ParameterValueType]
                          ) -> 'ParametricPulse':
        """Return a new ParametricPulse with parameters assigned.

        Args:
            value_dict: A mapping from Parameters to either numeric values or another
                Parameter expression.

        Returns:
            New pulse with updated parameters.
        """
        if not self.is_parameterized():
            return self

        new_parameters = {}
        for op, op_value in self.parameters.items():
            for parameter, value in value_dict.items():
                if _is_parameterized(op_value) and parameter in op_value.parameters:
                    op_value = op_value.assign(parameter, value)
                    try:
                        # TODO: ParameterExpression doesn't support complex values
                        op_value = float(op_value)
                    except TypeError:
                        # It's alright if the value is still parameterized
                        pass
                new_parameters[op] = op_value
        return type(self)(**new_parameters)

    def draw(self, dt: float = 1,
             style=None,
             filename: Optional[str] = None,
             interp_method: Optional[Callable] = None,
             scale: float = 1, interactive: bool = False,
             draw_title: bool = False):
        """Plot the pulse.

        Args:
            dt: Time interval of samples.
            style (Optional[PulseStyle]): A style sheet to configure plot appearance
            filename: Name required to save pulse image
            interp_method: A function for interpolation
            scale: Relative visual scaling of waveform amplitudes
            interactive: When set true show the circuit in a new window
                (this depends on the matplotlib backend being used supporting this)
            draw_title: Add a title to the plot when set to ``True``.

        Returns:
            matplotlib.figure: A matplotlib figure object of the pulse envelope
        """
        return self.get_waveform().draw(dt=dt, style=style, filename=filename,
                                        interp_method=interp_method, scale=scale,
                                        interactive=interactive, draw_title=draw_title)

    def __eq__(self, other: Pulse) -> bool:
        return super().__eq__(other) and self.parameters == other.parameters

    def __hash__(self) -> int:
        return hash(self.parameters[k] for k in sorted(self.parameters))


class Gaussian(ParametricPulse):
    """A truncated pulse envelope shaped according to the Gaussian function whose mean is centered
    at the center of the pulse (duration / 2):

    .. math::

        f(x) = amp * exp( -(1/2) * (x - duration/2)^2 / sigma^2) )  ,  0 <= x < duration
    """

    def __init__(self,
                 duration: int,
                 amp: Union[complex, ParameterExpression],
                 sigma: Union[float, ParameterExpression],
                 name: Optional[str] = None):
        """Initialize the gaussian pulse.

        Args:
            duration: Pulse length in terms of the the sampling period `dt`.
            amp: The amplitude of the Gaussian envelope.
            sigma: A measure of how wide or narrow the Gaussian peak is; described mathematically
                   in the class docstring.
            name: Display name for this pulse envelope.
        """
        if not _is_parameterized(amp):
            amp = complex(amp)
        self._amp = amp
        self._sigma = sigma
        super().__init__(duration=duration, name=name)

    @property
    def amp(self) -> Union[complex, ParameterExpression]:
        """The Gaussian amplitude."""
        return self._amp

    @property
    def sigma(self) -> Union[float, ParameterExpression]:
        """The Gaussian standard deviation of the pulse width."""
        return self._sigma

    def get_waveform(self) -> Waveform:
        return gaussian(duration=self.duration, amp=self.amp,
                        sigma=self.sigma, zero_ends=True)

    def validate_parameters(self) -> None:
        if not _is_parameterized(self.amp) and abs(self.amp) > 1.:
            raise PulseError("The amplitude norm must be <= 1, "
                             "found: {}".format(abs(self.amp)))
        if not _is_parameterized(self.sigma) and self.sigma <= 0:
            raise PulseError("Sigma must be greater than 0.")

    @property
    def parameters(self) -> Dict[str, Any]:
        return {"duration": self.duration, "amp": self.amp, "sigma": self.sigma}

    def __repr__(self) -> str:
        return "{}(duration={}, amp={}, sigma={}{})" \
               "".format(self.__class__.__name__, self.duration, self.amp, self.sigma,
                         ", name='{}'".format(self.name) if self.name is not None else "")


class GaussianSquare(ParametricPulse):
    """A square pulse with a Gaussian shaped risefall on either side:

    .. math::

        risefall = (duration - width) / 2

        0 <= x < risefall

        f(x) = amp * exp( -(1/2) * (x - risefall/2)^2 / sigma^2) )

        risefall <= x < risefall + width

        f(x) = amp

        risefall + width <= x < duration

        f(x) = amp * exp( -(1/2) * (x - (risefall + width)/2)^2 / sigma^2) )
    """

    def __init__(self,
                 duration: int,
                 amp: Union[complex, ParameterExpression],
                 sigma: Union[float, ParameterExpression],
                 width: Union[float, ParameterExpression],
                 name: Optional[str] = None):
        """Initialize the gaussian square pulse.

        Args:
            duration: Pulse length in terms of the the sampling period `dt`.
            amp: The amplitude of the Gaussian and of the square pulse.
            sigma: A measure of how wide or narrow the Gaussian risefall is; see the class
                   docstring for more details.
            width: The duration of the embedded square pulse.
            name: Display name for this pulse envelope.
        """
        if not _is_parameterized(amp):
            amp = complex(amp)
        self._amp = amp
        self._sigma = sigma
        self._width = width
        super().__init__(duration=duration, name=name)

    @property
    def amp(self) -> Union[complex, ParameterExpression]:
        """The Gaussian amplitude."""
        return self._amp

    @property
    def sigma(self) -> Union[float, ParameterExpression]:
        """The Gaussian standard deviation of the pulse width."""
        return self._sigma

    @property
    def width(self) -> Union[float, ParameterExpression]:
        """The width of the square portion of the pulse."""
        return self._width

    def get_waveform(self) -> Waveform:
        return gaussian_square(duration=self.duration, amp=self.amp,
                               width=self.width, sigma=self.sigma,
                               zero_ends=True)

    def validate_parameters(self) -> None:
        if not _is_parameterized(self.amp) and abs(self.amp) > 1.:
            raise PulseError("The amplitude norm must be <= 1, "
                             "found: {}".format(abs(self.amp)))
        if not _is_parameterized(self.sigma) and self.sigma <= 0:
            raise PulseError("Sigma must be greater than 0.")
        if not _is_parameterized(self.width) and self.width < 0 or self.width >= self.duration:
            raise PulseError("The pulse width must be at least 0 and less than its duration.")

    @property
    def parameters(self) -> Dict[str, Any]:
        return {"duration": self.duration, "amp": self.amp, "sigma": self.sigma,
                "width": self.width}

    def __repr__(self) -> str:
        return "{}(duration={}, amp={}, sigma={}, width={}{})" \
               "".format(self.__class__.__name__, self.duration, self.amp, self.sigma, self.width,
                         ", name='{}'".format(self.name) if self.name is not None else "")


class Drag(ParametricPulse):
    r"""The Derivative Removal by Adiabatic Gate (DRAG) pulse is a standard Gaussian pulse
    with an additional Gaussian derivative component. It is designed to reduce the frequency
    spectrum of a normal gaussian pulse near the :math:`|1\rangle` - :math:`|2\rangle` transition,
    reducing the chance of leakage to the :math:`|2\rangle` state.

    .. math::

        f(x) = Gaussian + 1j * beta * d/dx [Gaussian]
             = Gaussian + 1j * beta * (-(x - duration/2) / sigma^2) [Gaussian]

    where 'Gaussian' is:

    .. math::

        Gaussian(x, amp, sigma) = amp * exp( -(1/2) * (x - duration/2)^2 / sigma^2) )

    References:
        1. |citation1|_

        .. _citation1: https://link.aps.org/doi/10.1103/PhysRevA.83.012308

        .. |citation1| replace:: *Gambetta, J. M., Motzoi, F., Merkel, S. T. & Wilhelm, F. K.
           Analytic control methods for high-fidelity unitary operations
           in a weakly nonlinear oscillator. Phys. Rev. A 83, 012308 (2011).*

        2. |citation2|_

        .. _citation2: https://link.aps.org/doi/10.1103/PhysRevLett.103.110501

        .. |citation2| replace:: *F. Motzoi, J. M. Gambetta, P. Rebentrost, and F. K. Wilhelm
           Phys. Rev. Lett. 103, 110501 – Published 8 September 2009.*
    """

    def __init__(self,
                 duration: int,
                 amp: Union[complex, ParameterExpression],
                 sigma: Union[float, ParameterExpression],
                 beta: Union[float, ParameterExpression],
                 name: Optional[str] = None):
        """Initialize the drag pulse.

        Args:
            duration: Pulse length in terms of the the sampling period `dt`.
            amp: The amplitude of the Drag envelope.
            sigma: A measure of how wide or narrow the Gaussian peak is; described mathematically
                   in the class docstring.
            beta: The correction amplitude.
            name: Display name for this pulse envelope.
        """
        if not _is_parameterized(amp):
            amp = complex(amp)
        self._amp = amp
        self._sigma = sigma
        self._beta = beta
        super().__init__(duration=duration, name=name)

    @property
    def amp(self) -> Union[complex, ParameterExpression]:
        """The Gaussian amplitude."""
        return self._amp

    @property
    def sigma(self) -> Union[float, ParameterExpression]:
        """The Gaussian standard deviation of the pulse width."""
        return self._sigma

    @property
    def beta(self) -> Union[float, ParameterExpression]:
        """The weighing factor for the Gaussian derivative component of the waveform."""
        return self._beta

    def get_waveform(self) -> Waveform:
        return drag(duration=self.duration, amp=self.amp, sigma=self.sigma,
                    beta=self.beta, zero_ends=True)

    def validate_parameters(self) -> None:
        if not _is_parameterized(self.amp) and abs(self.amp) > 1.:
            raise PulseError("The amplitude norm must be <= 1, "
                             "found: {}".format(abs(self.amp)))
        if not _is_parameterized(self.sigma) and self.sigma <= 0:
            raise PulseError("Sigma must be greater than 0.")
        if not _is_parameterized(self.beta) and isinstance(self.beta, complex):
            raise PulseError("Beta must be real.")
        # Check if beta is too large: the amplitude norm must be <=1 for all points
        if (not _is_parameterized(self.beta) and not _is_parameterized(self.sigma)
                and self.beta > self.sigma):
            # If beta <= sigma, then the maximum amplitude is at duration / 2, which is
            # already constrainted by self.amp <= 1

            # 1. Find the first maxima associated with the beta * d/dx gaussian term
            #    This eq is derived from solving for the roots of the norm of the drag function.
            #    There is a second maxima mirrored around the center of the pulse with the same
            #    norm as the first, so checking the value at the first x maxima is sufficient.
            argmax_x = (self.duration / 2
                        - (self.sigma / self.beta) * math.sqrt(self.beta ** 2 - self.sigma ** 2))
            if argmax_x < 0:
                # If the max point is out of range, either end of the pulse will do
                argmax_x = 0

            # 2. Find the value at that maximum
            max_val = continuous.drag(np.array(argmax_x), sigma=self.sigma,
                                      beta=self.beta, amp=self.amp, center=self.duration / 2)
            if abs(max_val) > 1.:
                raise PulseError("Beta is too large; pulse amplitude norm exceeds 1.")

    @property
    def parameters(self) -> Dict[str, Any]:
        return {"duration": self.duration, "amp": self.amp, "sigma": self.sigma,
                "beta": self.beta}

    def __repr__(self) -> str:
        return "{}(duration={}, amp={}, sigma={}, beta={}{})" \
               "".format(self.__class__.__name__, self.duration, self.amp, self.sigma, self.beta,
                         ", name='{}'".format(self.name) if self.name is not None else "")


class Constant(ParametricPulse):
    """
    A simple constant pulse, with an amplitude value and a duration:

    .. math::

        f(x) = amp    ,  0 <= x < duration
        f(x) = 0      ,  elsewhere
    """

    def __init__(self,
                 duration: int,
                 amp: Union[complex, ParameterExpression],
                 name: Optional[str] = None):
        """
        Initialize the constant-valued pulse.

        Args:
            duration: Pulse length in terms of the the sampling period `dt`.
            amp: The amplitude of the constant square pulse.
            name: Display name for this pulse envelope.
        """
        if not _is_parameterized(amp):
            amp = complex(amp)
        self._amp = amp
        super().__init__(duration=duration, name=name)

    @property
    def amp(self) -> Union[complex, ParameterExpression]:
        """The constant value amplitude."""
        return self._amp

    def get_waveform(self) -> Waveform:
        return constant(duration=self.duration, amp=self.amp)

    def validate_parameters(self) -> None:
        if not _is_parameterized(self.amp) and abs(self.amp) > 1.:
            raise PulseError("The amplitude norm must be <= 1, "
                             "found: {}".format(abs(self.amp)))

    @property
    def parameters(self) -> Dict[str, Any]:
        return {"duration": self.duration, "amp": self.amp}

    def __repr__(self) -> str:
        return "{}(duration={}, amp={}{})" \
               "".format(self.__class__.__name__, self.duration, self.amp,
                         ", name='{}'".format(self.name) if self.name is not None else "")


class ConstantPulse(Constant):
    """
    Deprecated. A simple constant pulse, with an amplitude value and a duration:

    .. math::

        f(x) = amp    ,  0 <= x < duration
        f(x) = 0      ,  elsewhere
    """

    def __init__(self,
                 duration: int,
                 amp: Union[complex, ParameterExpression],
                 name: Optional[str] = None):
        """
        Initialize the constant-valued pulse.

        Args:
            duration: Pulse length in terms of the the sampling period `dt`.
            amp: The amplitude of the constant square pulse.
            name: Display name for this pulse envelope.
        """
        super().__init__(duration, amp, name)
        warnings.warn("The ConstantPulse is deprecated. Use Constant instead", DeprecationWarning)


def _is_parameterized(value: Any) -> bool:
    """Shorthand for a frequently checked predicate. ParameterExpressions cannot be
    validated until they are numerically assigned.
    """
    return isinstance(value, ParameterExpression)
