# -*- coding: utf-8 -*-

# Copyright 2018, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

# pylint: disable=invalid-name

"""Tests for the wrapper functionality."""

import logging
import unittest

import qiskit.wrapper
from qiskit import QISKitError
from qiskit.backends.ibmq import IBMQProvider
from qiskit.wrapper import registered_providers
from ._mockutils import DummyProvider
from .common import QiskitTestCase, requires_qe_access
from .test_backends import remove_backends_from_list


class TestWrapper(QiskitTestCase):
    """Wrapper test case."""
    @requires_qe_access
    def test_wrapper_register_ok(self, QE_TOKEN, QE_URL, hub, group, project):
        """wrapper.register()."""
        qiskit.wrapper.register(QE_TOKEN, QE_URL, hub, group, project)
        backends = qiskit.wrapper.available_backends()
        backends = remove_backends_from_list(backends)
        self.log.info(backends)
        self.assertTrue(len(backends) > 0)

    @requires_qe_access
    def test_backends_with_filter(self, QE_TOKEN, QE_URL, hub, group, project):
        """wrapper.available_backends(filter=...)."""
        qiskit.wrapper.register(QE_TOKEN, QE_URL, hub, group, project)
        backends = qiskit.wrapper.available_backends({'local': False,
                                                      'simulator': True})
        self.log.info(backends)
        self.assertTrue(len(backends) > 0)

    def test_local_backends(self):
        """wrapper.available_backends({'local': True})"""
        local_backends = qiskit.wrapper.available_backends({'local': True})
        self.log.info(local_backends)
        self.assertTrue(len(local_backends) > 0)

    @requires_qe_access
    def test_register_twice(self, QE_TOKEN, QE_URL, hub, group, project):
        """Double registration of the same credentials."""
        qiskit.wrapper.register(QE_TOKEN, QE_URL, hub, group, project)
        initial_providers = registered_providers()
        # Registering twice should give warning and add no providers.
        qiskit.wrapper.register(QE_TOKEN, QE_URL, hub, group, project)
        self.assertCountEqual(initial_providers, registered_providers())

    def test_register_bad_credentials(self):
        """Registering a provider with bad credentials."""
        initial_providers = registered_providers()
        with self.assertRaises(QISKitError):
            qiskit.wrapper.register('FAKE_TOKEN', 'http://unknown')
        self.assertEqual(initial_providers, registered_providers())

    @requires_qe_access
    def test_unregister(self, QE_TOKEN, QE_URL, hub, group, project):
        """Unregistering."""
        initial_providers = registered_providers()
        ibmqprovider = qiskit.wrapper.register(QE_TOKEN, QE_URL, hub, group, project)
        self.assertCountEqual(initial_providers + [ibmqprovider],
                              registered_providers())
        qiskit.wrapper.unregister(ibmqprovider)
        self.assertEqual(initial_providers, registered_providers())

    @requires_qe_access
    def test_unregister_non_existent(self, QE_TOKEN, QE_URL, hub, group, project):
        """Unregistering a non existent provider."""
        initial_providers = registered_providers()
        ibmqprovider = IBMQProvider(QE_TOKEN, QE_URL, hub, group, project)
        with self.assertRaises(QISKitError):
            qiskit.wrapper.unregister(ibmqprovider)
        self.assertEqual(initial_providers, registered_providers())

    def test_register_backend_name_conflicts(self):
        """Backend name conflicts when registering."""
        class SecondDummyProvider(DummyProvider):
            """
            Subclass the DummyProvider so register treats them as different."""
            pass

        dummy_provider = qiskit.wrapper.register(provider_class=DummyProvider)
        initial_providers = registered_providers()
        initial_backends = qiskit.wrapper.available_backends()
        dummy_backend = dummy_provider.get_backend('local_dummy_simulator')
        with self.assertLogs(level=logging.WARNING) as logs:
            second_dummy_provider = qiskit.wrapper.register(
                provider_class=SecondDummyProvider)

        # Check that one, and only one warning has been issued.
        self.assertEqual(len(logs.records), 1)
        # Check that the provider has been registered.
        self.assertCountEqual(initial_providers + [second_dummy_provider],
                              registered_providers())
        # Check that no new backends have been added.
        self.assertCountEqual(initial_backends,
                              qiskit.wrapper.available_backends())

        # Check the name of the backend still refers to the previous one.
        self.assertEqual(dummy_backend,
                         qiskit.wrapper.get_backend('local_dummy_simulator'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
