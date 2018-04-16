# -*- coding: utf-8 -*-

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

"""Provider for remote IbmQ backends."""
from IBMQuantumExperience import IBMQuantumExperience

from qiskit._util import _snake_case_to_camel_case
from qiskit.backends.baseprovider import BaseProvider
from .ibmqbackend import IBMQBackend
from qiskit import QISKitError


class IBMQProvider(BaseProvider):
    """Provider for remote IbmQ backends."""
    def __init__(self, token, url='https://quantumexperience.ng.bluemix.net/api',
                 hub=None, group=None, project=None, proxies=None, verify=True):
        super().__init__()

        # Get a connection to IBMQuantumExperience.
        self._api = self._authenticate(token, url,
                                       hub, group, project, proxies, verify)

        # Populate the list of remote backends.
        self.backends = self._discover_remote_backends()

    def get_backend(self, name):
        return self.backends[name]

    def available_backends(self, *filters):
        # pylint: disable=arguments-differ
        backends = self.backends
        
        for filter_ in filters:
            if isinstance(filter_, dict):
                for key, value in filter_.items():
                    backends = {name: instance for name, instance in backends.items()
                                if instance.configuration.get(key) == value}
            elif callable(filter_):
                filter_(backends)
            else:
                raise QISKitError('backend filters must be either dict or callable.')

        return list(backends.values())

    @classmethod
    def _authenticate(cls, token, url,
                      hub=None, group=None, project=None, proxies=None,
                      verify=True):
        """
        Authenticate against the IBMQuantumExperience API.

        Returns:
            IBMQuantumExperience.IBMQuantumExperience.IBMQuantumExperience:
                instance of the IBMQuantumExperience API.
        Raises:
            ConnectionError: if the authentication resulted in error.
        """
        try:
            config_dict = {
                'url': url,
            }
            # Only append hub/group/project if they are different than None.
            if all([hub, group, project]):
                config_dict.update({
                    'hub': hub,
                    'group': group,
                    'project': project
                })
            if proxies:
                config_dict['proxies'] = proxies
            return IBMQuantumExperience(token, config_dict, verify)
        except Exception as ex:
            root_exception = ex
            if 'License required' in str(ex):
                # For the 401 License required exception from the API, be
                # less verbose with the exceptions.
                root_exception = None
            raise ConnectionError("Couldn't connect to IBMQuantumExperience server: {0}"
                                  .format(ex)) from root_exception

    @classmethod
    def _parse_backend_configuration(cls, config):
        """
        Parse a backend configuration returned by IBMQuantumConfiguration.

        Args:
            config (dict): raw configuration as returned by
                IBMQuantumExperience.

        Returns:
            dict: parsed configuration.
        """
        edited_config = {
            'local': False
        }

        for key in config.keys():
            new_key = _snake_case_to_camel_case(key)
            if new_key not in ['id', 'serial_number', 'topology_id',
                               'status']:
                edited_config[new_key] = config[key]

        # ibmqx_qasm_simulator doesn't report coupling_map
        if 'coupling_map' not in edited_config.keys() and config['simulator']:
            edited_config['coupling_map'] = 'all-to-all'

        return edited_config

    def _discover_remote_backends(self):
        """
        Return the remote backends available.

        Returns:
            dict[str:IBMQBackend]: a dict of the remote backend instances,
                keyed by backend name.
        """
        ret = {}
        configs_list = self._api.available_backends()
        for raw_config in configs_list:
            config = self._parse_backend_configuration(raw_config)
            ret[config['name']] = IBMQBackend(configuration=config, api=self._api)

        return ret

    def _lowest_pending_jobs(self):
        """Returns the backend with lowest pending jobs."""
        remote_backends = discover_remote_backends(api)
        remote_backends.remove('ibmqx_hpc_qasm_simulator')
        remote_backends.remove('ibmqx_qasm_simulator')
        device_status = [api.backend_status(backend) for backend in remote_backends]

        best = min([x for x in device_status if x['available'] is True],
                   key=lambda x: x['pending_jobs'])
        return best['backend']
