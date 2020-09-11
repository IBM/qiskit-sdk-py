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

"""Durations of instructions, one of transpiler configurations."""
from typing import Optional, List, Tuple, Union, Iterable

from qiskit.circuit import Barrier, Delay
from qiskit.circuit import Instruction, Qubit
from qiskit.providers import BaseBackend
from qiskit.transpiler.exceptions import TranspilerError


class InstructionDurations:
    """Helper class to provide durations for scheduling."""

    def __init__(self,
                 instruction_durations: Optional['InstructionDurationsType'] = None,
                 unit: str = None):
        self.duration_by_name = {}
        self.duration_by_name_qubits = {}
        self.unit = unit
        if instruction_durations:
            self.update(instruction_durations, unit)

    @classmethod
    def from_backend(cls, backend: BaseBackend):
        """Construct the instruction durations from the backend."""
        instruction_durations = []
        # backend.properties._gates -> instruction_durations
        for gate, insts in backend.properties()._gates.items():
            for qubits, props in insts.items():
                if 'gate_length' in props:
                    gate_length = props['gate_length'][0]  # Throw away datetime at index 1
                    instruction_durations.append((gate, qubits, gate_length))

        # TODO: backend.properties() should tell us all about instruction durations
        if not backend.configuration().open_pulse:
            raise TranspilerError("No backend.configuration().dt in the backend")
        # To know duration of measures, to be removed
        dt = backend.configuration().dt  # pylint: disable=invalid-name
        inst_map = backend.defaults().instruction_schedule_map
        all_qubits = tuple(range(backend.configuration().num_qubits))
        meas_duration = inst_map.get('measure', all_qubits).duration
        for q in all_qubits:
            instruction_durations.append(('measure', [q], meas_duration * dt))

        return InstructionDurations(instruction_durations, unit='s')

    def update(self,
               inst_durations: Optional['InstructionDurationsType'],
               unit: str = None):
        """Merge/extend self with instruction_durations."""
        if inst_durations is None:
            return self

        if (not isinstance(inst_durations, InstructionDurations) and self.unit != unit) or \
           (isinstance(inst_durations, InstructionDurations) and self.unit != inst_durations.unit):
            raise TranspilerError("unit must be '%s', the same as original" % self.unit)

        if isinstance(inst_durations, InstructionDurations):
            self.duration_by_name.update(inst_durations.duration_by_name)
            self.duration_by_name_qubits.update(inst_durations.duration_by_name_qubits)
        else:
            for name, qubits, duration in inst_durations:
                if isinstance(qubits, int):
                    qubits = [qubits]

                if qubits is None:
                    self.duration_by_name[name] = duration
                else:
                    self.duration_by_name_qubits[(name, tuple(qubits))] = duration

        return self

    def get(self,
            inst_name: Union[str, Instruction],
            qubits: Union[int, List[int], Qubit, List[Qubit]]) -> float:
        """Get the duration of the instruction with the name and the qubits.

        Args:
            inst_name: an instruction or its name to be queried.
            qubits: qubits or its indices that the instruction acts on.

        Returns:
            float: The duration of the instruction on the qubits.

        Raises:
            TranspilerError: No duration is defined for the instruction.
        """
        if isinstance(inst_name, Barrier):
            return 0
        elif isinstance(inst_name, Delay):
            if inst_name.unit != self.unit:
                raise TranspilerError("unit of delay (currently %s) must be '%s', consistent "
                                      "with other instructions" % (inst_name.unit, self.unit))
            return inst_name.duration

        if isinstance(inst_name, Instruction):
            inst_name = inst_name.name

        if isinstance(qubits, (int, Qubit)):
            qubits = [qubits]

        if isinstance(qubits[0], Qubit):
            qubits = [q.index for q in qubits]

        try:
            return self._get(inst_name, qubits)
        except TranspilerError:
            raise TranspilerError("Duration of %s on qubits %s is not found." % (inst_name, qubits))

    def _get(self, name: str, qubits: List[int]):
        """Get the duration of the instruction with the name and the qubits."""
        if name == 'barrier':
            return 0

        key = (name, tuple(qubits))
        if key in self.duration_by_name_qubits:
            return self.duration_by_name_qubits[key]

        if name in self.duration_by_name:
            return self.duration_by_name[name]

        raise TranspilerError("No value is found for key={}".format(key))


InstructionDurationsType = Union[List[Tuple[str, Optional[Iterable[int]], float]],
                                 InstructionDurations]
"""List of tuples representing (instruction name, qubits indices, duration)."""
