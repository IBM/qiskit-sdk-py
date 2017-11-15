# -*- coding: utf-8 -*-
# pylint: disable=invalid-name,missing-docstring

# Copyright 2017 IBM RESEARCH. All Rights Reserved.
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

import unittest

from qiskit import QuantumProgram
from .common import QiskitTestCase

class MapperTest(QiskitTestCase):
    """Test the mapper."""

    def setUp(self):
        self.qp = QuantumProgram()

    def tearDown(self):
        pass

    def test_issue_81(self):
        # https://github.com/QISKit/qiskit-sdk-py/issues/81
        self.qp.load_qasm_file(self._get_resource_path('qasm/issue_81.qasm'), name='test')
        coupling_map = {0: [2], 1: [2], 2: [3], 3: []}
        result1 = self.qp.execute(["test"], backend="local_qasm_simulator", coupling_map=coupling_map)
        count1 = result1.get_counts("test")
        result2 = self.qp.execute(["test"], backend="local_qasm_simulator", coupling_map=None)
        count2 = result2.get_counts("test")
        self.assertEqual(count1.keys(), count2.keys(),)

    def test_issue_111(self):
        # https://github.com/QISKit/qiskit-sdk-py/issues/111
        self.qp.load_qasm_file(self._get_resource_path('qasm/issue_111.qasm'), name='test')
        coupling_map = {0: [2], 1: [2], 2: [3], 3: []}
        result1 = self.qp.execute(["test"], backend="local_qasm_simulator", coupling_map=coupling_map)
        result1.get_counts("test")

if __name__ == '__main__':
    unittest.main()
