# -*- coding: utf-8 -*-

# Copyright (c) 2017, IBM. All Rights Reserved.
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

"""
Node for an OPENQASM file identifier/version statement.
"""
import re

from ._node import Node


class Format(Node):
    """Node for an OPENQASM file identifier/version statement.
    """

    def __init__(self, value):
        """Create the version node."""
        Node.__init__(self, "format", None, None)
        parts = re.match(r'(\w+)\s+(\d+)\.(\d+)', value)
        self.language = parts.group(1)
        self.majorversion = parts.group(2)
        self.minorversion = parts.group(3)

    def version(self):
        """Return the version."""
        return "%s.%s" % (self.majorversion, self.minorversion)

    def qasm(self, prec=15):
        """Return the corresponding format string."""
        # pylint: disable=unused-argument
        return "%s %s;" % (self.language, self.version())
