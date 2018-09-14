# -*- coding: utf-8 -*-

# Copyright 2018, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""Meta-provider that aggregates several providers."""

import logging
from itertools import combinations
import warnings
from qiskit import QISKitError
from qiskit.backends.baseprovider import BaseProvider
from qiskit.backends.local.localprovider import LocalProvider

logger = logging.getLogger(__name__)


def _qiskit_supported_providers():
    """Get the providers supported by the Qiskit team.

    Returns:
        list[class]: list of provider classes.
    """
    supported_providers = [LocalProvider]

    # Add Qiskit-supported backends.
    # TODO: once the backends are available as packages, they will not need to
    # be imported conditionally.
    try:
        from qiskit.backends.sympy import SympyProvider
        supported_providers.append(SympyProvider)
    except ImportError:
        pass
    try:
        from qiskit.backends.projectq import ProjectQProvider
        supported_providers.append(ProjectQProvider)
    except ImportError:
        pass
    try:
        from qiskit.backends.jku import JKUProvider
        supported_providers.append(JKUProvider)
    except ImportError:
        pass

    return supported_providers

class DefaultQISKitProvider(BaseProvider):
    """
    Meta-provider that aggregates several providers.
    """
    def __init__(self):
        super().__init__()

        # List of providers.
        self.providers = [provider_class() for provider_class
                          in _qiskit_supported_providers()]

    def get_backend(self, name):
        provider_name = None
        # We have an overridding backend name
        if '@' in name:
           provider_name = name.split('@')[1]
        name = self.resolve_backend_name(name)
        if provider_name is not None:
            for provider in self.providers:
                if provider.name == provider_name:
                    return provider.get_backend(name)
        else:
            for provider in self.providers:
                try:
                    return provider.get_backend(name)
                except KeyError:
                    pass
            raise KeyError(name)

    def available_backends(self, filters=None):
        """Get a list of available backends from all providers (after filtering).

        Note:
            If two or more providers share similar backend names, only the backends
            belonging to the first registered provider will be returned.

        Args:
            filters (dict or callable): filtering conditions.
                each will either pass through, or be filtered out:

                1) dict: {'criteria': value}
                    the criteria can be over backend's `configuration` or `status`
                    e.g. {'local': False, 'simulator': False, 'operational': True}

                2) callable: BaseBackend -> bool
                    e.g. lambda x: x.configuration()['n_qubits'] > 5

        Returns:
            list[BaseBackend]: a list of backend instances available
                from all the providers.

        Raises:
            QISKitError: if passing filters that is neither dict nor callable
        """
        # pylint: disable=arguments-differ

        # Find duplicate backend names
        backends_by_name = {}
        for provider in self.providers:
            pro_backends = provider.available_backends()
            for back in pro_backends:
                back._overridding_name = None
                if back.name() in backends_by_name.keys():
                    backends_by_name[back.name()] = True
                else:
                    backends_by_name[back.name()] = False

        backends = []
        for provider in self.providers:
            pro_backends = provider.available_backends()
            for back in pro_backends:
                if backends_by_name[back.name()]:
                    back._overridding_name = back.name()+'@'+provider.name
                backends.append(back)

        if filters is not None:
            if isinstance(filters, dict):
                # exact match filter:
                # e.g. {'n_qubits': 5, 'operational': True}
                for key, value in filters.items():
                    backends = [instance for instance in backends
                                if instance.configuration().get(key) == value
                                or instance.status().get(key) == value]
            elif callable(filters):
                # acceptor filter: accept or reject a specific backend
                # e.g. lambda x: x.configuration()['n_qubits'] > 5
                accepted_backends = []
                for backend in backends:
                    try:
                        if filters(backend) is True:
                            accepted_backends.append(backend)
                    except Exception:  # pylint: disable=broad-except
                        pass
                backends = accepted_backends
            else:
                raise QISKitError('backend filters must be either dict or callable.')

        return backends

    def grouped_backend_names(self):
        """
        Aggregate group names from all providers.

        Returns:
            dict[str: list[str]]: aggregated group dictionary

        Raises:
            ValueError: if a backend is mapped to multiple groups
        """
        groups = {}
        for provider in self.providers:
            groups.update(provider.grouped_backend_names())
        for pair in combinations(groups.values(), r=2):
            if not set.isdisjoint(set(pair[0]), set(pair[1])):
                raise ValueError('duplicate backend group definition')

        return groups

    def deprecated_backend_names(self):
        """
        Aggregate deprecated names from all providers.

        Returns:
            dict[str: str]: aggregated dictionary of deprecated names
        """
        deprecates = {}
        for provider in self.providers:
            deprecates.update(provider.deprecated_backend_names())

        return deprecates

    def aliased_backend_names(self):
        """
        Aggregate aliased names from all providers.

        Returns:
            dict[str: str]: aggregated alias dictionary
        """
        aliases = {}
        for provider in self.providers:
            aliases.update(provider.aliased_backend_names())

        return aliases

    def add_provider(self, provider):
        """
        Add a new provider to the list of known providers.

        Args:
            provider (BaseProvider): Provider instance.

        Returns:
            BaseProvider: the provider instance.
        """
        # checks for equality of provider instances, based on the __eq__ method
        if provider not in self.providers:
            self.providers.append(provider)
            return provider
        else:
            warnings.warn("Skipping registration: The provider is already registered.")
            return self.providers[self.providers.index(provider)]

    def remove_provider(self, provider):
        """
        Remove a provider from the list of known providers.

        Args:
            provider (BaseProvider): provider to be removed.

        Raises:
            QISKitError: if the provider is not registered.
        """
        if isinstance(provider, LocalProvider):
            raise QISKitError("Cannot unregister 'local' provider.")
        try:
            self.providers.remove(provider)
        except ValueError:
            raise QISKitError("'%s' provider is not registered.")

    def resolve_backend_name(self, name):
        """Resolve backend name from a possible short group name, a deprecated name,
        or an alias.

        A group will be resolved in order of member priorities, depending on availability.

        Args:
            name (str): name of backend to resolve

        Returns:
            str: name of resolved backend, which is available from one of the providers

        Raises:
            LookupError: if name cannot be resolved through
            regular available names, nor groups, nor deprecated, nor alias names
        """
        resolved_name = ""
        available = []
        for back in self.available_backends(filters=None):
            bname = back.name()
            if '@' in bname:
                bname = back.name().split('@')[0]
            if bname not in available:
                available.append(bname)
        
        grouped = self.grouped_backend_names()
        deprecated = self.deprecated_backend_names()
        aliased = self.aliased_backend_names()
        
        provider_name = None
        if '@' in name:
            name, provider_name = name.split('@')

        if name in available:
            resolved_name = name
        elif name in grouped:
            available_members = [b for b in grouped[name] if b in available]
            if available_members:
                resolved_name = available_members[0]
        elif name in deprecated:
            resolved_name = deprecated[name]
            logger.warning('WARNING: %s is deprecated. Use %s.', name, resolved_name)
        elif name in aliased:
            resolved_name = aliased[name]

        if resolved_name not in available:
            raise LookupError('backend "{}" not found.'.format(name))

        return resolved_name
