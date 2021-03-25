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

"""ASAP Scheduling."""
from collections import defaultdict
from typing import List
from qiskit.transpiler.passes.scheduling.time_unit_conversion import TimeUnitConversion
from qiskit.circuit.delay import Delay
from qiskit.dagcircuit import DAGCircuit
from qiskit.transpiler.basepasses import TransformationPass
from qiskit.transpiler.exceptions import TranspilerError


class ASAPSchedule(TransformationPass):
    """ASAP Scheduling."""

    def __init__(self, durations, time_unit=None):
        """ASAPSchedule initializer.

        Args:
            durations (InstructionDurations): Durations of instructions to be used in scheduling
        """
        super().__init__()
        self.durations = durations
        self.time_unit = time_unit
        # ensure op node durations are attached and in consistent unit
        self.requires.append(TimeUnitConversion(durations))

    def run(self, dag):
        """Run the ASAPSchedule pass on `dag`.

        Args:
            dag (DAGCircuit): DAG to schedule.

        Returns:
            DAGCircuit: A scheduled DAG.

        Raises:
            TranspilerError: if the circuit is not mapped on physical qubits.
        """
        if len(dag.qregs) != 1 or dag.qregs.get('q', None) is None:
            raise TranspilerError('ASAP schedule runs on physical circuits only')

        if not self.time_unit:
            self.time_unit = self.property_set['time_unit']

        new_dag = DAGCircuit()
        for qreg in dag.qregs.values():
            new_dag.add_qreg(qreg)
        for creg in dag.cregs.values():
            new_dag.add_creg(creg)

        qubit_time_available = defaultdict(int)

        def pad_with_delays(qubits: List[int], until, unit) -> None:
            """Pad idle time-slots in ``qubits`` with delays in ``unit`` until ``until``."""
            for q in qubits:
                if qubit_time_available[q] < until:
                    idle_duration = until - qubit_time_available[q]
                    new_dag.apply_operation_back(Delay(idle_duration, unit), [q])

        for node in dag.topological_op_nodes():
            start_time = max(qubit_time_available[q] for q in node.qargs)
            pad_with_delays(node.qargs, until=start_time, unit=self.time_unit)

            new_dag.apply_operation_back(node.op, node.qargs, node.cargs, node.condition)

            if node.op.duration is None:
                indices = [n.index for n in node.qargs]
                raise TranspilerError(f"Duration of {node.op.name} on qubits "
                                      f"{indices} is not found.")

            stop_time = start_time + node.op.duration
            # update time table
            for q in node.qargs:
                qubit_time_available[q] = stop_time

        working_qubits = qubit_time_available.keys()
        circuit_duration = max(qubit_time_available[q] for q in working_qubits)
        pad_with_delays(new_dag.qubits, until=circuit_duration, unit=self.time_unit)

        new_dag.name = dag.name
        new_dag.metadata = dag.metadata
        new_dag.duration = circuit_duration
        new_dag.unit = self.time_unit
        return new_dag
