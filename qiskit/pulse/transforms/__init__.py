# This code is part of Qiskit.
#
# (C) Copyright IBM 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
"""
===================================================
Pulse Transforms (:mod:`qiskit.pulse.transforms`)
===================================================

The pulse transforms provide a collection of conversion to reallocate and optimize
instructions to execute the input program on backends supporting the Open Pulse.

Alignments
==========

The alignment transforms define alignment policies of instructions in ``ScheduleBlock``.
This transformation is called to create ``Schedule`` from ``ScheduleBlock``.

.. autosummary::
   :toctree: ../stubs/

   AlignEquispaced
   AlignFunc
   AlignLeft
   AlignRight
   AlignSequential
   pad


Basis
=====

The basis transforms perform a fundamental conversion of schedules to
optimize it to execute on Open Pulse backends.

.. autosummary::
   :toctree: ../stubs/

   compress_pulses
   flatten
   inline_subroutines
   remove_directives
   remove_trivial_barriers


DAG
===

The DAG transforms create DAG representation of input program. This can be used for
optimization of instructions and equality check.

.. autosummary::
   :toctree: ../stubs/

   block_to_dag


Measures
========

The measure transforms schedule and align measurement and acquisition instructions.

.. autosummary::
   :toctree: ../stubs/

   add_implicit_acquires
   align_measures
"""

from qiskit.pulse.transforms.alignments import (
    AlignEquispaced,
    AlignFunc,
    AlignLeft,
    AlignRight,
    AlignSequential,
    align_equispaced,
    align_func,
    align_left,
    align_right,
    align_sequential,
    pad
)

from qiskit.pulse.transforms.basis import (
    block_to_schedule,
    compress_pulses,
    flatten,
    inline_subroutines,
    remove_directives,
    remove_trivial_barriers
)

from qiskit.pulse.transforms.dag import (
    block_to_dag
)

from qiskit.pulse.transforms.measures import (
    add_implicit_acquires,
    align_measures
)
