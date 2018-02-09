# -*- coding: utf-8 -*-

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

"""
Exception for errors raised by unroller.
"""

from qiskit import QISKitError


class UnrollerError(QISKitError):
    """Base class for errors raised by unroller."""

    def __init__(self, *message):
        """Set the error message."""
        super(UnrollerError, self).__init__(*message)
        self.message = ' '.join(message)

    def __str__(self):
        """Return the message."""
        return repr(self.message)
