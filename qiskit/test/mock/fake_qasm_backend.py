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

"""
Fake backend abstract class for mock backends.
"""

import json
import os
from abc import ABC

from qiskit.providers.models import BackendProperties, QasmBackendConfiguration
from qiskit.test.mock.fake_backend import FakeBackend
from qiskit.test.mock.utils.json_decoder import decode_backend_configuration


class FakeQasmBackend(FakeBackend, ABC):
    """A fake qasm backend."""

    def __init__(self):
        configuration = self._get_conf_from_json()
        self._defaults = None
        self._properties = None
        super().__init__(configuration)

    def properties(self):
        """Returns a snapshot of device properties"""
        if not self._properties:
            self._set_props_from_json()
        return self._properties

    def _get_conf_from_json(self):
        conf = self._load_json(self.conf_filename)
        decode_backend_configuration(conf)
        configuration = self._get_config_from_dict(conf)
        configuration.backend_name = self.backend_name
        return configuration

    def _set_props_from_json(self):
        props = self._load_json(self.props_filename)
        self._properties = BackendProperties.from_dict(props)

    def _load_json(self, filename):
        with open(os.path.join(self.dirname, filename)) as f_json:
            the_json = json.load(f_json)
        return the_json

    def _get_config_from_dict(self, conf):
        return QasmBackendConfiguration.from_dict(conf)
