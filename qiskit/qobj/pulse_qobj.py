# -*- coding: utf-8 -*-

# This code is part of Qiskit.
#
# (C) Copyright IBM 2019.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

# pylint: disable=invalid-name,redefined-builtin,method-hidden,arguments-differ

"""Module providing definitions of Pulse Qobj classes."""

import copy
import json

import numpy

from qiskit.qobj.qasm_qobj import QobjHeader
from qiskit.qobj.qasm_qobj import QasmQobjExperimentHeader
from qiskit.qobj.qasm_qobj import validator


class QobjMeasurementOption:
    """An individual measurement option."""

    def __init__(self, name, params=None):
        """Instantiate a new QobjMeasurementOption object.

        Args:
            name (str): The name of the measurement option
            params (list): The parameters of the measurement option.
        """
        self._data = {}
        self._data['name'] = name
        if params is not None:
            self._data['params'] = params

    @property
    def name(self):
        """The name of the measurement option."""
        if 'name' not in self._data:
            raise AttributeError('Attribute name is not defined')
        return self._data['name']

    @name.setter
    def name(self, value):
        self._data['name'] = value

    @property
    def params(self):
        """The parameters of the measurement option."""
        if 'params' not in self._data:
            raise AttributeError('Attribute name is not defined')
        return self._data['params']

    @params.setter
    def params(self, value):
        self._data['params'] = value

    def to_dict(self):
        """Return a dict format representation of the QobjMeasurementOption.

        Returns:
            dict: The dictionary form of the QasmMeasurementOption.
        """
        return self._data

    @classmethod
    def from_dict(cls, data):
        """Create a new QobjMeasurementOption object from a dictionary.

        Args:
            data (dict): A dictionary for the experiment config

        Returns:
            QobjMeasurementOption: The object from the input dictionary.
        """
        return cls(**data)

    def __eq__(self, other):
        if isinstance(other, QobjMeasurementOption):
            if self.to_dict() == other.to_dict():
                return True
        return False


class PulseQobjInstruction:
    """A class representing a single instruction in an PulseQobj Experiment."""

    def __init__(self, name, t0, ch=None, conditional=None, val=None, phase=None,
                 duration=None, qubits=None, memory_slot=None,
                 register_slot=None, kernels=None, discriminators=None,
                 label=None, type=None, pulse_shape=None,
                 parameters=None):
        """Instantiate a new PulseQobjInstruction object.

        Args:
            name (str): The name of the instruction
            t0 (int): Pulse start time in integer **dt** units.
            ch (str): The channel to apply the pulse instruction.
            conditional (int): The register to use for a conditional for this
                instruction
            val (complex): Complex value to apply, bounded by an absolute value
                of 1.
            phase (float): if a ``fc`` instruction, the frame change phase in
                radians.
            duration (int): The duration of the pulse in **dt** units.
            qubits (list): A list of `int`s representing the qubits the
                instruction operates on
            memory_slot (list): If a ``measure`` instruction this is a list
                of `int`s containing the list of memory slots to store the
                measurement results in (must be the same length as qubits).
                If a ``bfunc`` instruction this is a single `int` of the
                memory slot to store the boolean function result in.
            register_slot (list): If a ``measure`` instruction this is a list
                of `int`s containing the list of register slots in which to
                store the measurement results (must be the same length as
                qubits). If a ``bfunc`` instruction this is a single `int`
                of the register slot in which to store the result.
            kernels (list): List of :class:`QobjMeasurementOption` objects
                defining the measurement kernels and set of parameters if the
                measurement level is 1 or 2. Only used for ``acquire``
                instructions.
            discriminators (list): A list of :class:`QobjMeasurementOption`
                used to set the discriminators to be used if the measurement
                level is 2. Only used for ``acquire`` instructions.
            label (str): Label of instruction
            type (str): Type of instruction
            pulse_shape (str): The shape of the parametric pulse
            parameters (dict): The parameters for a parametric pulse
        """
        self.name = name
        self.t0 = t0
        if ch is not None:
            self.ch = ch
        if conditional is not None:
            self.conditional = conditional
        if val is not None:
            self.val = val
        if phase is not None:
            self.phase = phase
        if duration is not None:
            self.duration = duration
        if qubits is not None:
            self.qubits = qubits
        if memory_slot is not None:
            self.memory_slot = memory_slot
        if register_slot is not None:
            self.register_slot = register_slot
        if kernels is not None:
            self.kernels = kernels
        if discriminators is not None:
            self.discriminators = discriminators
        if label is not None:
            self.label = label
        if type is not None:
            self.type = type
        if pulse_shape is not None:
            self.pulse_shape = pulse_shape
        if parameters is not None:
            self.parameters = parameters

    def to_dict(self):
        """Return a dictionary format representation of the Instruction.

        Returns:
            dict: The dictionary form of the PulseQobjInstruction.
        """
        out_dict = {
            'name': self.name,
            't0': self.t0
        }
        for attr in ['ch', 'conditional', 'val', 'phase', 'duration',
                     'qubits', 'memory_slot', 'register_slot',
                     'label', 'type', 'pulse_shape', 'parameters']:
            if hasattr(self, attr):
                out_dict[attr] = getattr(self, attr)
        if hasattr(self, 'kernels'):
            out_dict['kernels'] = [x.to_dict() for x in self.kernels]
        if hasattr(self, 'discriminators'):
            out_dict['discriminators'] = [
                x.to_dict() for x in self.discriminators]
        return out_dict

    @classmethod
    def from_dict(cls, data):
        """Create a new PulseQobjExperimentConfig object from a dictionary.

        Args:
            data (dict): A dictionary for the experiment config

        Returns:
            PulseQobjInstruction: The object from the input dictionary.
        """
        t0 = data.pop('t0')
        name = data.pop('name')
        if 'kernels' in data:
            kernels = data.pop('kernels')
            kernel_obj = [QobjMeasurementOption.from_dict(x) for x in kernels]
            data['kernels'] = kernel_obj
        return cls(name, t0, **data)

    def __eq__(self, other):
        if isinstance(other, PulseQobjInstruction):
            if self.to_dict() == other.to_dict():
                return True
        return False


class PulseQobjConfig:
    """A configuration for a Pulse Qobj."""

    def __init__(self, meas_level, meas_return, pulse_library,
                 qubit_lo_freq, meas_lo_freq, memory_slot_size=None,
                 rep_time=None, shots=None, max_credits=None,
                 seed_simulator=None, memory_slots=None, **kwargs):
        """Instantiate a PulseQobjConfig object.

        Args:
            meas_level (int): The measurement level to use.
            meas_return (int): The level of measurement information to return.
            pulse_library (list): A list of :class:`PulseLibraryItem` objects
                which define the set of primative pulses
            qubit_lo_freq (list): List of frequencies (as floats) for the qubit
                driver LO's in GHz.
            meas_lo_freq (list): List of frequencies (as floats) for the'
                measurement driver LO's in GHz.
            memory_slot_size (int): Size of each memory slot if the output is
                Level 0.
            rep_time (int): Repetition time of the experiment in μs
            shots (int): The number of shots
            max_credits (int): the max_credits to use on the IBMQ public devices.
            seed_simulator (int): the seed to use in the simulator
            memory_slots (list): The number of memory slots on the device
            kwargs: Additional free form key value fields to add to the
                configuration
        """
        self._data = {}
        self._data['meas_level'] = meas_level
        self._data['meas_return'] = meas_return
        self.pulse_library = pulse_library
        self._data['qubit_lo_freq'] = qubit_lo_freq
        self._data['meas_lo_freq'] = meas_lo_freq
        if memory_slot_size is not None:
            self._data['memory_slot_size'] = memory_slot_size
        if rep_time is not None:
            self._data['rep_time'] = rep_time or []
        if shots is not None:
            self._data['shots'] = int(shots)

        if max_credits is not None:
            self._data['max_credits'] = int(max_credits)

        if seed_simulator is not None:
            self._data['seed_simulator'] = int(seed_simulator)

        if memory_slots is not None:
            self._data['memory_slots'] = int(memory_slots)

        if kwargs:
            self._data.update(kwargs)

    @property
    def meas_level(self):
        """The measurement level to use."""
        return self._data['meas_level']

    @meas_level.setter
    def meas_level(self, data):
        self._data['meas_level'] = data

    @property
    def meas_return(self):
        """The level of measurement information to return."""
        return self._data['meas_return']

    @meas_return.setter
    def meas_return(self, data):
        self._data['meas_return'] = data

    @property
    def shots(self):
        """The number of shots."""
        return self._data.get('shots')

    @shots.setter
    def shots(self, value):
        self._data['shots'] = value

    @property
    def max_credits(self):
        """The max_credits to use on the IBMQ public devices."""
        return self._data.get('max_credits')

    @max_credits.setter
    def max_credits(self, value):
        self._data['max_credits'] = value

    @property
    def memory_slots(self):
        """The number of memory slots on the device."""
        mem_slots = self._data.get('memory_slots')
        if mem_slots is None:
            raise AttributeError('Attribute memory_slots is not defined')
        return mem_slots

    @memory_slots.setter
    def memory_slots(self, value):
        self._data['memory_slots'] = value

    def to_dict(self):
        """Return a dictionary format representation of the Pulse Qobj config.

        Returns:
            dict: The dictionary form of the PulseQobjConfig.
        """
        out_dict = copy.copy(self._data)
        if hasattr(self, 'pulse_library'):
            out_dict['pulse_library'] = [
                x.to_dict() for x in self.pulse_library]

        return out_dict

    @classmethod
    def from_dict(cls, data):
        """Create a new PulseQobjConfig object from a dictionary.

        Args:
            data (dict): A dictionary for the config

        Returns:
            PulseQobjConfig: The object from the input dictionary.
        """
        if 'pulse_library' in data:
            pulse_lib = data.pop('pulse_library')
            pulse_lib_obj = [PulseLibraryItem.from_dict(x) for x in pulse_lib]
            data['pulse_library'] = pulse_lib_obj
        return cls(**data)

    def __getattr__(self, name):
        try:
            return self._data[name]
        except KeyError:
            raise AttributeError('Attribute %s is not defined' % name)

    def __eq__(self, other):
        if isinstance(other, PulseQobjConfig):
            if self.to_dict() == other.to_dict():
                return True
        return False


class PulseQobjExperiment:
    """A Pulse Qobj Experiment.

    Each instance of this class is used to represent an individual Pulse
    experiment as part of a larger Pulse Qobj.
    """

    def __init__(self, config=None, header=None, instructions=None):
        """Instantiate a PulseQobjExperiment.

        Args:
            config (PulseQobjExperimentConfig): A config object for the experiment
            header (PulseQobjExperimentHeader): A header object for the experiment
            instructions (list): A list of :class:`PulseQobjInstruction` objects
        """
        if config is not None:
            self.config = config
        if header is not None:
            self.header = header
        self.instructions = instructions or []

    def to_dict(self):
        """Return a dictionary format representation of the Experiment.

        Returns:
            dict: The dictionary form of the PulseQobjExperiment.
        """
        out_dict = {
            'instructions': [x.to_dict() for x in self.instructions]
        }
        if hasattr(self, 'config'):
            out_dict['config'] = self.config.to_dict()
        if hasattr(self, 'header'):
            out_dict['header'] = self.header.to_dict()
        return out_dict

    @classmethod
    def from_dict(cls, data):
        """Create a new PulseQobjExperiment object from a dictionary.

        Args:
            data (dict): A dictionary for the experiment config

        Returns:
            PulseQobjExperiment: The object from the input dictionary.
        """
        config = None
        if 'config' in data:
            config = PulseQobjExperimentConfig.from_dict(data.pop('config'))
        header = None
        if 'header' in data:
            header = QasmQobjExperimentHeader.from_dict(data.pop('header'))
        instructions = None
        if 'instructions' in data:
            instructions = [
                PulseQobjInstruction.from_dict(
                    inst) for inst in data.pop('instructions')]
        return cls(config, header, instructions)

    def __eq__(self, other):
        if isinstance(other, PulseQobjExperiment):
            if self.to_dict() == other.to_dict():
                return True
        return False


class PulseQobjExperimentConfig:
    """A config for a single Pulse experiment in the qobj."""

    _data = {}

    def __init__(self, qubit_lo_freq=None, meas_lo_freq=None):
        """Instantiate a PulseQobjExperimentConfig object.

        Args:
            qubit_lo_freq (list): List of frequencies (as floats) for the qubit
                driver LO's in GHz.
            meas_lo_freq (list): List of frequencies (as floats) for the'
                measurement driver LO's in GHz.
        """
        super(PulseQobjExperimentConfig, self).__init__()
        self._data = {}
        if qubit_lo_freq is not None:
            self._data['qubit_lo_freq'] = qubit_lo_freq
        if meas_lo_freq is not None:
            self._data['meas_lo_freq'] = meas_lo_freq

    def to_dict(self):
        """Return a dictionary format representation of the experiment config.

        Returns:
            dict: The dictionary form of the PulseQobjExperimentConfig.
        """
        return self._data

    @classmethod
    def from_dict(cls, data):
        """Create a new PulseQobjExperimentConfig object from a dictionary.

        Args:
            data (dict): A dictionary for the experiment config

        Returns:
            PulseQobjExperimentConfig: The object from the input dictionary.
        """
        return cls(**data)

    def __eq__(self, other):
        if isinstance(other, PulseQobjExperimentConfig):
            if self.to_dict() == other.to_dict():
                return True
        return False


class PulseLibraryItem:
    """An item in a pulse library."""

    def __init__(self, name, samples):
        """Instantiate a pulse library item.

        Args:
            name (str): A name for the pulse.
            samples (list[complex]): A list of complex values defining pulse
                shape.
        """
        self.name = name
        self.samples = samples

    def to_dict(self):
        """Return a dictionary format representation of the pulse library item.

        Returns:
            dict: The dictionary form of the PulseLibraryItem.
        """
        return {'name': self.name, 'samples': self.samples}

    @classmethod
    def from_dict(cls, data):
        """Create a new PulseLibraryItem object from a dictionary.

        Args:
            data (dict): A dictionary for the experiment config

        Returns:
            PulseLibraryItem: The object from the input dictionary.
        """
        return cls(**data)

    def __eq__(self, other):
        if isinstance(other, PulseLibraryItem):
            if self.to_dict() == other.to_dict():
                return True
        return False


class PulseQobj:
    """A Pulse Qobj."""

    def __init__(self, qobj_id=None, config=None, experiments=None,
                 header=None):
        """Instatiate a new QASM Qobj Object.

        Each QASM Qobj object is used to represent a single payload that will
        be passed to a Qiskit provider. It mirrors the Qobj the published
        `Qobj specification <https://arxiv.org/abs/1809.03452>`_ for OpenQASM
        experiments.

        Args:
            qobj_id (str): An identifier for the qobj
            config (PulseQobjRunConfig): A config for the entire run
            header (QobjHeader): A header for the entire run
            experiments (list): A list of lists of :class:`PulseQobjExperiment`
                objects representing an experiment
        """
        self.qobj_id = qobj_id
        self.config = config or PulseQobjConfig()
        self.header = header or QobjHeader()
        self.experiments = experiments or []

    def to_dict(self, validate=False):
        """Return a dictionary format representation of the Pulse Qobj.

        Note this dict is not in the json wire format expected by IBMQ and qobj
        specification because complex numbers are still of type complex. Also
        this may contain native numpy arrays. When serializing this output
        for use with IBMQ you can leverage a json encoder that converts these
        as expected. For example:

        .. code-block::

            import json
            import numpy

            class QobjEncoder(json.JSONEncoder):
                def default(self, obj):
                    if isinstance(obj, numpy.ndarray):
                        return obj.tolist()
                    if isinstance(obj, complex):
                        return (obj.real, obj.imag)
                    return json.JSONEncoder.default(self, obj)

            json.dumps(qobj.to_dict(), cls=QobjEncoder)

        Args:
            validate (bool): When set to true validate the output dictionary
                against the jsonschema for qobj spec.

        Returns:
            dict: A dictionary representation of the QasmQobj object
        """
        out_dict = {
            'qobj_id': self.qobj_id,
            'header': self.header.to_dict(),
            'config': self.config.to_dict(),
            'schema_version': '1.1.0',
            'type': 'PULSE',
            'experiments': [x.to_dict() for x in self.experiments]
        }
        if validate:

            class PulseQobjEncoder(json.JSONEncoder):
                """A json encoder for pulse qobj"""
                def default(self, obj):
                    if isinstance(obj, numpy.ndarray):
                        return obj.tolist()
                    if isinstance(obj, complex):
                        return (obj.real, obj.imag)
                    return json.JSONEncoder.default(self, obj)

            json_str = json.dumps(out_dict, cls=PulseQobjEncoder)
            validator(json.loads(json_str))
        return out_dict

    @classmethod
    def from_dict(cls, data):
        """Create a new PulseQobj object from a dictionary.

        Args:
            data (dict): A dictionary representing the PulseQobj to create. It
                will be in the same format as output by :func:`to_dict`.

        Returns:
            PulseQobj: The PulseQobj from the input dictionary.
        """
        config = None
        if 'config' in data:
            config = PulseQobjConfig.from_dict(data['config'])
        experiments = None
        if 'experiments' in data:
            experiments = [
                PulseQobjExperiment.from_dict(
                    exp) for exp in data['experiments']]
        header = None
        if 'header' in data:
            header = QobjHeader.from_dict(data['header'])

        return cls(qobj_id=data.get('qobj_id'), config=config,
                   experiments=experiments, header=header)

    def __eq__(self, other):
        if isinstance(other, PulseQobj):
            if self.to_dict() == other.to_dict():
                return True
        return False
