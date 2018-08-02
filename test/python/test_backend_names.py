# -*- coding: utf-8 -*-

# Copyright 2018, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

# pylint: disable=invalid-name,missing-docstring,broad-except

"""Backend grouped/deprecated/aliased test."""

from qiskit import get_backend, available_backends
from qiskit.backends.local import QasmSimulatorPy, QasmSimulatorCpp
from .common import QiskitTestCase


# Cpp backend required
try:
    cpp_backend = QasmSimulatorCpp()
except FileNotFoundError:
    _skip_cpp = True
else:
    _skip_cpp = False


class TestBackendNames(QiskitTestCase):
    """
    Test grouped/deprecated/aliased names from providers.
    """

    def test_local_groups(self):
        """Local group names are resolved correctly"""
        group_name = "local_qasm_simulator"
        backend = get_backend(group_name)
        if not _skip_cpp:
            self.assertIsInstance(backend, QasmSimulatorCpp)
        else:
            self.assertIsInstance(backend, QasmSimulatorPy)

    def test_local_deprecated(self):
        """Deprecated local backends are resolved correctly"""
        old_name = "local_qiskit_simulator"
        if not _skip_cpp:
            new_backend = get_backend(old_name)
            self.assertIsInstance(new_backend, QasmSimulatorCpp)

    def test_compact_flag(self):
        """Compact flag for available_backends works"""
        compact_names = available_backends()
        expanded_names = available_backends(compact=False)
        self.assertIn('local_qasm_simulator', compact_names)
        self.assertIn('local_statevector_simulator', compact_names)
        self.assertIn('local_unitary_simulator', compact_names)
        self.assertIn('local_qasm_simulator_py', expanded_names)
        self.assertIn('local_statevector_simulator_py', expanded_names)
