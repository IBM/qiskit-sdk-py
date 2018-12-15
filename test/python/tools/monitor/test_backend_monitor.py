# -*- coding: utf-8 -*-

# Copyright 2018, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

# pylint: disable=redefined-builtin

"""Tests for the wrapper functionality."""

import unittest
from qiskit.backends.ibmq import IBMQ
from qiskit.tools.monitor import backend_overview
from ...common import QiskitTestCase, requires_qe_access


class TestBackendOverview(QiskitTestCase):
    """Tools test case."""
    @requires_qe_access
    def test_backend_overview(self, qe_token, qe_url):
        """Test backend_overview"""
        IBMQ.enable_account(qe_token, qe_url)
        backend_overview()


if __name__ == '__main__':
    unittest.main(verbosity=2)
