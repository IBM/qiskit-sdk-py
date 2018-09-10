# -*- coding: utf-8 -*-

# Copyright 2017, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

# pylint: disable=wrong-import-order
# pylint: disable=redefined-builtin

"""Main QISKit public functionality."""

import os
import sys
import pkgutil

# First, check for required Python and API version
from . import _util

from ._qiskiterror import QISKitError
from ._classicalregister import ClassicalRegister
from ._quantumregister import QuantumRegister
from ._quantumcircuit import QuantumCircuit
from ._gate import Gate
from ._compositegate import CompositeGate
from ._instruction import Instruction
from ._instructionset import InstructionSet
from ._reset import Reset
from ._measure import Measure
from .result import Result

# The qiskit.extensions.x imports needs to be placed here due to the
# mechanism for adding gates dynamically.
import qiskit.extensions.standard
import qiskit.extensions.quantum_initializer

# Import circuit drawing methods by default
# This is wrapped in a try because the Travis tests fail due to non-framework
# Python build since using pyenv
try:
    from qiskit.tools.visualization import (circuit_drawer, plot_histogram)
except (ImportError, RuntimeError) as expt:
    print("Error: {0}".format(expt))

# Import the TextProgressBar for easy use.
from qiskit._progressbar import TextProgressBar

# Allow extending this namespace. Please note that currently this line needs
# to be placed *before* the wrapper imports.
__path__ = pkgutil.extend_path(__path__, __name__)

from .wrapper._wrapper import (
    available_backends, local_backends, remote_backends,
    get_backend, compile, execute, register, unregister,
    registered_providers, load_qasm_string, load_qasm_file, least_busy,
    store_credentials)

# Import the wrapper, to make it available when doing "import qiskit".
from . import wrapper

# Import Jupyter tools if running in a Jupyter notebook env.
if ('ipykernel' in sys.modules) and ('spyder' not in sys.modules):
    try:
        # The import * is here to register the Jupyter magics
        from qiskit.wrapper.jupyter import *  # pylint: disable=wildcard-import
    except ImportError:
        print("Error importing Jupyter notebook extensions.")

# Set parallel ennvironmental variable
os.environ['QISKIT_IN_PARALLEL'] = 'FALSE'

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(ROOT_DIR, "VERSION.txt"), "r") as version_file:
    __version__ = version_file.read().strip()
