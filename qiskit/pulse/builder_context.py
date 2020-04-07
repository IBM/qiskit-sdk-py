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

"""Context based pulse programming interface.

Use the context builder interface to program pulse programs with assembly-like
syntax. For example::

.. code::
    from qiskit.circuit import QuantumCircuit
    from qiskit.pulse import pulse_lib, Schedule, Gaussian, DriveChannel
    from qiskit.test.mock import FakeOpenPulse2Q

    sched = Schedule()

    # This creates a PulseProgramBuilderContext(sched, backend=backend)
    # instance internally and wraps in a
    # dsl builder context
    with builder(sched, backend=backend):
      # create a pulse
      gaussian_pulse = pulse_lib.gaussian(10, 1.0, 2)
      # create a channel type
      d0 = DriveChannel(0)
      d1 = DriveChannel(1)
      # play a pulse at time=0
      play(d0, gaussian_pulse)
      # play another pulse directly after at t=10
      play(d0, gaussian_pulse)
      # The default scheduling behavior is to schedule pulse in parallel
      # across independent resources, for example
      # play the same pulse on a different channel at t=0
      play(d1, gaussian_pulse)

      # We also provide alignment contexts
      # if channels are not supplied defaults to all channels
      # this context starts at t=10 due to earlier pulses
      with sequential():
        play(d0, gaussian_pulse)
        # play another pulse after at t=20
        play(d1, gaussian_pulse)

        # we can also layer contexts as each instruction is contained in its
        # local scheduling context (block).
        # Scheduling contexts are layered, and the output of a child context is
        # a fixed scheduled block in its parent context.
        # starts at t=20
        with parallel():
          # start at t=20
          play(d0, gaussian_pulse)
          # start at t=20
          play(d1, gaussian_pulse)
        # context ends at t=30

      # We also support different alignment contexts
      # Default is
      # with left():

      # all pulse instructions occur as late as possible
      with right_align():
        set_phase(d1, math.pi)
        # starts at t=30
        delay(d0, 100)
        # ends at t=130

        # starts at t=120
        play(d1, gaussian_pulse)
        # ends at t=130

      # acquire a qubit
      acquire(0, ClassicalRegister(0))
      # maps to
      #acquire(AcquireChannel(0), ClassicalRegister(0))

      # We will also support a variety of helper functions for common operations

      # measure all qubits
      # Note that as this DSL is pure Python
      # any Python code is accepted within contexts
      for i in range(n_qubits):
        measure(i, ClassicalRegister(i))

      # delay on a qubit
      # this requires knowledge of which channels belong to which qubits
      delay(0, 100)

      # insert a quantum circuit. This functions by behind the scenes calling
      # the scheduler on the given quantum circuit to output a new schedule
      # NOTE: assumes quantum registers correspond to physical qubit indices
      qc = QuantumCircuit(2, 2)
      qc.cx(0, 1)
      call(qc)
      # We will also support a small set of standard gates
      u3(0, 0, np.pi, 0)
      cx(0, 1)


      # It is also be possible to call a preexisting
      # schedule constructed with another
      # NOTE: once internals are fleshed out, Schedule may not be the default class
      tmp_sched = Schedule()
      tmp_sched += Play(dc0, gaussian_pulse)
      call(tmp_sched)

      # We also support:

      # frequency instructions
      set_frequency(dc0, 5.0e9)
      shift_frequency(dc0, 0.1e9)

      # phase instructions
      set_phase(dc0, math.pi)
      shift_phase(dc0, 0.1)

      # offset contexts
      with phase_offset(d0, math.pi):
        play(d0, gaussian_pulse)

      with frequency_offset(d0, 0.1e9):
        play(d0, gaussian_pulse)
"""
import collections
import contextvars
import functools
import numpy as np
from contextlib import contextmanager
from typing import Any, Callable, Dict, Mapping, Set, Tuple, Union

import qiskit.extensions.standard as gates
import qiskit.circuit as circuit
import qiskit.pulse.channels as channels
import qiskit.pulse.configuration as configuration
import qiskit.pulse.exceptions as exceptions
import qiskit.pulse.instructions as instructions
import qiskit.pulse.macros as macros
import qiskit.pulse.pulse_lib as pulse_lib
import qiskit.pulse.transforms as transforms
from qiskit.pulse.schedule import Schedule


#: contextvars.ContextVar[BuilderContext]: current builder
BUILDER_CONTEXT = contextvars.ContextVar("backend")


def _schedule_lazy_circuit_before(fn):
    """Decorator thats schedules and calls the current circuit executing
    the decorated function."""
    @functools.wraps(fn)
    def wrapper(self, *args, **kwargs):
        self.schedule_lazy_circuit()
        return fn(self, *args, **kwargs)
    return wrapper


class _PulseBuilder():
    """Builder context class."""

    def __init__(self,
                 backend, entry_block: Schedule = None,
                 transpiler_settings: Mapping = None,
                 circuit_scheduler_settings: Mapping = None):
        """Initialize builder context.

        This is not a public class

        Args:
            backend (BaseBackend):
        """
        #: BaseBackend: Backend instance for context builder.
        self.backend = backend

        #: pulse.Schedule: Current current schedule of BuilderContext.
        self._block = None

        #: QuantumCircuit: Lazily constructed quantum circuit
        self._lazy_circuit = self.new_circuit()

        if transpiler_settings is None:
            transpiler_settings = {}
        self._transpiler_settings = transpiler_settings

        if circuit_scheduler_settings is None:
            circuit_scheduler_settings = {}
        self._circuit_scheduler_settings = {}

        if entry_block is None:
            entry_block = Schedule()
        # pulse.Schedule: Root program block
        self._entry_block = entry_block

        self.set_current_block(Schedule())

    def __enter__(self):
        """Enter Builder Context."""
        self._backend_ctx_token = BUILDER_CONTEXT.set(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit Builder Context."""
        self.compile()
        BUILDER_CONTEXT.reset(self._backend_ctx_token)

    @property
    def block(self) -> Schedule:
        """The current block."""
        return self._block

    @property
    def num_qubits(self):
        """Get the number of qubits in the backend."""
        return self.backend.configuration().n_qubits

    @property
    def transpiler_settings(self) -> Mapping:
        return self._transpiler_settings

    @transpiler_settings.setter
    def transpiler_settings(self, settings: Mapping):
        self.schedule_lazy_circuit()
        self._transpiler_settings = settings

    @property
    def circuit_scheduler_settings(self) -> Mapping:
        return self._circuit_scheduler_settings

    @circuit_scheduler_settings.setter
    def circuit_scheduler_settings(self, settings: Mapping):
        self.schedule_lazy_circuit()
        self._circuit_scheduler_settings = settings

    def compile(self) -> Schedule:
        """Compile built program."""
        # Not much happens because we currently compile as we build.
        # This should be offloaded to a true compilation module
        # once we define a more sophisticated IR.
        program = self._entry_block.append(self.block, mutate=True)
        self.set_current_block(Schedule())
        return program

    @_schedule_lazy_circuit_before
    def set_current_block(self, block: Schedule):
        """Set the current block."""
        assert isinstance(block, Schedule)
        self._block = block

    @_schedule_lazy_circuit_before
    def append_block(self, block: Schedule):
        """Add a block to the current current block."""
        self.block.append(block, mutate=True)

    @_schedule_lazy_circuit_before
    def append_instruction(self, instruction: instructions.Instruction):
        """Add an instruction to the current current block."""
        self.block.append(instruction, mutate=True)

    def call_schedule(self, schedule: Schedule):
        """Call a schedule."""
        self.append_block(schedule)

    def new_circuit(self):
        """Create a new circuit for scheduling."""
        return circuit.QuantumCircuit(self.num_qubits)

    def schedule_lazy_circuit(self):
        """Call a QuantumCircuit."""
        if len(self._lazy_circuit):
            import qiskit.compiler as compiler

            lazy_circuit = self._lazy_circuit
            # reset lazy circuit
            self._lazy_circuit = self.new_circuit()
            circuit = compiler.transpile(lazy_circuit,
                                         self.backend,
                                         **self.transpiler_settings)
            sched = compiler.schedule(circuit,
                                      self.backend,
                                      **self.circuit_scheduler_settings)
            self.call_schedule(sched)

    def call_circuit(self, circuit: circuit.QuantumCircuit, lazy=True):
        self._lazy_circuit.extend(circuit)
        if not lazy:
            self.schedule_lazy_circuit()

    def call_gate(self,
                  gate: circuit.Gate, qubits: Tuple[int, ...],
                  lazy=True):
        """Lower a circuit gate to pulse instruction."""
        try:
            iter(qubits)
        except TypeError:
            qubits = (qubits,)

        qc = circuit.QuantumCircuit(self.num_qubits)
        qc.append(gate, qargs=qubits)
        self.call_circuit(qc)


def build(backend, schedule):
    """
    A context manager for the pulse DSL.

    Args:
        backend: a qiskit backend
        schedule: a *mutable* pulse Schedule
    """
    return _PulseBuilder(backend, schedule)


# Builder Utilities ############################################################
def _current_builder() -> _PulseBuilder:
    """Get the current builder in the current context."""
    return BUILDER_CONTEXT.get()


def current_backend():
    """Get the backend of the current context.

    Returns:
        BaseBackend
    """
    return _current_builder().backend


def append_block(block: Schedule):
    """Append a block to the current block. The current block is not changed."""
    _current_builder().append_block(block)


def append_instruction(instruction: instructions.Instruction):
    """Append an instruction to current context."""
    _current_builder().append_instruction(instruction)


def qubit_channels(qubit: int) -> Set[channels.Channel]:
    """
    Returns the 'typical' set of channels associated with a qubit.
    """
    raise NotImplementedError('Qubit channels is not yet implemented.')


def current_transpiler_settings() -> Dict[str, Any]:
    """Return current context transpiler settings."""
    return _current_builder().transpiler_settings


def current_circuit_scheduler_settings() -> Dict[str, Any]:
    """Return current context circuit scheduler settings."""
    return _current_builder().circuit_scheduler_settings


# Contexts ###########################################################
def _transform_context(transform: Callable,
                       **decorator_kwargs) -> Callable:
    """A tranform context.

    Args:
        transform: Transform to decorate as context.
    """
    @functools.wraps(transform)
    def wrap(fn):
        @contextmanager
        def wrapped_transform(*args, **kwargs):
            builder = _current_builder()
            current_block = builder.block
            transform_block = Schedule()
            builder.set_current_block(transform_block)
            try:
                yield
            finally:
                transformed_block = transform(transform_block,
                                              *args,
                                              **kwargs,
                                              **decorator_kwargs)
                builder.set_current_block(current_block)
                builder.append_block(transformed_block)

        return wrapped_transform

    return wrap


@_transform_context(transforms.parallelize)
def parallel():
    """Parallel transform builder context."""


@_transform_context(transforms.sequentialize)
def sequential():
    """Sequential transform builder context."""


@_transform_context(transforms.left_align)
def left_align():
    """Left align transform builder context."""


@_transform_context(transforms.right_align)
def right_align():
    """Right align transform builder context."""


@_transform_context(transforms.group)
def group():
    """Group the instructions within this context fixing their relative timing."""


@_transform_context(transforms.flatten)
def flatten():
    """Flatten any grouped instructions upon exiting context.

    .. warning:: This will remove any ``barrier`` you have set.
    """


@_transform_context(transforms.pad, mutate=True)
def pad(*channels):
    """Pad all availale timeslots with delays upon exiting context."""


@contextmanager
def transpiler_settings(**settings):
    """Set the current current tranpiler settings for this context."""
    builder = _current_builder()
    current_transpiler_settings = builder.transpiler_settings
    builder.transpiler_settings = collections.ChainMap(
        settings, current_transpiler_settings)
    try:
        yield
    finally:
        builder.transpiler_settings = current_transpiler_settings


@contextmanager
def circuit_scheduler_settings(**settings):
    """Set the current current circuit scheduling settings for this context."""
    builder = _current_builder()
    current_circuit_scheduler_settings = builder.circuit_scheduler_settings
    builder.circuit_scheduler_settings = collections.ChainMap(
        settings, current_circuit_scheduler_settings)
    try:
        yield
    finally:
        builder.circuit_scheduler_settings = current_circuit_scheduler_settings


# Base Instructions ############################################################
def delay(channel: channels.Channel, duration: int):
    """Delay on a ``channel`` for a ``duration``."""
    append_instruction(instructions.Delay(duration, channel))


def play(channel: channels.PulseChannel,
         pulse: Union[pulse_lib.Pulse, np.ndarray]):
    """Play a ``pulse`` on a ``channel``."""

    if not isinstance(pulse, pulse_lib.Pulse):
        pulse = pulse_lib.SamplePulse(pulse)

    append_instruction(instructions.Play(pulse, channel))


def acquire(channel: Union[channels.AcquireChannel, int],
            register: Union[channels.RegisterSlot, channels.MemorySlot],
            duration: int,
            **metadata: Union[configuration.Kernel, configuration.Discriminator]):
    """Acquire for a ``duration`` on a ``channel`` and store the result
    in a ``register``."""
    if isinstance(register, channels.MemorySlot):
        append_instruction(instructions.Acquire(
            duration, channel, mem_slot=register, **metadata))
    elif isinstance(register, channels.RegisterSlot):
        append_instruction(instructions.Acquire(
            duration, channel, reg_slot=register, **metadata))
    else:
        raise exceptions.PulseError(
            'Register of type: "{}" is not supported'.format(type(register)))


def set_frequency(channel: channels.PulseChannel, frequency: float):
    """Set the ``frequency`` of a pulse ``channel``."""
    append_instruction(instructions.SetFrequency(frequency, channel))


def shift_frequency(channel: channels.PulseChannel, frequency: float):
    """Shift the ``frequency`` of a pulse ``channel``."""
    raise NotImplementedError()


def set_phase(channel: channels.PulseChannel, phase: float):
    """Set the ``phase`` of a pulse ``channel``."""
    raise NotImplementedError()


def shift_phase(channel: channels.PulseChannel, phase: float):
    """Shift the ``phase`` of a pulse ``channel``."""
    append_instruction(instructions.ShiftPhase(phase, channel))


def barrier(*channels_or_qubits: Union[channels.Channel, int]):
    """Barrier a set of channels and qubits.

    Args:
        channels_or_qubits: Channels or qubits to barrier.

    .. todo:: Implement this as a proper instruction.
    """
    channels = set()
    for channel_or_qubit in channels_or_qubits:
        if isinstance(channel_or_qubit, int):
            channels += qubit_channels(channel_or_qubit)
        elif isinstance(channel_or_qubit, channels.Channel):
            channels += channel_or_qubit
        else:
            raise exceptions.PulseError(
                '{} is not a "Channel" or '
                'qubit (integer).'.format(channel_or_qubit))
    raise NotImplementedError('Barrier has not yet been implemented.')


def snapshot(label: str, snapshot_type: str = 'statevector'):
    """Simulator snapshot."""
    append_instruction(
        instructions.Snapshot(label, snapshot_type=snapshot_type))


def call_schedule(schedule: Schedule):
    """Call a pulse ``schedule`` in the builder context."""
    _current_builder().call_schedule(schedule)


def call_circuit(circuit: circuit.QuantumCircuit, lazy=True):
    """Call a quantum ``circuit`` in the builder context."""
    _current_builder().call_circuit(circuit, lazy=True)


def call(target: Union[circuit.QuantumCircuit, Schedule]):
    """Call the ``target`` within this builder context."""
    if isinstance(target, circuit.QuantumCircuit):
        call_circuit(target)
    elif isinstance(target, Schedule):
        call_schedule(target)
    raise exceptions.PulseError(
        'Target of type "{}" is not supported.'.format(type(target)))


# Macros #######################################################################
def measure(qubit: int):
    backend = current_backend()
    call_schedule(macros.measure(qubits=[qubit],
                  inst_map=backend.defaults().instruction_schedule_map,
                  meas_map=backend.configuration().meas_map))


def delay_qubit(qubit: int, duration: int):
    with parallel(), group():
        for channel in qubit_channels(qubit):
            delay(channel, duration)


# Gate instructions ############################################################
def call_gate(gate: circuit.Gate, qubits: Tuple[int, ...]):
    """Lower a circuit gate to pulse instruction."""
    _current_builder().call_gate(gate, qubits)


def cx(control: int, target: int):
    call_gate(gates.CnotGate(), control, target)


def u1(qubit: int, theta: float):
    call_gate(gates.U1Gate(theta), qubit)


def u2(qubit: int, phi: float, lam: float):
    call_gate(gates.U2Gate(phi, lam), qubit)


def u3(qubit: int, theta: float, phi: float, lam: float):
    call_gate(gates.U3Gate(phi, lam), qubit)


def x(qubit: int):
    call_gate(gates.XGate(), qubit)
