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
      with align_sequential():
        play(d0, gaussian_pulse)
        # play another pulse after at t=20
        play(d1, gaussian_pulse)

        # we can also layer contexts as each instruction is contained in its
        # local scheduling context (block).
        # Scheduling contexts are layered, and the output of a child context is
        # a fixed scheduled block in its parent context.
        # starts at t=20
        with align_left():
          # start at t=20
          play(d0, gaussian_pulse)
          # start at t=20
          play(d1, gaussian_pulse)
        # context ends at t=30

      # We also support different alignment contexts
      # Default is
      # with left():

      # all pulse instructions occur as late as possible
      with align_right():
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
import itertools
from contextlib import contextmanager
from typing import (Any, Callable, ContextManager, Dict,
                    Iterable, Mapping, Set, Tuple, TypeVar,
                    Union)

import numpy as np

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
BUILDER_CONTEXTVAR = contextvars.ContextVar("backend")

T = TypeVar('T')  # pylint: disable=invalid-name
def _compile_lazy_circuit_before(function: Callable[..., T]) -> Callable[..., T]:
    """Decorator thats schedules and calls the current circuit executing
    the decorated function."""
    @functools.wraps(function)
    def wrapper(self, *args, **kwargs):
        self.compile_lazy_circuit()
        return function(self, *args, **kwargs)
    return wrapper


class _PulseBuilder():
    """Builder context class."""

    def __init__(self,
                 backend,
                 entry_block: Schedule = None,
                 default_alignment: Union[str, Callable] = 'left',
                 default_transpiler_settings: Mapping = None,
                 default_circuit_scheduler_settings: Mapping = None):
        """Initialize builder context.

        This is not a public class

        Args:
            backend (BaseBackend): Input backend to use in builder.
            entry_block: Initital schedule block to build off of.
            default_alignment: Default scheduling alignment for builder.
                One of 'left', 'right', 'sequential' or an alignment
                contextmanager.
            default_transpiler_settings: Default settings for the transpiler.
            default_circuit_scheduler_settings: Default settings for the
                circuit to pulse scheduler.
        """
        #: BaseBackend: Backend instance for context builder.
        self.backend = backend

        #: Union[None, ContextVar]: Token for this ``_PulseBuilder``'s ``ContextVar``.
        self._backend_ctx_token = None

        #: pulse.Schedule: Current current schedule of BuilderContext.
        self._block = None

        #: QuantumCircuit: Lazily constructed quantum circuit
        self._lazy_circuit = self.new_circuit()

        # ContextManager: Default alignment context.
        self._default_alignment_context = align(default_alignment)

        if default_transpiler_settings is None:
            default_transpiler_settings = {}
        self._transpiler_settings = default_transpiler_settings

        if default_circuit_scheduler_settings is None:
            default_circuit_scheduler_settings = {}
        self._circuit_scheduler_settings = default_circuit_scheduler_settings

        if entry_block is None:
            entry_block = Schedule()
        # pulse.Schedule: Root program block
        self._entry_block = entry_block

        self.set_current_block(Schedule())

    def __enter__(self) -> '_PulseBuilder':
        """Enter Builder Context."""
        self._backend_ctx_token = BUILDER_CONTEXTVAR.set(self)
        self._default_alignment_context.__enter__()
        return self

    @_compile_lazy_circuit_before
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit Builder Context."""
        self._default_alignment_context.__exit__(exc_type, exc_val, exc_tb)
        self.compile()
        BUILDER_CONTEXTVAR.reset(self._backend_ctx_token)

    @property
    def block(self) -> Schedule:
        """Return the current block of this bulder."""
        return self._block

    @property
    def num_qubits(self):
        """Get the number of qubits in the backend."""
        return self.backend.configuration().n_qubits

    @property
    def transpiler_settings(self) -> Mapping:
        """The current builder transpiler settings."""
        return self._transpiler_settings

    @transpiler_settings.setter
    @_compile_lazy_circuit_before
    def transpiler_settings(self, settings: Mapping):
        self.compile_lazy_circuit()
        self._transpiler_settings = settings

    @property
    def circuit_scheduler_settings(self) -> Mapping:
        """The current builder circuit to pulse scheduler settings."""
        return self._circuit_scheduler_settings

    @circuit_scheduler_settings.setter
    @_compile_lazy_circuit_before
    def circuit_scheduler_settings(self, settings: Mapping):
        self.compile_lazy_circuit()
        self._circuit_scheduler_settings = settings

    @_compile_lazy_circuit_before
    def compile(self) -> Schedule:
        """Compile and output the built program."""
        # Not much happens because we currently compile as we build.
        # This should be offloaded to a true compilation module
        # once we define a more sophisticated IR.
        program = self._entry_block.append(self.block, mutate=True)
        self.set_current_block(Schedule())
        return program

    @_compile_lazy_circuit_before
    def set_current_block(self, block: Schedule):
        """Set the current block."""
        assert isinstance(block, Schedule)
        self._block = block

    @_compile_lazy_circuit_before
    def append_block(self, block: Schedule):
        """Add a block to the current current block."""
        self.block.append(block, mutate=True)

    @_compile_lazy_circuit_before
    def append_instruction(self, instruction: instructions.Instruction):
        """Add an instruction to the current current block."""
        self.block.append(instruction, mutate=True)

    def compile_lazy_circuit(self):
        """Call a QuantumCircuit."""
        # check by length, can't check if QuantumCircuit is None
        # so disable pylint error.
        if len(self._lazy_circuit):  # pylint: disable=len-as-condition
            import qiskit.compiler as compiler

            lazy_circuit = self._lazy_circuit
            # reset lazy circuit
            self._lazy_circuit = self.new_circuit()
            transpiled_circuit = compiler.transpile(lazy_circuit,
                                                    self.backend,
                                                    **self.transpiler_settings)
            sched = compiler.schedule(transpiled_circuit,
                                      self.backend,
                                      **self.circuit_scheduler_settings)
            self.call_schedule(sched)

    def call_schedule(self, schedule: Schedule):
        """Call a schedule."""
        self.append_block(schedule)

    def new_circuit(self):
        """Create a new circuit for scheduling."""
        return circuit.QuantumCircuit(self.num_qubits)

    def call_circuit(self,
                     circ: circuit.QuantumCircuit,
                     lazy: bool = True):
        """Call a circuit in the pulse program.

        The circuit is assumed to be defined on physical qubits.

        If ``lazy == True`` this circuit will extend a lazily constructed
        quantum circuit. When the given context changes breaking the circuit
        assumptions such as adding a pulse instruction, changing the alignment
        context, or using new scheduling instructions the circuit will be
        transpiled and pulse scheduled.

        Args:
            circ: Circuit to call.
            lazy: If false the circuit will be transpiled and pulse scheduled
                immediately. Otherwise, it will extend the current lazy circuit
                as defined above.
        """
        if lazy:
            self._lazy_circuit.extend(circ)
        else:
            self.compile_lazy_circuit()
            self._lazy_circuit.extend(circ)
            self.compile_lazy_circuit()

    def call_gate(self,
                  gate: circuit.Gate,
                  qubits: Tuple[int, ...],
                  lazy: bool = True):
        """Call the circuit ``gate`` in the pulse program.

        The qubits are assumed to be defined on physical qubits.

        If ``lazy == True`` this gate will extend a lazily constructed
        quantum circuit. When the given context changes breaking the circuit
        assumptions such as adding a pulse instruction, changing the alignment
        context, or using new scheduling instructions the circuit will be
        transpiled and pulse scheduled.

        Args:
            gate: Gate to call.
            qubits: Qubits to call gate on.
            lazy: If false the circuit will be transpiled and pulse scheduled
                immediately. Otherwise, it will extend the current lazy circuit
                as defined above.
        """
        try:
            iter(qubits)
        except TypeError:
            qubits = (qubits,)

        qc = circuit.QuantumCircuit(self.num_qubits)
        qc.append(gate, qargs=qubits)
        self.call_circuit(qc, lazy=lazy)


def build(backend,
          schedule: Schedule,
          default_alignment: str = 'left',
          default_transpiler_settings: Dict[str, Any] = None,
          default_circuit_scheduler_settings: Dict[str, Any] = None
          ) -> ContextManager[None]:
    """
    A context manager for the imperative pulse builder DSL.

    Args:
        backend (BaseBackend): a Qiskit backend.
        schedule: a *mutable* pulse Schedule in which to build your pulse program.
        default_alignment: Default scheduling alignment for builder.
            One of ``left``, ``right``, ``sequential`` or an alignment
            contextmanager.
        default_transpiler_settings: Default settings for the transpiler.
        default_circuit_scheduler_settings: Default settings for the
            circuit to pulse scheduler.

    Returns:
        A new builder context which has the current builder inititalized.
    """
    return _PulseBuilder(
        backend,
        schedule,
        default_alignment=default_alignment,
        default_transpiler_settings=default_transpiler_settings,
        default_circuit_scheduler_settings=default_circuit_scheduler_settings)


# Builder Utilities ############################################################
def _current_builder() -> _PulseBuilder:
    """Get the current builder in the current context.

    Returns:
        The current active builder in this context.

    Raises:
        exceptions.PulseError: If a pulse builder function is called outside of a
            builder context.
    """
    try:
        return BUILDER_CONTEXTVAR.get()
    except LookupError as err:
        raise exceptions.PulseError(
            'A Pulse builder function was called outside of '
            'a builder context. Try calling within a builder '
            'context, eg., "with build(backend, schedule): ...".') from err


def current_backend():
    """Get the backend of the current context.

    Returns:
        BaseBackend: The current backend in the current builder context.
    """
    return _current_builder().backend


def append_block(block: Schedule):
    """Append a block to the current block.

    The current block is not changed.
    """
    _current_builder().append_block(block)


def append_instruction(instruction: instructions.Instruction):
    """Append an instruction to current context."""
    _current_builder().append_instruction(instruction)


def qubit_channels(qubit: int) -> Set[channels.Channel]:
    """Returns the 'typical' set of channels associated with a qubit."""
    return set(current_backend().configuration().get_qubit_channels(qubit))


def current_transpiler_settings() -> Dict[str, Any]:
    """Return current context transpiler settings."""
    return _current_builder().transpiler_settings


# pylint: disable=invalid-name
def current_circuit_scheduler_settings() -> Dict[str, Any]:
    """Return current context circuit scheduler settings."""
    return _current_builder().circuit_scheduler_settings


# Contexts ###########################################################
def _transform_context(transform: Callable[[Schedule], Schedule],
                       **transform_kwargs: Any,
                       ) -> Callable[..., ContextManager[None]]:
    """A tranform context generator decorator

    Decorator accepts a transformation function, and then decorates a new
    ContextManager function.

    When the context is entered it creates a new schedule, sets it as the
    active block and then yields.

    Finally it will reset the initial active block after exiting
    the context and apply the decorated transform function to the
    context Schedule. The output transformed schedule will then be
    appended to the initial active block.

    Args:
        transform: Transform to decorate as context.
        transform_kwargs: Additional override keyword arguments for the
            decorated transform.

    Returns:
        A function that generates a new transformation ``ContextManager``.
    """
    @functools.wraps(transform)
    def wrap(function):  # pylint: disable=unused-argument
        @contextmanager
        def wrapped_transform(*args, **kwargs):
            builder = _current_builder()
            current_block = builder.block
            transform_block = Schedule()
            builder.set_current_block(transform_block)
            try:
                yield
            finally:
                builder.compile_lazy_circuit()
                transformed_block = transform(transform_block,
                                              *args,
                                              **kwargs,
                                              **transform_kwargs)
                builder.set_current_block(current_block)
                builder.append_block(transformed_block)
        return wrapped_transform

    return wrap


@_transform_context(transforms.align_left)
def align_left() -> ContextManager[None]:
    """Left alignment transform builder context."""


@_transform_context(transforms.align_right)
def align_right() -> ContextManager[None]:
    """Right alignment transform builder context."""


@_transform_context(transforms.align_sequential)
def align_sequential() -> ContextManager[None]:
    """Sequential alignment transform builder context."""


def align(alignment: str = 'left') -> ContextManager[None]:
    """General alignment context.

    Args:
        alignment: Alignment scheduling policy to follow.
            One of "left", "right" or "sequential".

    Returns:
        An alignment context that will schedule the instructions it contains
        according to the selected alignment policy upon exiting the context.

    Raises:
        exceptions.PulseError: If an unsupported alignment context is selected.
    """
    if alignment == 'left':
        return align_left()
    elif alignment == 'right':
        return align_right()
    elif alignment == 'sequential':
        return align_sequential()
    else:
        raise exceptions.PulseError('Alignment "{}" is not '
                                    'supported.'.format(alignment))


@_transform_context(transforms.group)
def group() -> ContextManager[None]:
    """Group the instructions within this context fixing their relative timing."""


@contextmanager
def inline() -> ContextManager[None]:
    """Inline all instructions within this context into the parent context.

    .. warning:: This will cause all scheduling directives within this context
        to be ignored.
    """
    builder = _current_builder()
    current_block = builder.block
    transform_block = Schedule()
    builder.set_current_block(transform_block)
    try:
        yield
    finally:
        builder.compile_lazy_circuit()
        builder.set_current_block(current_block)
        for _, instruction in transform_block.instructions:
            append_instruction(instruction)


@_transform_context(transforms.pad, mutate=True)
def pad(*chs: channels.Channel) -> ContextManager[None]:  # pylint: disable=unused-argument
    """Pad all availale timeslots with delays upon exiting context.
    Args:
        chs: Channels to pad with delays. Defaults to all channels in context
            if none are supplied.
    """


@contextmanager
def transpiler_settings(**settings) -> ContextManager[None]:
    """Set the current current tranpiler settings for this context."""
    builder = _current_builder()
    curr_transpiler_settings = builder.transpiler_settings
    builder.transpiler_settings = collections.ChainMap(
        settings, curr_transpiler_settings)
    try:
        yield
    finally:
        builder.transpiler_settings = curr_transpiler_settings


@contextmanager
def circuit_scheduler_settings(**settings) -> ContextManager[None]:
    """Set the current current circuit scheduling settings for this context."""
    builder = _current_builder()
    curr_circuit_scheduler_settings = builder.circuit_scheduler_settings
    builder.circuit_scheduler_settings = collections.ChainMap(
        settings, curr_circuit_scheduler_settings)
    try:
        yield
    finally:
        builder.circuit_scheduler_settings = curr_circuit_scheduler_settings


@contextmanager
def phase_offset(channel: channels.PulseChannel,
                 phase: float) -> ContextManager[None]:
    """Shift the phase of a channel on entry into context and undo on exit.

    Args:
        channel: Channel to offset phase of.
        phase: Amount of phase offset in radians.

    Yields:
        None
    """
    shift_phase(channel, phase)
    try:
        yield
    finally:
        shift_phase(channel, -phase)


@contextmanager
def frequency_offset(channel: channels.PulseChannel,
                     frequency: float,
                     compensate_phase: bool = False
                     ) -> ContextManager[None]:
    """Shift the frequency of a channel on entry into context and undo on exit.

    Args:
        channel: Channel to offset phase of.
        frequency: Amount of frequency offset in Hz.
        compensate_phase: Compensate for accumulated phase in accumulated with
            respect to the channels frame at its initial frequency.

    Yields:
        None
    """
    builder = _current_builder()
    t0 = builder.block.duration
    shift_frequency(channel, frequency)
    try:
        yield
    finally:
        if compensate_phase:
            duration = builder.block.duration - t0
            dt = current_backend().configuration().dt
            accumulated_phase = duration * dt * frequency % (2*np.pi)
            shift_phase(channel, -accumulated_phase)
        shift_frequency(channel, -frequency)


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
            **metadata: Union[configuration.Kernel,
                              configuration.Discriminator]):
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

    Raises:
        exceptions.PulseError: If input is not a ``Channel`` or an integer
            representing a qubit index.
        NotImplementedError: Barrier has not yet been implemented.
    """
    chans = set()
    for channel_or_qubit in channels_or_qubits:
        if isinstance(channel_or_qubit, int):
            chans += qubit_channels(channel_or_qubit)
        elif isinstance(channel_or_qubit, channels.Channel):
            chans.add(channel_or_qubit)
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


def call_circuit(circ: circuit.QuantumCircuit):
    """Call a quantum ``circuit`` within the current builder context."""
    _current_builder().call_circuit(circ, lazy=True)


def call(target: Union[circuit.QuantumCircuit, Schedule]):
    """Call the ``target`` within the current builder context.

    Args:
        target: Target circuit or pulse schedule to call.

    Raises:
        exceptions.PulseError: If the input ``target`` type is not supported.
    """
    if isinstance(target, circuit.QuantumCircuit):
        call_circuit(target)
    elif isinstance(target, Schedule):
        call_schedule(target)
    else:
        raise exceptions.PulseError(
            'Target of type "{}" is not supported.'.format(type(target)))


# Macros #######################################################################
def measure(qubit: int,
            register: Union[channels.MemorySlot, channels.RegisterSlot] = None,
            ) -> Union[channels.MemorySlot, channels.RegisterSlot]:
    """Measure a qubit within the current builder context.

    Args:
        qubit: Physical qubit to measure.
        register: Register to store result in. If not selected the current
            behavior is to return the :class:`MemorySlot` with the same
            index as ``qubit``. This register will be returned.
    Returns:
        The ``register`` the qubit measurement result will be stored in.
    """
    backend = current_backend()
    if not register:
        register = channels.MemorySlot(qubit)

    measure_sched = macros.measure(
        qubits=[qubit],
        inst_map=backend.defaults().instruction_schedule_map,
        meas_map=backend.configuration().meas_map,
        qubit_mem_slots={register: register})
    call_schedule(measure_sched)

    return register


def delay_qubits(qubits: Union[int, Iterable[int]], duration: int):
    """Insert delays on all of the :class:`channels.Channel` that belong ``qubits``.

    Args:
        qubits: Physical qubits to delay on. Delays will be inserted based on
            the channels returned by :function:`qubit_channels`.
        duration: Duration to delay for.
    """
    try:
        iter(qubits)
    except TypeError:
        qubits = [qubits]

    qubit_chans = set(itertools.chain.from_iterable(qubit_channels(qubit) for
                                                    qubit in qubits))
    with align_left(), group():
        for chan in qubit_chans:
            delay(chan, duration)


# Gate instructions ############################################################
def call_gate(gate: circuit.Gate, qubits: Tuple[int, ...]):
    """Call a gate and lower to its corresponding pulse instruction.

    .. note:: If multiple gates are called in a row they may be optimized by the
        transpiler, depending on the :function:`current_transpiler_settings``.
    """
    _current_builder().call_gate(gate, qubits, lazy=True)


def cx(control: int, target: int):
    """Call a cx gate on physical qubits."""
    call_gate(gates.CXGate(), (control, target))


def u1(qubit: int, theta: float):
    """Call a u1 gate on physical qubits."""
    call_gate(gates.U1Gate(theta), qubit)


def u2(qubit: int, phi: float, lam: float):
    """Call a u2 gate on physical qubits."""
    call_gate(gates.U2Gate(phi, lam), qubit)


def u3(qubit: int, theta: float, phi: float, lam: float):
    """Call a u3 gate on physical qubits."""
    call_gate(gates.U3Gate(theta, phi, lam), qubit)


def x(qubit: int):
    """Call a x gate on physical qubits."""
    call_gate(gates.XGate(), qubit)
