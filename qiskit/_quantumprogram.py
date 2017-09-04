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
# =============================================================================
"""
Qasm Program Class
"""
# pylint: disable=line-too-long
import time
import random
import json
import os
import string
import re
import copy
from threading import Event

# use the external IBMQuantumExperience Library
from IBMQuantumExperience.IBMQuantumExperience import IBMQuantumExperience

# Stable Modules
from . import QuantumRegister
from . import ClassicalRegister
from . import QuantumCircuit
from . import QISKitError
from . import JobProcessor
from . import QuantumJob

# Beta Modules
from . import unroll
from . import qasm
from . import mapper

# Local Simulator Modules
from . import simulators

import sys
sys.path.append("..")
import qiskit.extensions.standard

from qiskit import openquantumcompiler

first_cap_re = re.compile('(.)([A-Z][a-z]+)')
all_cap_re = re.compile('([a-z0-9])([A-Z])')


def convert(name):
    s1 = first_cap_re.sub(r'\1_\2', name)
    return all_cap_re.sub(r'\1_\2', s1).lower()


class QuantumProgram(object):
    """Quantum Program Class.

     Class internal properties.

     Elements that are not python identifiers or string constants are denoted
     by "--description (type)--". For example, a circuit's name is denoted by
     "--circuit name (string)--" and might have the value "teleport".

     Internal::

        __quantum_registers (list[dic]): An dictionary of quantum registers
            used in the quantum program.
            __quantum_registers =
                {
                --register name (string)--: QuantumRegistor,
                }
        __classical_registers (list[dic]): An ordered list of classical
            registers used in the quantum program.
            __classical_registers =
                {
                --register name (string)--: ClassicalRegistor,
                }
        __quantum_program (dic): An dictionary of quantum circuits
            __quantum_program =
                {
                --circuit name (string)--:  --circuit object --,
                }
        __init_circuit (obj): A quantum circuit object for the initial quantum
            circuit
        __ONLINE_BACKENDS (list[str]): A list of online backends
        __LOCAL_BACKENDS (list[str]): A list of local backends
     """
    # -- FUTURE IMPROVEMENTS --
    # TODO: for status results make ALL_CAPS (check) or some unified method
    # TODO: Jay: coupling_map, basis_gates will move into a config object
    # only exists once you set the api to use the online backends
    __api = {}
    __api_config = {}

    def __init__(self, specs=None):
        self.__quantum_registers = {}
        self.__classical_registers = {}
        self.__quantum_program = {}  # stores all the quantum programs
        self.__init_circuit = None  # stores the intial quantum circuit of the
        # program
        self.__ONLINE_BACKENDS = []
        self.__LOCAL_BACKENDS = self.local_backends()
        self.mapper = mapper
        if specs:
            self.__init_specs(specs)

        self.callback = None
        self.results = []
        self.results_ready_event = Event()

    ###############################################################
    # methods to initiate an build a quantum program
    ###############################################################

    def __init_specs(self, specs, verbose=False):
        """Populate the Quantum Program Object with initial Specs.

        Args:
            specs (dict):
                    Q_SPECS = {
                        "circuits": [{
                            "name": "Circuit",
                            "quantum_registers": [{
                                "name": "qr",
                                "size": 4
                            }],
                            "classical_registers": [{
                                "name": "cr",
                                "size": 4
                            }]
                        }],
            verbose (bool): controls how information is returned.

        Returns:
            Sets up a quantum circuit.
        """
        quantumr = []
        classicalr = []
        if "circuits" in specs:
            for circuit in specs["circuits"]:
                quantumr = self.create_quantum_registers(
                    circuit["quantum_registers"])
                classicalr = self.create_classical_registers(
                    circuit["classical_registers"])
                self.create_circuit(name=circuit["name"], qregisters=quantumr,
                                    cregisters=classicalr)
        # TODO: Jay: I think we should return function handles for the
        # registers and circuit. So that we dont need to get them after we
        # create them with get_quantum_register etc

    def create_quantum_register(self, name, size, verbose=False):
        """Create a new Quantum Register.

        Args:
            name (str): the name of the quantum register
            size (int): the size of the quantum register
            verbose (bool): controls how information is returned.

        Returns:
            internal reference to a quantum register in __quantum_register s
        """
        if name in self.__quantum_registers:
            if size != len(self.__quantum_registers[name]):
                raise QISKitError("Can't make this register: Already in"
                                  " program with different size")
            if verbose is True:
                print(">> quantum_register exists:", name, size)
        else:
            if verbose is True:
                print(">> new quantum_register created:", name, size)
            self.__quantum_registers[name] = QuantumRegister(name, size)
        return self.__quantum_registers[name]

    def create_quantum_registers(self, register_array):
        """Create a new set of Quantum Registers based on a array of them.

        Args:
            register_array (list[dict]): An array of quantum registers in
                dictionay format::

                    "quantum_registers": [
                        {
                        "name": "qr",
                        "size": 4
                        },
                        ...
                    ]
        Returns:
            Array of quantum registers objects
        """
        new_registers = []
        for register in register_array:
            register = self.create_quantum_register(
                register["name"], register["size"])
            new_registers.append(register)
        return new_registers

    def create_classical_register(self, name, size, verbose=False):
        """Create a new Classical Register.

        Args:
            name (str): the name of the quantum register
            size (int): the size of the quantum register
            verbose (bool): controls how information is returned.
        Returns:
            internal reference to a quantum register in __quantum_register
        """
        if name in self.__classical_registers:
            if size != len(self.__classical_registers[name]):
                raise QISKitError("Can't make this register: Already in"
                                  " program with different size")
            if verbose is True:
                print(">> classical register exists:", name, size)
        else:
            if verbose is True:
                print(">> new classical register created:", name, size)
            self.__classical_registers[name] = ClassicalRegister(name, size)
        return self.__classical_registers[name]

    def create_classical_registers(self, registers_array):
        """Create a new set of Classical Registers based on a array of them.

        Args:
            register_array (list[dict]): An array of classical registers in
                dictionay fromat::

                    "classical_registers": [
                        {
                        "name": "qr",
                        "size": 4
                        },
                        ...
                    ]
        Returns:
            Array of clasical registers objects
        """
        new_registers = []
        for register in registers_array:
            new_registers.append(self.create_classical_register(
                register["name"], register["size"]))
        return new_registers

    def create_circuit(self, name, qregisters=None, cregisters=None):
        """Create a empty Quantum Circuit in the Quantum Program.

        Args:
            name (str): the name of the circuit
            qregisters list(object): is an Array of Quantum Registers by object
                reference
            cregisters list(object): is an Array of Classical Registers by
                object reference

        Returns:
            A quantum circuit is created and added to the Quantum Program
        """
        if not qregisters:
            qregisters = []
        if not cregisters:
            cregisters = []
        quantum_circuit = QuantumCircuit()
        if not self.__init_circuit:
            self.__init_circuit = quantum_circuit
        for register in qregisters:
            quantum_circuit.add(register)
        for register in cregisters:
            quantum_circuit.add(register)
        self.add_circuit(name, quantum_circuit)
        return self.__quantum_program[name]

    def add_circuit(self, name, quantum_circuit):
        """Add a new circuit based on an Object representation.

        Args:
            name (str): the name of the circuit to add.
            quantum_circuit: a quantum circuit to add to the program-name
        Returns:
            the quantum circuit is added to the object.
        """
        for qname, qreg in quantum_circuit.get_qregs().items():
            self.create_quantum_register(qname, len(qreg))
        for cname, creg in quantum_circuit.get_cregs().items():
            self.create_classical_register(cname, len(creg))
        self.__quantum_program[name] = quantum_circuit

    def load_qasm_file(self, qasm_file, name=None, verbose=False):
        """ Load qasm file into the quantum program.

        Args:
            qasm_file (str): a string for the filename including its location.
            name (str or None, optional): the name of the quantum circuit after
                loading qasm text into it. If no name is give the name is of
                the text file.
            verbose (bool, optional): controls how information is returned.
        Retuns:
            Adds a quantum circuit with the gates given in the qasm file to the
            quantum program and returns the name to be used to get this circuit
        """
        if not os.path.exists(qasm_file):
            raise QISKitError('qasm file "{0}" not found'.format(qasm_file))
        if not name:
            name = os.path.splitext(os.path.basename(qasm_file))[0]
        node_circuit = qasm.Qasm(filename=qasm_file).parse()  # Node (AST)
        if verbose is True:
            print("circuit name: " + name)
            print("******************************")
            print(node_circuit.qasm())
        # current method to turn it a DAG quantum circuit.
        basis_gates = "u1,u2,u3,cx,id"  # QE target basis
        unrolled_circuit = unroll.Unroller(node_circuit,
                                           unroll.CircuitBackend(basis_gates.split(",")))
        circuit_unrolled = unrolled_circuit.execute()
        self.add_circuit(name, circuit_unrolled)
        return name

    def load_qasm_text(self, qasm_string, name=None, verbose=False):
        """ Load qasm string in the quantum program.

        Args:
            qasm_string (str): a string for the file name.
            name (str): the name of the quantum circuit after loading qasm
                text into it. If no name is give the name is of the text file.
            verbose (bool): controls how information is returned.
        Retuns:
            Adds a quantum circuit with the gates given in the qasm string to
            the quantum program.
        """
        node_circuit = qasm.Qasm(data=qasm_string).parse()  # Node (AST)
        if not name:
            # Get a random name if none is give
            name = "".join([random.choice(string.ascii_letters+string.digits)
                            for n in range(10)])
        if verbose is True:
            print("circuit name: " + name)
            print("******************************")
            print(node_circuit.qasm())
        # current method to turn it a DAG quantum circuit.
        basis_gates = "u1,u2,u3,cx,id"  # QE target basis
        unrolled_circuit = unroll.Unroller(node_circuit,
                                           unroll.CircuitBackend(basis_gates.split(",")))
        circuit_unrolled = unrolled_circuit.execute()
        self.add_circuit(name, circuit_unrolled)
        return name

    ###############################################################
    # methods to get elements from a QuantumProgram
    ###############################################################

    def get_quantum_register(self, name):
        """Return a Quantum Register by name.

        Args:
            name (str): the name of the quantum circuit
        Returns:
            The quantum registers with this name
        """
        try:
            return self.__quantum_registers[name]
        except KeyError:
            raise KeyError('No quantum register "{0}"'.format(name))

    def get_classical_register(self, name):
        """Return a Classical Register by name.

        Args:
            name (str): the name of the quantum circuit
        Returns:
            The classical registers with this name
        """
        try:
            return self.__classical_registers[name]
        except KeyError:
            raise KeyError('No classical register "{0}"'.format(name))

    def get_quantum_register_names(self):
        """Return all the names of the quantum Registers."""
        return self.__quantum_registers.keys()

    def get_classical_register_names(self):
        """Return all the names of the classical Registers."""
        return self.__classical_registers.keys()

    def get_circuit(self, name):
        """Return a Circuit Object by name
        Args:
            name (str): the name of the quantum circuit
        Returns:
            The quantum circuit with this name
        """
        try:
            return self.__quantum_program[name]
        except KeyError:
            raise KeyError('No quantum circuit "{0}"'.format(name))

    def get_circuit_names(self):
        """Return all the names of the quantum circuits."""
        return self.__quantum_program.keys()

    def get_qasm(self, name):
        """Get qasm format of circuit by name.

        Args:
            name (str): name of the circuit

        Returns:
            The quantum circuit in qasm format
        """
        quantum_circuit = self.get_circuit(name)
        return quantum_circuit.qasm()

    def get_qasms(self, list_circuit_name):
        """Get qasm format of circuit by list of names.

        Args:
            list_circuit_name (list[str]): names of the circuit

        Returns:
            List of quantum circuit in qasm format
        """
        qasm_source = []
        for name in list_circuit_name:
            qasm_source.append(self.get_qasm(name))
        return qasm_source

    def get_initial_circuit(self):
        """Return the initialization Circuit."""
        return self.__init_circuit

    ###############################################################
    # methods for working with backends
    ###############################################################

    def set_api(self, token, url, verify=True):
        """ Setup the API.

        Does not catch exceptions from IBMQuantumExperience.

        Args:
            Token (str): The token used to register on the online backend such
                as the quantum experience.
            URL (str): The url used for online backend such as the quantum
                experience.
        Returns:
            Nothing but fills the __ONLINE_BACKENDS, __api, and __api_config
        """
        self.__api = IBMQuantumExperience(token, {"url": url}, verify)
        self.__ONLINE_BACKENDS = self.online_backends()
        self.__api_config["token"] = token
        self.__api_config["url"] = {"url": url}

    def get_api_config(self):
        """Return the program specs."""
        return self.__api_config

    def get_api(self):
        """Returns a function handle to the API."""
        return self.__api

    def save(self, file_name=None, beauty=False):
        """ Save Quantum Program in a Json file.

        Args:
            file_name (str): file name and path.
            beauty (boolean): save the text with indent 4 to make it readable.

        Returns:
            The dictionary with the status and result of the operation

        Raises:
            When you don't provide a correct file name
                raise a LookupError.
            When something happen with the file management
                raise a LookupError.
        """
        if file_name is None:
            error = {"status": "Error", "result": "Not filename provided"}
            raise LookupError(error['result'])

        if beauty:
            indent = 4
        else:
            indent = 0

        elemements_to_save = self.__quantum_program
        elements_saved = {}

        for circuit in elemements_to_save:
            elements_saved[circuit] = {}
            elements_saved[circuit]["qasm"] = elemements_to_save[circuit].qasm()

        try:
            with open(file_name, 'w') as save_file:
                json.dump(elements_saved, save_file, indent=indent)
            return {'status': 'Done', 'result': elemements_to_save}
        except ValueError:
            error = {'status': 'Error', 'result': 'Some Problem happened to save the file'}
            raise LookupError(error['result'])

    def load(self, file_name=None):
        """ Load Quantum Program Json file into the Quantum Program object.

        Args:
            file_name (str): file name and path.

        Returns:
            The dictionary with the status and result of the operation

        Raises:
            When you don't provide a correct file name
                raise a LookupError.
            When something happen with the file management
                raise a LookupError.
        """
        if file_name is None:
            error = {"status": "Error", "result": "Not filename provided"}
            raise LookupError(error['result'])

        elemements_to_load = {}

        try:
            with open(file_name, 'r') as load_file:
                elemements_loaded = json.load(load_file)

            for circuit in elemements_loaded:
                circuit_qasm = elemements_loaded[circuit]["qasm"]
                elemements_loaded[circuit] = qasm.Qasm(data=circuit_qasm).parse()
            self.__quantum_program = elemements_loaded

            return {"status": 'Done', 'result': self.__quantum_program}

        except ValueError:
            error = {'status': 'Error', 'result': 'Some Problem happened to load the file'}
            raise LookupError(error['result'])

    def available_backends(self):
        """All the backends that are seen by QISKIT."""
        return self.__ONLINE_BACKENDS + self.__LOCAL_BACKENDS

    def local_backends(self):
        """Get the local backends."""
        return simulators._localsimulator.local_backends()

    def online_backends(self):
        """Get the online backends.

        Queries network API if it exists and gets the backends that are online.

        Returns:
            List of online backends if the online api has been set or an empty
            list of it has not been set.
        """
        if self.get_api():
            try:
                return [backend['name'] for backend in self.__api.available_backends() ]
            except Exception as ex:
                return []
        else:
            return []

    def online_simulators(self):
        """Gets online simulators via QX API calls.

        Returns:
            List of online simulator names.
        """
        simulators = []
        if self.get_api():
            for backend in self.__api.available_backends():
                if backend['simulator']:
                    simulators.append(backend['name'])
        return simulators

    def online_devices(self):
        """Gets online devices via QX API calls.

        Returns:
            List of online simulator names.
        """
        devices = []
        if self.get_api():
            for backend in self.__api.available_backends():
                if not backend['simulator']:
                    devices.append(backend['name'])
        return devices

    def get_backend_status(self, backend):
        """Return the online backend status.

        It uses QX API call or by local backend is the name of the
        local or online simulator or experiment.

        Args:
            banckend (str): The backend to check
        """

        if backend in self.__ONLINE_BACKENDS:
            return self.__api.backend_status(backend)
        elif backend in self.__LOCAL_BACKENDS:
            return {'available': True}
        else:
            err_str = 'the backend "{0}" is not available'.format(backend)
            raise ValueError(err_str)

    def get_backend_configuration(self, backend, list_format=False):
        """Return the configuration of the backend.

        The return is via QX API call.

        Args:
            backend (str):  Name of the backend.

        Returns:
            The configuration of the named backend.

        Raises:
            If a configuration for the named backend can't be found
            raise a LookupError.
        """
        if self.get_api():
            configuration_edit = {}
            for configuration in self.__api.available_backends():
                if configuration['name'] == backend:
                    for key in configuration:
                        new_key = convert(key)
                        # TODO: removed these from the API code
                        if new_key not in ['id', 'serial_number', 'topology_id',
                                           'status', 'coupling_map']:
                            configuration_edit[new_key] = configuration[key]
                        if new_key == 'coupling_map':
                            if configuration[key] == 'all-to-all':
                                configuration_edit[new_key] = \
                                    configuration[key]
                            else:
                                if not list_format:
                                    cmap = mapper.coupling_list2dict(
                                                configuration[key])
                                else:
                                    cmap = configuration[key]
                                configuration_edit[new_key] = cmap
                    return configuration_edit
        for configuration in simulators.local_configuration:
            if configuration['name'] == backend:
                return configuration
        raise LookupError(
            'backend configuration for "{0}" not found'.format(backend))

    def get_backend_calibration(self, backend):
        """Return the online backend calibrations.

        The return is via QX API call.

        Args:
            backend (str):  Name of the backend.

        Returns:
            The configuration of the named backend.

        Raises:
            If a configuration for the named backend can't be found
            raise a LookupError.
        """
        if backend in self.__ONLINE_BACKENDS:
            calibrations = self.__api.backend_calibration(backend)
            calibrations_edit = {}
            for key, vals in calibrations.items():
                new_key = convert(key)
                calibrations_edit[new_key] = vals
            return calibrations_edit
        elif  backend in self.__LOCAL_BACKENDS:
            return {'backend': backend, 'calibrations': None}
        else:
            raise LookupError(
                'backend calibration for "{0}" not found'.format(backend))

    def get_backend_parameters(self, backend):
        """Return the online backend parameters.

        The return is via QX API call.

        Args:
            backend (str):  Name of the backend.

        Returns:
            The configuration of the named backend.

        Raises:
            If a configuration for the named backend can't be found
            raise a LookupError.
        """
        if backend in self.__ONLINE_BACKENDS:
            parameters = self.__api.backend_parameters(backend)
            parameters_edit = {}
            for key, vals in parameters.items():
                new_key = convert(key)
                parameters_edit[new_key] = vals
            return parameters_edit
        elif backend in self.__LOCAL_BACKENDS:
            return {'backend': backend, 'parameters': None}
        else:
            raise LookupError(
                'backend parameters for "{0}" not found'.format(backend))

    ###############################################################
    # methods to compile quantum programs into q_object
    ###############################################################

    def compile(self, name_of_circuits, backend="local_qasm_simulator",
                config=None, silent=True, basis_gates=None, coupling_map=None,
                initial_layout=None, shots=1024, max_credits=3, seed=None,
                q_objectid=None):
        """Compile the circuits into the exectution list.

        This builds the internal "to execute" list which is list of quantum
        circuits to run on different backends.

        Args:
            name_of_circuits (list[str]): circuit names to be compiled.
            backend (str): a string representing the backend to compile to
            config (dict): a dictionary of configurations parameters for the
                compiler
            silent (bool): is an option to print out the compiling information
                or not
            basis_gates (str): a comma seperated string and are the base gates,
                               which by default are: u1,u2,u3,cx,id
            coupling_map (dict): A directed graph of coupling::

                {
                 control(int):
                     [
                         target1(int),
                         target2(int),
                         , ...
                     ],
                     ...
                }

                eg. {0: [2], 1: [2], 3: [2]}

            initial_layout (dict): A mapping of qubit to qubit::

                                  {
                                    ("q", strart(int)): ("q", final(int)),
                                    ...
                                  }
                                  eg.
                                  {
                                    ("q", 0): ("q", 0),
                                    ("q", 1): ("q", 1),
                                    ("q", 2): ("q", 2),
                                    ("q", 3): ("q", 3)
                                  }

            shots (int): the number of shots
            max_credits (int): the max credits to use 3, or 5
            seed (int): the intial seed the simulatros use

        Returns:
            the job id and populates the q_object::

            q_object =
                {
                    id: --job id (string),
                    config: -- dictionary of config settings (dict)--,
                        {
                        "max_credits" (online only): -- credits (int) --,
                        "shots": -- number of shots (int) --.
                        "backend": -- backend name (str) --
                        }
                    circuits:
                        [
                            {
                            "name": --circuit name (string)--,
                            "compiled_circuit": --compiled quantum circuit (JSON format)--,
                            "compiled_circuit_qasm": --compiled quantum circuit (QASM format)--,
                            "config": --dictionary of additional config settings (dict)--,
                                {
                                "coupling_map": --adjacency list (dict)--,
                                "basis_gates": --comma separated gate names (string)--,
                                "layout": --layout computed by mapper (dict)--,
                                "seed": (simulator only)--initial seed for the simulator (int)--,
                                }
                            },
                            ...
                        ]
                    }

        """
        # TODO: Jay: currently basis_gates, coupling_map, initial_layout,
        # shots, max_credits and seed are extra inputs but I would like
        # them to go into the config.

        q_object = {}
        if not q_objectid:
            q_objectid = "".join([random.choice(string.ascii_letters+string.digits)
                              for n in range(30)])
        q_object['id'] = q_objectid
        q_object["config"] = {"max_credits": max_credits, 'backend': backend,
                          "shots": shots}
        q_object["circuits"] = []

        if not name_of_circuits:
            raise ValueError('"name_of_circuits" must be specified')
        if isinstance(name_of_circuits, str):
            name_of_circuits = [name_of_circuits]
        for name in name_of_circuits:
            if name not in self.__quantum_program:
                raise QISKitError('circuit "{0}" not found in program'.format(name))
            if not basis_gates:
                basis_gates = "u1,u2,u3,cx,id"  # QE target basis
            # TODO: The circuit object going into this is to have .qasm() method (be careful)
            circuit = self.__quantum_program[name]
            dag_circuit, final_layout = openquantumcompiler.compile(circuit.qasm(),
                                                    basis_gates=basis_gates,
                                                    coupling_map=coupling_map,
                                                    initial_layout=initial_layout,
                                                    silent=silent, get_layout=True)
            # making the job to be added to q_object
            job = {}
            job["name"] = name
            # config parameters used by the runner
            if config is None:
                config = {}  # default to empty config dict
            job["config"] = config
            # TODO: Jay: make config options optional for different backends
            job["config"]["coupling_map"] = mapper.coupling_dict2list(coupling_map)
            # Map the layout to a format that can be json encoded
            list_layout = None
            if final_layout:
                list_layout = [[k, v] for k, v in final_layout.items()]
            job["config"]["layout"] = list_layout
            job["config"]["basis_gates"] = basis_gates
            if seed is None:
                job["config"]["seed"] = None
            else:
                job["config"]["seed"] = seed
            # the compiled circuit to be run saved as a dag
            job["compiled_circuit"] = openquantumcompiler.dag2json(dag_circuit)
            job["compiled_circuit_qasm"] = dag_circuit.qasm(qeflag=True)
            # add job to the q_object
            q_object["circuits"].append(job)
        return q_object

    def get_execution_list(self, q_object, verbose=False):
        """Print the compiled circuits that are ready to run.

        Args:
            verbose (bool): controls how much is returned.
        """
        if not q_object:
            if verbose:
                print("no exectuions to run")
        execution_list_all = {}
        execution_list = []
        if verbose:
            print("id: %s" % q_object['id'])
            print("backend: %s" % q_object['config']['backend'])
            print("q_object config:")
            for key in q_object['config']:
                if key != 'backend':
                    print(' '+ key + ': ' + str(q_object['config'][key]))
        for circuit in q_object['circuits']:
            execution_list.append(circuit["name"])
            if verbose:
                print('  circuit name: ' + circuit["name"])
                print('  circuit config:')
                for key in circuit['config']:
                    print('   '+ key + ': ' + str(circuit['config'][key]))
        return execution_list

    def get_compiled_configuration(self, q_object, name):
        """Get the compiled layout for the named circuit and backend.

        Args:
            name (str):  the circuit name
            q_object (str): the name of the q_object

        Returns:
            the config of the circuit.
        """
        try:
            for index in range(len(q_object["circuits"])):
                if q_object["circuits"][index]['name'] == name:
                    return q_object["circuits"][index]["config"]
        except KeyError:
            raise QISKitError('No compiled configurations for circuit "{0}"'.format(name))

    def get_compiled_qasm(self, q_object, name):
        """Print the compiled cricuit in qasm format.

        Args:
            q_object (str): the name of the q_object
            name (str): name of the quantum circuit

        """
        try:
            for index in range(len(q_object["circuits"])):
                if q_object["circuits"][index]['name'] == name:
                    return q_object["circuits"][index]["compiled_circuit_qasm"]
        except KeyError:
            raise QISKitError('No compiled qasm for circuit "{0}"'.format(name))

    ###############################################################
    # methods to run quantum programs (run )
    ###############################################################

    # TODO Async: Timeout management
    def run(self, q_objecty, wait=5, timeout=60, silent=True):
        """Run a program (a pre-compiled quantum program) asynchronously. This
           function will return inmediately.

        All input for run comes from q_object.

        Args:
            q_objecty(dict|list(dict)): the dictionary of the quantum object to
                run or list of q_object.
            wait (int): wait time is how long to check if the job is completed
            timeout (int): is time until the execution stops
            silent (bool): is an option to print out the running information or
            not

        Returns:
            status done and populates the internal __quantum_program with the
            data

        """
        self.callback = None
        self._run_internal(q_objecty, wait, timeout, silent)
        self.wait_for_results(timeout)
        # TODO Don't really like that. Input and Output arguments should be
        # allways from the same type. Returning a list or an element of the list
        # depending on the type of input, adds complexity so error-prone code
        if isinstance(q_objecty, dict): # ... so not a List
            return self.results[0] if self.results != None else None
        else:
            return self.results

    # TODO Async: Timeout management
    def run_async(self, q_objecty, callback, wait=5, timeout=60, silent=True):
        """Run a program (a pre-compiled quantum program) asynchronously. This
           function will return inmediately.

        All input for run comes from q_object.

        Args:
            q_objecty(dict|list(dict)): the dictionary of the quantum object to
                run or list of q_object.
            callback: A function with signature: fn(results=None, error=None)
                If there were no errors, results param will be set to a list of
                Result objects, one Result per Job, and error param will be set
                to None. If there was an error, error param will contain a
                string explaning what happened and results param will be set to
                an empty list.
            wait (int): wait time is how long to check if the job is completed
            timeout (int): is time until the execution stops
            silent (bool): is an option to print out the running information or
            not

        Returns:
            status done and populates the internal __quantum_program with the
            data

        """
        self.callback = callback
        self._run_internal(q_objecty, wait, timeout, silent)


    def _run_internal(self, q_objecty, wait=5, timeout=60, silent=True):
        q_object_list = q_objecty
        if isinstance(q_objecty, dict):
            q_object_list = [q_objecty]

        q_job_list = []
        for q_object in q_object_list:
            q_job = QuantumJob(q_object, preformatted=True)
            q_job_list.append(q_job)

        jp = JobProcessor(q_job_list, max_workers=5, api=self.__api, callback=self._jobs_done_callback)
        jp.submit()


    def _jobs_done_callback(self, job_results):
        """ This internal callback will be called once all Jobs submitted have
            finished. NOT every time a job has finished."""
        results = []
        for result, q_object in job_results:
            results.append(Result(result, q_object))
        if self.callback != None:
            # call user callback with the proper parameter
            self.callback(results)
        else:
            self.results = results
            self.results_ready_event.set()

    def wait_for_results(self, timeout):
        is_ok = self.results_ready_event.wait(timeout)
        self.results_ready_event.clear()
        if is_ok == False:
            raise QISKitError("""Error waiting for Job results: Timeout after %d
                    seconds. """ % timeout)

    def execute(self, name_of_circuits, backend="local_qasm_simulator",
                config=None, wait=5, timeout=60, silent=True, basis_gates=None,
                coupling_map=None, initial_layout=None, shots=1024,
                max_credits=3, seed=None):

        """Execute, compile, and run an array of quantum circuits).

        This builds the internal "to execute" list which is list of quantum
        circuits to run on different backends.

        Args:
            name_of_circuits (list[str]): circuit names to be compiled.
            backend (str): a string representing the backend to compile to
            config (dict): a dictionary of configurations parameters for the
                compiler
            wait (int): wait time is how long to check if the job is completed
            timeout (int): is time until the execution stops
            silent (bool): is an option to print out the compiling information
            or not
            basis_gates (str): a comma seperated string and are the base gates,
                               which by default are: u1,u2,u3,cx,id
            coupling_map (dict): A directed graph of coupling::

                                {
                                control(int):
                                    [
                                        target1(int),
                                        target2(int),
                                        , ...
                                    ],
                                    ...
                                }
                                eg. {0: [2], 1: [2], 3: [2]}
            initial_layout (dict): A mapping of qubit to qubit
                                  {
                                  ("q", strart(int)): ("q", final(int)),
                                  ...
                                  }
                                  eg.
                                  {
                                  ("q", 0): ("q", 0),
                                  ("q", 1): ("q", 1),
                                  ("q", 2): ("q", 2),
                                  ("q", 3): ("q", 3)
                                  }
            shots (int): the number of shots
            max_credits (int): the max credits to use 3, or 5
            seed (int): the intial seed the simulatros use

        Returns:
            status done and populates the internal __quantum_program with the
            data
        """
        # TODO: Jay: currently basis_gates, coupling_map, intial_layout, shots,
        # max_credits, and seed are extra inputs but I would like them to go
        # into the config
        q_object = self.compile(name_of_circuits, backend=backend, config=config,
                     silent=silent, basis_gates=basis_gates,
                     coupling_map=coupling_map, initial_layout=initial_layout,
                     shots=shots, max_credits=max_credits, seed=seed)
        result = self.run(q_object, wait=wait, timeout=timeout, silent=silent)
        return result


class Result(object):
    """ Result Class.

    Class internal properties.

    Methods to process the quantum program after it has been run

    Internal::

        q_object =  { -- the quantum object that was complied --}
        result =
            [
                {
                "data":
                    {  #### DATA CAN BE A DIFFERENT DICTIONARY FOR EACH BACKEND ####
                    "counts": {’00000’: XXXX, ’00001’: XXXXX},
                    "time"  : xx.xxxxxxxx
                    },
                "status": --status (string)--
                },
                ...
            ]
    """

    def __init__(self, q_object_result, q_object):
        self.__q_object = q_object
        self.__result = q_object_result

    def __str__(self):
        """Get the status of the run.

        Returns:
            the status of the results.
        """
        return self.__result['status']

    def __iadd__(self, other):
        """Append a Result object to current Result object.

        Arg:
            other (Result): a Result object to append.
        Returns:
            The current object with appended results.
        """
        if self.__q_object['config'] == other.__q_object['config']:
            if isinstance(self.__q_object['id'], str):
                self.__q_object['id'] = [self.__q_object['id']]
            self.__q_object['id'].append(other.__q_object['id'])
            self.__q_object['circuits'] += other.__q_object['circuits']
            self.__result['result'] += other.__result['result']
            return self
        else:
            raise QISKitError('Result objects have different configs and cannot be combined.')

    def __add__(self, other):
        """Combine Result objects.

        Note that the q_object id of the returned result will be the same as the
        first result.

        Arg:
            other (Result): a Result object to combine.
        Returns:
            A new Result object consisting of combined objects.
        """
        ret = copy.deepcopy(self)
        ret += other
        return ret

    def get_error(self):
        if self.__result['status'] == 'ERROR':
            return self.__result['result']
        else:
            return None

    def get_ran_qasm(self, name):
        """Get the ran qasm for the named circuit and backend.

        Args:
            name (str): the name of the quantum circuit.

        Returns:
            A text version of the qasm file that has been run.
        """
        try:
            q_object = self.__q_object
            for index in range(len(q_object["circuits"])):
                if q_object["circuits"][index]['name'] == name:
                    return q_object["circuits"][index]["compiled_circuit_qasm"]
        except KeyError:
            raise QISKitError('No  qasm for circuit "{0}"'.format(name))

    def get_data(self, name):
        """Get the data of cicuit name.

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
            A dictionary of data for the different backends.
        """
        try:
            q_object = self.__q_object
            for index in range(len(q_object['circuits'])):
                if q_object['circuits'][index]['name'] == name:
                    return self.__result['result'][index]['data']
        except (KeyError, TypeError) as err:
            print(err)
            raise QISKitError('No data for circuit "{0}"'.format(name))

    def get_counts(self, name):
        """Get the histogram data of cicuit name.

        The data from the a qasm circuit is dictionary of the format
        {’00000’: XXXX, ’00001’: XXXXX}.

        Args:
            name (str): the name of the quantum circuit.
            backend (str): the name of the backend the data was run on.

        Returns:
            A dictionary of counts {’00000’: XXXX, ’00001’: XXXXX}.
        """
        try:
            return self.get_data(name)['counts']
        except KeyError:
            raise QISKitError('No counts for circuit "{0}"'.format(name))

    def average_data(self, name, observable):
        """Compute the mean value of an diagonal observable.

        Takes in an observable in dictionary format and then
        calculates the sum_i value(i) P(i) where value(i) is the value of
        the observable for state i.

        Args:
            name (str): the name of the quantum circuit
            obsevable (dict): The observable to be averaged over. As an example
            ZZ on qubits equals {"00": 1, "11": 1, "01": -1, "10": -1}

        Returns:
            a double for the average of the observable
        """
        counts = self.get_counts(name)
        temp = 0
        tot = sum(counts.values())
        for key in counts:
            if key in observable:
                temp += counts[key] * observable[key] / tot
        return temp


class ResultError(QISKitError):
    """Exceptions raised due to errors in result output.

    It may be better for the QISKit API to raise this exception.

    Args:
        error (dict): This is the error record as it comes back from
            the API. The format is like::

                error = {'status': 403,
                         'message': 'Your credits are not enough.',
                         'code': 'MAX_CREDITS_EXCEEDED'}
    """
    def __init__(self, error):
        self.status = error['status']
        self.message = error['message']
        self.code = error['code']
