# -*- coding: utf-8 -*-

# Copyright 2018, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""Model for schema-conformant Results."""

from qiskit import QISKitError, QuantumCircuit
from qiskit.validation.base import BaseModel, bind_schema
from .schema import ResultSchema


@bind_schema(ResultSchema)
class Result(BaseModel):
    """Model for Results.

    Please note that this class only describes the required fields. For the
    full description of the model, please check ``ResultSchema``.

    Attributes:
        backend_name (str): backend name.
        backend_version (str): backend version, in the form X.Y.Z.
        qobj_id (str): user-generated Qobj id.
        job_id (str): unique execution id from the backend.
        success (bool): True if complete input qobj executed correctly. (Implies
            each experiment success)
        results (ExperimentResult): corresponding results for array of
            experiments of the input qobj
    """

    def __init__(self, backend_name, backend_version, qobj_id, job_id, success,
                 results, **kwargs):
        self.backend_name = backend_name
        self.backend_version = backend_version
        self.qobj_id = qobj_id
        self.job_id = job_id
        self.success = success
        self.results = results

        super().__init__(**kwargs)

    def __len__(self):
        return len(self.results)

    def __iadd__(self, other):
        """Append a Result object to current Result object.

        Arg:
            other (Result): a Result object to append.
        Returns:
            Result: The current object with appended results.
        Raises:
            QISKitError: if the Results cannot be combined.
        """
        this_backend = self.backend_name
        other_backend = other.backend_name
        if this_backend != other_backend:
            raise QISKitError('Result objects from different backends cannot be combined.')

        if not self.success or not other.success:
            raise QISKitError('Can not combine a failed result with another result.')

        self.results.extend(other.results)
        return self

    def __add__(self, other):
        """Combine Result objects.

        Arg:
            other (Result): a Result object to combine.
        Returns:
            Result: A new Result object consisting of combined objects.
        """
        copy_of_self = self.from_dict(self.to_dict())
        copy_of_self += other
        return copy_of_self

    def get_data(self, circuit=None):
        """Get the data of an experiment.

        Args:
            circuit (str or QuantumCircuit or int or None): x

        Returns:
            dict: A dictionary of data for the different backends.

        Raises:
            QISKitError: if data for the experiment could not be retrieved.
        """
        try:
            return self._get_experiment(circuit).data.to_dict()
        except (KeyError, TypeError):
            raise QISKitError('No data for circuit "{0}"'.format(circuit))

    def get_counts(self, circuit=None):
        """Get the histogram data of circuit name.

        The data from the a qasm circuit is dictionary of the format
        {'00000': XXXX, '00001': XXXXX}.

        Args:
            circuit (str or QuantumCircuit or None): reference to a quantum circuit
                If None and there is only one circuit available, returns
                that one.

        Returns:
            Dictionary: Counts {'00000': XXXX, '00001': XXXXX}.

        Raises:
            QISKitError: if there are no counts for the circuit.
        """
        try:
            return self._get_experiment(circuit).data.counts.to_dict()
        except KeyError:
            raise QISKitError('No counts for circuit "{0}"'.format(circuit))

    def get_statevector(self, circuit=None):
        """Get the final statevector of circuit name.

        The data is a list of complex numbers
        [1.+0.j, 0.+0.j].

        Args:
            circuit (str or QuantumCircuit or None): reference to a quantum circuit
                If None and there is only one circuit available, returns
                that one.

        Returns:
            list[complex]: list of 2^n_qubits complex amplitudes.

        Raises:
            QISKitError: if there is no statevector for the circuit.
        """
        try:
            return self._get_experiment(circuit).data.statevector
        except KeyError:
            raise QISKitError('No statevector for circuit "{0}"'.format(circuit))

    def get_unitary(self, circuit=None):
        """Get the final unitary of circuit name.

        The data is a matrix of complex numbers
        [[1.+0.j, 0.+0.j], .. ].

        Args:
            circuit (str or QuantumCircuit or None): reference to a quantum circuit
                If None and there is only one circuit available, returns
                that one.

        Returns:
            list[list[complex]]: list of 2^n_qubits x 2^n_qubits complex amplitudes.

        Raises:
            QISKitError: if there is no unitary for the circuit.
        """
        try:
            return self._get_experiment(circuit).data.unitary
        except KeyError:
            raise QISKitError('No unitary for circuit "{0}"'.format(circuit))

    def get_snapshots(self, circuit=None):
        """Get snapshots recorded during the run.

        The data is a dictionary:
        where keys are requested snapshot slots.
        and values are a dictionary of the snapshots themselves.

        Args:
            circuit (str or QuantumCircuit or None): reference to a quantum circuit
                If None and there is only one circuit available, returns
                that one.

        Returns:
            dict[slot: dict[str: array]]: list of 2^n_qubits complex amplitudes.

        Raises:
            QISKitError: if there are no snapshots for the circuit.
        """
        try:
            return self._get_experiment(circuit).data.snapshots.to_dict()
        except KeyError:
            raise QISKitError('No snapshots for circuit "{0}"'.format(circuit))

    def get_snapshot(self, slot=None, circuit=None):
        """Get snapshot at a specific slot.

        Args:
            slot (str): snapshot slot to retrieve. If None and there is only one
                slot, return that one.
            circuit (str or QuantumCircuit or None): reference to a quantum circuit
                If None and there is only one circuit available, returns
                that one.

        Returns:
            dict[slot: dict[str: array]]: list of 2^n_qubits complex amplitudes.

        Raises:
            QISKitError: if there is no snapshot at all, or in this slot
        """
        try:
            snapshots_dict = self.get_snapshots(circuit)

            if slot is None:
                slots = list(snapshots_dict.keys())
                if len(slots) == 1:
                    slot = slots[0]
                else:
                    raise QISKitError("You have to select a slot when there "
                                      "is more than one available")
            snapshot_dict = snapshots_dict[slot]

            snapshot_types = list(snapshot_dict.keys())
            if len(snapshot_types) == 1:
                snapshot_list = snapshot_dict[snapshot_types[0]]
                if len(snapshot_list) == 1:
                    return snapshot_list[0]
                return snapshot_list
            return snapshot_dict
        except KeyError:
            raise QISKitError('No snapshot at slot {0} for '
                              'circuit "{1}"'.format(slot, circuit))

    def get_status(self):
        """Return whole result status."""
        return getattr(self, 'status', '')

    def circuit_statuses(self):
        """Return statuses of all circuits.

        Returns:
            list(str): List of status result strings.
        """
        return [getattr(experiment_result, 'status', '') for
                experiment_result in self.results]

    def _get_experiment(self, key=None):
        """Return an experiment from a given key.

        Args:
            key (str or QuantumCircuit or integer or None): x

        Returns:
            ExperimentResult: the results for an experiment.

        Raises:
            QISKitError: if there is no data for the circuit, or an unhandled
                error occurred while fetching the data.
        """
        if not self.success:
            raise QISKitError(getattr(self, 'status',
                                      'Result was not successful'))

        # Automatically return the first result if no key was provided.
        if key is None:
            if len(self.results) != 1:
                raise QISKitError(
                    'You have to select a circuit when there is more than '
                    'one available')
            else:
                key = 0

        # Key is an integer: return result by index.
        if isinstance(key, int):
            return self.results[key]

        # Key is a QuantumCircuit or str: retrieve result by name.
        if isinstance(key, QuantumCircuit):
            key = key.name
        try:
            # TODO: look into result.name AND result.header.name?
            return next(result for result in self.results
                        if getattr(getattr(result, 'header', result),
                                   'name', '') == key)
        except StopIteration:
            raise QISKitError('Data for experiment "%s" could not be found.' %
                              key)

    # Methods to be moved to a module.

    def average_data(self, name, observable):
        """Compute the mean value of an diagonal observable."""
        # TODO: move to a module
        raise NotImplementedError

    def get_qubitpol_vs_xval(self, nqubits, xvals_dict=None):
        """Compute the polarization of each qubit for all circuits."""
        # TODO: move to a module
        raise NotImplementedError

    # Methods not covered by tests. Candidates for removal?

    # TODO: disabled for testing.
    # def __getitem__(self, i):
    #     return list(self.results.values())[i]

    def get_circuit_status(self, icircuit):
        """Return the status of circuit at index icircuit.

        Args:
            icircuit (int): index of circuit
        Returns:
            string: the status of the circuit.
        """
        return self[icircuit].status

    def get_job_id(self):
        """Return the job id assigned by the api if this is a remote job.

        Returns:
            string: a string containing the job id.
        """
        return self.job_id

    def get_ran_qasm(self, name):
        """Get the ran qasm for the named circuit and backend.

        Args:
            name (str): the name of the quantum circuit.

        Returns:
            string: A text version of the qasm file that has been run.
        Raises:
            QISKitError: if the circuit was not found.
        """
        try:
            return self.results[name].compiled_circuit_qasm
        except KeyError:
            raise QISKitError('No  qasm for circuit "{0}"'.format(name))

    def get_names(self):
        """Get the circuit names of the results.

        Returns:
            List: A list of circuit names.
        """
        return list(self.results.keys())
