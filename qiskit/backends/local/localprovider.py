# -*- coding: utf-8 -*-
# pylint: disable=invalid-name

# Copyright 2018 IBM RESEARCH. All Rights Reserved.
#
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

"""Provider for local backends."""
import logging

from qiskit._qiskiterror import QISKitError
from qiskit.backends import BaseProvider
from .qasmsimulator import QasmSimulator
from .qasm_simulator_cpp import CliffordCppSimulator, QasmSimulatorCpp
from .projectq_simulator import ProjectQSimulator
from .sympy_unitarysimulator import SympyUnitarySimulator
from .sympy_qasmsimulator import SympyQasmSimulator
from .unitarysimulator import UnitarySimulator


logger = logging.getLogger(__name__)

SDK_STANDARD_BACKENDS = [
    CliffordCppSimulator,
    ProjectQSimulator,
    QasmSimulator,
    QasmSimulatorCpp,
    SympyQasmSimulator,
    SympyUnitarySimulator,
    UnitarySimulator
]


class LocalProvider(BaseProvider):
    """Provider for local backends."""
    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)

        # Populate the list of local backends.
        self.backends = self._verify_local_backends()

    def get_backend(self, name):
        return self.backends[name]

    def available_backends(self, filters=None):
        """
        Args:
            filters (dict): dictionary of filtering conditions.
        Returns:
            list[BaseBackend]: a list of backend names available from all the
                providers.
        """        
        # pylint: disable=arguments-differ
        backends = self.backends

        if isinstance(filters, dict):
            filters = [filters]

        for filter_ in filters:
            if isinstance(filter_, dict):
                for key, value in filter_.items():
                    backends = {name: instance for name, instance in backends.items()
                                if instance.configuration.get(key) == value}
        return list(backends.values())

    @classmethod
    def _verify_local_backends(cls):
        """
        Return the local backends in `SDK_STANDARD_BACKENDS` that are
        effectively available (as some of them might depend on the presence
        of an optional dependency or on the existence of a binary).

        Returns:
            dict[str:BaseBackend]: a dict of the local backends instances for
                the backends that could be instantiated, keyed by backend name.
        """
        ret = {}
        for backend_cls in SDK_STANDARD_BACKENDS:
            try:
                backend_instance = cls._get_backend_instance(backend_cls)
                backend_name = backend_instance.configuration['name']
                ret[backend_name] = backend_instance
            except QISKitError as e:
                # Ignore backends that could not be initialized.
                logger.info('local backend %s is not available: %s',
                            backend_cls, str(e))
        return ret

    @classmethod
    def _get_backend_instance(cls, backend_cls):
        """
        Return an instance of a backend from its class.

        Args:
            backend_cls (class): Backend class.
        Returns:
            BaseBackend: a backend instance.
        Raises:
            QISKitError: if the backend could not be instantiated or does not
                provide a valid configuration containing a name.
        """
        # Verify that the backend can be instantiated.
        try:
            backend_instance = backend_cls()
        except Exception as err:
            raise QISKitError('Backend %s could not be instantiated: %s' %
                              (cls, err))

        # Verify that the instance has a minimal valid configuration.
        try:
            _ = backend_instance.configuration['name']
        except (LookupError, TypeError):
            raise QISKitError('Backend %s has an invalid configuration')

        return backend_instance
