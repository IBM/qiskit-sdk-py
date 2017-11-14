# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========================================================
"""Representation of a Quantum circuit Result."""

import copy
from enum import Enum

import numpy
from . import QISKitError


class Result(object):
    """Representation of the results of the execution of a quantum program.

    Attributes:
        _job_id (str): the identifier of the job that produced the result,
            issued by the backend the job is run on.
        _status (ResultStatus): the status of the execution.
        _qobj (Qobj): the quantum object that was executed.
        _result (list(dict)): list of results:

            [
                {
                "data":
                    {  #### DATA CAN BE A DIFFERENT DICTIONARY FOR EACH
                            BACKEND ####
                    "counts": {’00000’: XXXX, ’00001’: XXXXX},
                    "time"  : xx.xxxxxxxx
                    },
                "status": --status (string)--
                },
                ...
            ]
    """

    def __init__(self, job_id, status, qobj_result, qobj):
        self._job_id = job_id
        self._status = status
        self._qobj = qobj
        self._result = qobj_result

    def __str__(self):
        """Get the status of the run.

        Returns:
            str: the status of the results.
        """
        return self._status

    def __getitem__(self, i):
        return self._result[i]

    def __len__(self):
        return len(self._result)

    def __iadd__(self, other):
        """Append a Result object to current Result object.

        Arg:
            other (Result): a Result object to append.
        Returns:
            Result: The current object with appended results.
        Raises:
            QISKitError: if the result objects can't be combined.
        """
        # pylint: disable=protected-access
        if self._qobj.config == other._qobj.config:
            if isinstance(self._qobj.id_, str):
                self._qobj.id_ = [self._qobj.id_]
            self._qobj.id_.append(other._qobj.id_)

            self._qobj.circuits.extend(other._qobj.circuits)
            self._result += other._result
            return self
        else:
            raise QISKitError('Result objects have different configs and '
                              'cannot be combined.')

    def __add__(self, other):
        """Combine Result objects.

        Note that the qobj id of the returned result will be the same as the
        first result.

        Arg:
            other (Result): a Result object to combine.
        Returns:
            Result: A new Result object consisting of combined objects.
        """
        ret = copy.deepcopy(self)
        ret += other
        return ret

    def _is_error(self):
        return self._status == ResultStatus.ERROR.value

    def get_status(self):
        """Return whole qobj result status."""
        return self._status

    def circuit_statuses(self):
        """Return statuses of all circuits

        Return:
            list(str): List of status result strings.
        """
        return [circuit_result['status'] for circuit_result in self._result]

    def get_circuit_status(self, idx_circuit):
        """Return the status of circuit at index idx_circuit.

        Args:
            idx_circuit (int): index of circuit
        Return:
            str: the status of circuit at index idx_circuit.
        """
        return self._result[idx_circuit]['status']

    def get_job_id(self):
        """Return the job id assigned by the api if this is a remote job.

        Returns:
            str: a string containing the job id.
        """
        return self._job_id

    def get_ran_qasm(self, name):
        """Get the ran qasm for the named circuit and backend.

        Args:
            name (str): the name of the quantum circuit.

        Returns:
            str: A text version of the qasm file that has been run.
        Raises:
            QISKitError: if the circuit cannot be found.
        """
        try:
            return next(c.compiled_circuit_qasm for c in self._qobj.circuits
                        if c.name == name)
        except StopIteration:
            raise QISKitError('No  qasm for circuit "{0}"'.format(name))

    def get_data(self, name):
        """Get the data of circuit name.

        The data format will depend on the backend. For a real device it
        will be for the form::

            "counts": {’00000’: XXXX, ’00001’: XXXX},
            "time"  : xx.xxxxxxxx

        for the qasm simulators of 1 shot::

            'quantum_state': array([ XXX,  ..., XXX]),
            'classical_state': 0

        for the qasm simulators of n shots::

            'counts': {'0000': XXXX, '1001': XXXX}

        for the unitary simulators::

            'unitary': np.array([[ XX + XXj
                                   ...
                                   XX + XX]
                                 ...
                                 [ XX + XXj
                                   ...
                                   XX + XXj]]

        Args:
            name (str): the name of the quantum circuit.

        Returns:
            dict: A dictionary of data for the different backends.

        Raises:
            QISKitError: if the circuit cannot be found, or there is an error
                that is stored as a string in self._result.
            Exception: if there is an error that is stored as an Exception in
                self._result.
        """
        if self._is_error():
            exception = self._result
            if isinstance(exception, BaseException):
                raise exception
            else:
                raise QISKitError(str(exception))

        try:
            index = next(i for i, circuit in enumerate(self._qobj.circuits)
                         if circuit.name == name)
            return self._result[index]['data']
        except (KeyError, TypeError, StopIteration):
            raise QISKitError('No data for circuit "{0}"'.format(name))

    def get_counts(self, name):
        """Get the histogram data of circuit name.

        The data from the a qasm circuit is dictionary of the format
        {’00000’: XXXX, ’00001’: XXXXX}.

        Args:
            name (str): the name of the quantum circuit.
        Returns:
            Dictionary: Counts {’00000’: XXXX, ’00001’: XXXXX}.
        Raises:
            QISKitError: if the circuit cannot be found
        """
        try:
            return self.get_data(name)['counts']
        except (QISKitError, KeyError):
            raise QISKitError('No counts for circuit "{0}"'.format(name))

    def get_names(self):
        """Get the circuit names of the results.

        Returns:
            List: A list of circuit names.
        """
        return [c.name for c in self._qobj.circuits]

    def average_data(self, name, observable):
        """Compute the mean value of an diagonal observable.

        Takes in an observable in dictionary format and then
        calculates the sum_i value(i) P(i) where value(i) is the value of
        the observable for state i.

        Args:
            name (str): the name of the quantum circuit
            observable (dict): The observable to be averaged over. As an
                example ZZ on qubits equals
                {"00": 1, "11": 1, "01": -1, "10": -1}

        Returns:
            float: Average of the observable
        """
        counts = self.get_counts(name)
        temp = 0
        tot = sum(counts.values())
        for key in counts:
            if key in observable:
                temp += counts[key] * observable[key] / tot
        return temp

    def get_qubitpol_vs_xval(self, xvals_dict=None):
        """Compute the polarization of each qubit for all circuits and pull out
        each circuits xval into an array. Assumes that each circuit has the
        same number of qubits and that all qubits are measured.

        Args:
            xvals_dict (dict): xvals for each circuit
                {'circuitname1': xval1,...}. If this is None then the xvals
                list is just left as an array of zeros

        Returns:
            tuple(numpy.array, numpy.array):
                qubit_pol: mxn double array where m is the number of circuit,
                    n the number of qubits
                xvals: mx1 array of the circuit xvals
        """
        ncircuits = len(self._qobj.circuits)

        # TODO: Is this the best way to get the number of qubits?
        nqubits = self._qobj.circuits[0].\
            compiled_circuit['header']['number_of_qubits']
        qubitpol = numpy.zeros([ncircuits, nqubits], dtype=float)
        xvals = numpy.zeros([ncircuits], dtype=float)

        # build Z operators for each qubit
        z_dicts = []
        for qubit_ind in range(nqubits):
            z_dicts.append(dict())
            for qubit_state in range(2**nqubits):
                new_key = ("{0:0" + "{:d}".format(nqubits) + "b}").format(
                    qubit_state)
                z_dicts[-1][new_key] = -1
                if new_key[nqubits-qubit_ind-1] == '1':
                    z_dicts[-1][new_key] = 1

        # go through each circuit and for eqch qubit and apply the operators
        # using "average_data"
        for i in range(ncircuits):
            if xvals_dict:
                xvals[i] = xvals_dict[self._qobj.circuits[i].name]
            for qubit_ind in range(nqubits):
                qubitpol[i, qubit_ind] = self.average_data(
                    self._qobj.circuits[i].name, z_dicts[qubit_ind])

        return qubitpol, xvals


class ResultStatus(Enum):
    """Enumeration of the different status that a Result can have."""
    COMPLETED = 'COMPLETED'
    ERROR = 'ERROR'
