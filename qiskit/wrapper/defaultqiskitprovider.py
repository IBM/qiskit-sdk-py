# -*- coding: utf-8 -*-

# Copyright 2018, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

# pylint: disable=broad-except

"""Meta-provider that aggregates several providers."""
import logging

from itertools import combinations
from qiskit.backends.baseprovider import BaseProvider
from qiskit.backends.local.localprovider import LocalProvider
from qiskit import QISKitError

logger = logging.getLogger(__name__)


class DefaultQISKitProvider(BaseProvider):
    """
    Meta-provider that aggregates several providers.
    """
    def __init__(self):
        super().__init__()

        # List of providers.
        self.providers = [LocalProvider()]

    def get_backend(self, name):
        name = self.resolve_backend_name(name)
        for provider in self.providers:
            try:
                return provider.get_backend(name)
            except KeyError:
                pass
        raise KeyError(name)

    def available_backends(self, filters=None):
        """Get a list of available backends from all providers (after filtering).

        Args:
            filters (dict or callable): filtering conditions.
                each will either pass through, or be filtered out.
                1) dict: {'criteria': value}
                    the criteria can be over backend's `configuration` or `status`
                    e.g. {'local': False, 'simulator': False, 'available': True}
                2) callable: BaseBackend -> bool
                    e.g. lambda x: x.configuration['n_qubits'] > 5

        Returns:
            list[BaseBackend]: a list of backend instances available
                from all the providers.

        Raises:
            QISKitError: if passing filters that is neither dict nor callable
        """
        # pylint: disable=arguments-differ
        backends = []
        for provider in self.providers:
            backends.extend(provider.available_backends())

        if filters is not None:
            if isinstance(filters, dict):
                # exact match filter:
                # e.g. {'n_qubits': 5, 'available': True}
                for key, value in filters.items():
                    backends = [instance for instance in backends
                                if instance.configuration.get(key) == value
                                or instance.status.get(key) == value]
            elif callable(filters):
                # acceptor filter: accept or reject a specific backend
                # e.g. lambda x: x.configuration['n_qubits'] > 5
                accepted_backends = []
                for backend in backends:
                    try:
                        if filters(backend) is True:
                            accepted_backends.append(backend)
                    except Exception:
                        pass
                backends = accepted_backends
            else:
                raise QISKitError('backend filters must be either dict or callable.')

        return backends

    def aliased_backend_names(self):
        """
        Aggregate alias information from all providers.

        Returns:
            dict[str: list[str]]: aggregated alias dictionary

        Raises:
            ValueError: if a backend is mapped to multiple aliases
        """
        aliases = {}
        for provider in self.providers:
            aliases = {**aliases, **provider.aliased_backend_names()}
        for pair in combinations(aliases.values(), r=2):
            if not set.isdisjoint(set(pair[0]), set(pair[1])):
                raise ValueError('duplicate backend alias definition')

        return aliases

    def deprecated_backend_names(self):
        """
        Aggregate deprecated names from all providers.

        Returns:
            dict[str: list[str]]: aggregated alias dictionary
        """
        deprecates = {}
        for provider in self.providers:
            deprecates = {**deprecates, **provider.deprecated_backend_names()}

        return deprecates

    def add_provider(self, provider):
        """
        Add a new provider to the list of known providers.

        Args:
            provider (BaseProvider): Provider instance.
        """
        self.providers.append(provider)

    def resolve_backend_name(self, name):
        """Resolve backend name from a possible short alias or a deprecated name.

        The alias will be chosen in order of priority, depending on availability.

        Args:
            name (str): name of backend to resolve

        Returns:
            str: name of resolved backend, which is available from one of the providers

        Raises:
            LookupError: if name cannot be resolved through
            regular available names, nor aliases, nor deprecated names
        """
        resolved_name = ""
        available = [b.name for b in self.available_backends()]
        aliased = self.aliased_backend_names()
        deprecated = self.deprecated_backend_names()

        if name in available:
            resolved_name = name
        elif name in aliased:
            available_dealiases = [b for b in aliased[name] if b in available]
            if available_dealiases:
                resolved_name = available_dealiases[0]
        elif name in deprecated:
            resolved_name = deprecated[name]
            logger.warning('WARNING: %s is deprecated. Use %s.', name, resolved_name)

        if resolved_name not in available:
            raise LookupError('backend "{}" not found.'.format(name))

        return resolved_name
