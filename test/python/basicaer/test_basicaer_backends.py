# -*- coding: utf-8 -*-

# Copyright 2018, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""BasicAer Backends Test."""

from qiskit import BasicAer
from qiskit.providers.basicaer import BasicAerProvider
from qiskit.providers.exceptions import QiskitBackendNotFoundError
from qiskit.test import providers


class TestBasicAerBackends(providers.ProviderTestCase):
    """Qiskit BasicAer Backends (Object) Tests."""

    provider_cls = BasicAerProvider
    backend_name = 'qasm_simulator'

    def test_deprecated(self):
        """Test that deprecated names map the same backends as the new names.
        """
        def _get_first_available_backend(provider, backend_names):
            """Gets the first available backend."""
            if isinstance(backend_names, str):
                backend_names = [backend_names]
            for backend_name in backend_names:
                try:
                    return provider.get_backend(backend_name).name()
                except QiskitBackendNotFoundError:
                    pass
            return None

        deprecated_names = BasicAer._deprecated_backend_names()
        for oldname, newname in deprecated_names.items():
            with self.subTest(oldname=oldname, newname=newname):
                try:
                    resolved_newname = _get_first_available_backend(BasicAer, newname)
                    real_backend = BasicAer.get_backend(resolved_newname)
                except QiskitBackendNotFoundError:
                    # The real name of the backend might not exist
                    pass
                else:
                    self.assertEqual(BasicAer.backends(oldname)[0], real_backend)

    def test_aliases_fail(self):
        """Test a failing backend lookup."""
        self.assertRaises(QiskitBackendNotFoundError, BasicAer.get_backend, 'bad_name')

    def test_aliases_return_empty_list(self):
        """Test backends() return an empty list if name is unknown."""
        self.assertEqual(BasicAer.backends("bad_name"), [])
