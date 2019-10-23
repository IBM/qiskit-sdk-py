# -*- coding: utf-8 -*-

# This code is part of Qiskit.
#
# (C) Copyright IBM 2017, 2018.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

# pylint: disable=invalid-name

"""Transpiler testing"""

import io
from logging import StreamHandler, getLogger
import unittest.mock
import sys

from qiskit import QuantumRegister, QuantumCircuit
from qiskit.transpiler import PassManager, TranspilerAccessError, TranspilerError
from qiskit.compiler import transpile
from qiskit.transpiler.runningpassmanager import DoWhileController, ConditionalController, \
    FlowController
from qiskit.test import QiskitTestCase
from ._dummy_passes import (PassA_TP_NR_NP, PassB_TP_RA_PA, PassC_TP_RA_PA,
                            PassD_TP_NR_NP, PassE_AP_NR_NP, PassF_reduce_dag_property,
                            PassH_Bad_TP, PassI_Bad_AP, PassJ_Bad_NoReturn,
                            PassK_check_fixed_point_property, PassM_AP_NR_NP,
                            PassN_AP_save_property)


class SchedulerTestCase(QiskitTestCase):
    """Asserts for the scheduler."""

    def setUp(self):
        self.passmanager = PassManager()
        self.circuit = QuantumCircuit(QuantumRegister(1))

    def assertScheduler(self, passmanager, expected):
        """
        Run `transpile(self.circuit, passmanager)` and check
        if the passes run as expected.

        Args:
            passmanager (PassManager): pass manager instance for the transpilation process
            expected (list): List of things the passes are logging
        """
        logger = 'LocalLogger'
        with self.assertLogs(logger, level='INFO') as cm:
            out = transpile(self.circuit, pass_manager=passmanager)
        self.assertIsInstance(out, QuantumCircuit)
        self.assertEqual([record.message for record in cm.records], expected)

    def assertSchedulerRaises(self, circuit, passmanager, expected, exception_type):
        """
        Run `transpile(circuit, passmanager)` and check
        if the passes run as expected until exception_type is raised.

        Args:
            circuit (QuantumCircuit): Circuit to transform via transpilation
            passmanager (PassManager): pass manager instance for the transpilation process
            expected (list): List of things the passes are logging
            exception_type (Exception): Exception that is expected to be raised.
        """
        logger = 'LocalLogger'
        with self.assertLogs(logger, level='INFO') as cm:
            self.assertRaises(exception_type, transpile, circuit, pass_manager=passmanager)
        self.assertEqual([record.message for record in cm.records], expected)


class TestPassManagerInit(SchedulerTestCase):
    """ The pass manager sets things at init time."""

    def test_passes(self):
        """ A single chain of passes, with Requests and Preserves, at __init__ time"""
        self.circuit = QuantumCircuit(QuantumRegister(1))
        passmanager = PassManager(passes=[
            PassC_TP_RA_PA(),  # Request: PassA / Preserves: PassA
            PassB_TP_RA_PA(),  # Request: PassA / Preserves: PassA
            PassD_TP_NR_NP(argument1=[1, 2]),  # Requires: {}/ Preserves: {}
            PassB_TP_RA_PA()])
        self.assertScheduler(passmanager, ['run transformation pass PassA_TP_NR_NP',
                                           'run transformation pass PassC_TP_RA_PA',
                                           'run transformation pass PassB_TP_RA_PA',
                                           'run transformation pass PassD_TP_NR_NP',
                                           'argument [1, 2]',
                                           'run transformation pass PassA_TP_NR_NP',
                                           'run transformation pass PassB_TP_RA_PA'])


class TestUseCases(SchedulerTestCase):
    """Combine passes in different ways and checks that passes are run
    in the right order."""

    def setUp(self):
        self.circuit = QuantumCircuit(QuantumRegister(1))
        self.passmanager = PassManager()

    def test_chain(self):
        """A single chain of passes, with Requires and Preserves."""
        self.passmanager.append(PassC_TP_RA_PA())  # Requires: PassA / Preserves: PassA
        self.passmanager.append(PassB_TP_RA_PA())  # Requires: PassA / Preserves: PassA
        self.passmanager.append(PassD_TP_NR_NP(argument1=[1, 2]))  # Requires: {}/ Preserves: {}
        self.passmanager.append(PassB_TP_RA_PA())
        self.assertScheduler(self.passmanager,
                             ['run transformation pass PassA_TP_NR_NP',
                              'run transformation pass PassC_TP_RA_PA',
                              'run transformation pass PassB_TP_RA_PA',
                              'run transformation pass PassD_TP_NR_NP',
                              'argument [1, 2]',
                              'run transformation pass PassA_TP_NR_NP',
                              'run transformation pass PassB_TP_RA_PA'])

    def test_conditional_passes_true(self):
        """A pass set with a conditional parameter. The callable is True."""
        self.passmanager.append(PassE_AP_NR_NP(True))
        self.passmanager.append(PassA_TP_NR_NP(),
                                condition=lambda property_set: property_set['property'])
        self.assertScheduler(self.passmanager,
                             ['run analysis pass PassE_AP_NR_NP',
                              'set property as True',
                              'run transformation pass PassA_TP_NR_NP'])

    def test_conditional_passes_false(self):
        """A pass set with a conditional parameter. The callable is False."""
        self.passmanager.append(PassE_AP_NR_NP(False))
        self.passmanager.append(PassA_TP_NR_NP(),
                                condition=lambda property_set: property_set['property'])
        self.assertScheduler(self.passmanager,
                             ['run analysis pass PassE_AP_NR_NP',
                              'set property as False'])

    def test_conditional_and_loop(self):
        """Run a conditional first, then a loop."""
        self.passmanager.append(PassE_AP_NR_NP(True))
        self.passmanager.append(
            [PassK_check_fixed_point_property(),
             PassA_TP_NR_NP(),
             PassF_reduce_dag_property()],
            do_while=lambda property_set: not property_set['property_fixed_point'],
            condition=lambda property_set: property_set['property'])
        self.assertScheduler(self.passmanager,
                             ['run analysis pass PassE_AP_NR_NP',
                              'set property as True',
                              'run analysis pass PassG_calculates_dag_property',
                              'set property as 8 (from dag.property)',
                              'run analysis pass PassK_check_fixed_point_property',
                              'run transformation pass PassA_TP_NR_NP',
                              'run transformation pass PassF_reduce_dag_property',
                              'dag property = 6',
                              'run analysis pass PassG_calculates_dag_property',
                              'set property as 6 (from dag.property)',
                              'run analysis pass PassK_check_fixed_point_property',
                              'run transformation pass PassA_TP_NR_NP',
                              'run transformation pass PassF_reduce_dag_property',
                              'dag property = 5',
                              'run analysis pass PassG_calculates_dag_property',
                              'set property as 5 (from dag.property)',
                              'run analysis pass PassK_check_fixed_point_property',
                              'run transformation pass PassA_TP_NR_NP',
                              'run transformation pass PassF_reduce_dag_property',
                              'dag property = 4',
                              'run analysis pass PassG_calculates_dag_property',
                              'set property as 4 (from dag.property)',
                              'run analysis pass PassK_check_fixed_point_property',
                              'run transformation pass PassA_TP_NR_NP',
                              'run transformation pass PassF_reduce_dag_property',
                              'dag property = 3',
                              'run analysis pass PassG_calculates_dag_property',
                              'set property as 3 (from dag.property)',
                              'run analysis pass PassK_check_fixed_point_property',
                              'run transformation pass PassA_TP_NR_NP',
                              'run transformation pass PassF_reduce_dag_property',
                              'dag property = 2',
                              'run analysis pass PassG_calculates_dag_property',
                              'set property as 2 (from dag.property)',
                              'run analysis pass PassK_check_fixed_point_property',
                              'run transformation pass PassA_TP_NR_NP',
                              'run transformation pass PassF_reduce_dag_property',
                              'dag property = 2',
                              'run analysis pass PassG_calculates_dag_property',
                              'set property as 2 (from dag.property)',
                              'run analysis pass PassK_check_fixed_point_property',
                              'run transformation pass PassA_TP_NR_NP',
                              'run transformation pass PassF_reduce_dag_property',
                              'dag property = 2'])

    def test_loop_and_conditional(self):
        """Run a loop first, then a conditional."""
        FlowController.remove_flow_controller('condition')
        FlowController.add_flow_controller('condition', ConditionalController)

        self.passmanager.append(PassK_check_fixed_point_property())
        self.passmanager.append(
            [PassK_check_fixed_point_property(),
             PassA_TP_NR_NP(),
             PassF_reduce_dag_property()],
            do_while=lambda property_set: not property_set['property_fixed_point'],
            condition=lambda property_set: not property_set['property_fixed_point'])
        self.assertScheduler(self.passmanager,
                             ['run analysis pass PassG_calculates_dag_property',
                              'set property as 8 (from dag.property)',
                              'run analysis pass PassK_check_fixed_point_property',
                              'run transformation pass PassA_TP_NR_NP',
                              'run transformation pass PassF_reduce_dag_property',
                              'dag property = 6',
                              'run analysis pass PassG_calculates_dag_property',
                              'set property as 6 (from dag.property)',
                              'run analysis pass PassK_check_fixed_point_property',
                              'run transformation pass PassA_TP_NR_NP',
                              'run transformation pass PassF_reduce_dag_property',
                              'dag property = 5',
                              'run analysis pass PassG_calculates_dag_property',
                              'set property as 5 (from dag.property)',
                              'run analysis pass PassK_check_fixed_point_property',
                              'run transformation pass PassA_TP_NR_NP',
                              'run transformation pass PassF_reduce_dag_property',
                              'dag property = 4',
                              'run analysis pass PassG_calculates_dag_property',
                              'set property as 4 (from dag.property)',
                              'run analysis pass PassK_check_fixed_point_property',
                              'run transformation pass PassA_TP_NR_NP',
                              'run transformation pass PassF_reduce_dag_property',
                              'dag property = 3',
                              'run analysis pass PassG_calculates_dag_property',
                              'set property as 3 (from dag.property)',
                              'run analysis pass PassK_check_fixed_point_property',
                              'run transformation pass PassA_TP_NR_NP',
                              'run transformation pass PassF_reduce_dag_property',
                              'dag property = 2',
                              'run analysis pass PassG_calculates_dag_property',
                              'set property as 2 (from dag.property)',
                              'run analysis pass PassK_check_fixed_point_property',
                              'run transformation pass PassA_TP_NR_NP',
                              'run transformation pass PassF_reduce_dag_property',
                              'dag property = 2',
                              'run analysis pass PassG_calculates_dag_property',
                              'set property as 2 (from dag.property)',
                              'run analysis pass PassK_check_fixed_point_property',
                              'run transformation pass PassA_TP_NR_NP',
                              'run transformation pass PassF_reduce_dag_property',
                              'dag property = 2'])

    def test_do_not_repeat_based_on_preservation(self):
        """When a pass is still a valid pass (because the following passes
        preserved it), it should not run again."""
        self.passmanager.append([PassB_TP_RA_PA(),
                                 PassA_TP_NR_NP(),
                                 PassB_TP_RA_PA()])
        self.assertScheduler(self.passmanager,
                             ['run transformation pass PassA_TP_NR_NP',
                              'run transformation pass PassB_TP_RA_PA'])

    def test_do_not_repeat_based_on_idempotence(self):
        """Repetition can be optimized to a single execution when
        the pass is idempotent."""
        self.passmanager.append(PassA_TP_NR_NP())
        self.passmanager.append([PassA_TP_NR_NP(), PassA_TP_NR_NP()])
        self.passmanager.append(PassA_TP_NR_NP())
        self.assertScheduler(self.passmanager,
                             ['run transformation pass PassA_TP_NR_NP'])

    def test_non_idempotent_pass(self):
        """Two or more runs of a non-idempotent pass cannot be optimized."""
        self.passmanager.append(PassF_reduce_dag_property())
        self.passmanager.append([PassF_reduce_dag_property(),
                                 PassF_reduce_dag_property()])
        self.passmanager.append(PassF_reduce_dag_property())
        self.assertScheduler(self.passmanager,
                             ['run transformation pass PassF_reduce_dag_property',
                              'dag property = 6',
                              'run transformation pass PassF_reduce_dag_property',
                              'dag property = 5',
                              'run transformation pass PassF_reduce_dag_property',
                              'dag property = 4',
                              'run transformation pass PassF_reduce_dag_property',
                              'dag property = 3'])

    def test_fenced_property_set(self):
        """Transformation passes are not allowed to modify the property set."""
        self.passmanager.append(PassH_Bad_TP())
        self.assertSchedulerRaises(self.circuit, self.passmanager,
                                   ['run transformation pass PassH_Bad_TP'],
                                   TranspilerAccessError)

    def test_fenced_dag(self):
        """Analysis passes are not allowed to modified the DAG."""
        qr = QuantumRegister(2)
        circ = QuantumCircuit(qr)
        circ.cx(qr[0], qr[1])
        circ.cx(qr[0], qr[1])
        circ.cx(qr[1], qr[0])
        circ.cx(qr[1], qr[0])

        self.passmanager.append(PassI_Bad_AP())
        self.assertSchedulerRaises(circ, self.passmanager,
                                   ['run analysis pass PassI_Bad_AP',
                                    'cx_runs: {(5, 6, 7, 8)}'],
                                   TranspilerAccessError)

    def test_analysis_pass_is_idempotent(self):
        """Analysis passes are idempotent."""
        passmanager = PassManager()
        passmanager.append(PassE_AP_NR_NP(argument1=1))
        passmanager.append(PassE_AP_NR_NP(argument1=1))
        self.assertScheduler(passmanager,
                             ['run analysis pass PassE_AP_NR_NP',
                              'set property as 1'])

    def test_ap_before_and_after_a_tp(self):
        """A default transformation does not preserves anything
        and analysis passes need to be re-run"""
        passmanager = PassManager()
        passmanager.append(PassE_AP_NR_NP(argument1=1))
        passmanager.append(PassA_TP_NR_NP())
        passmanager.append(PassE_AP_NR_NP(argument1=1))
        self.assertScheduler(passmanager,
                             ['run analysis pass PassE_AP_NR_NP',
                              'set property as 1',
                              'run transformation pass PassA_TP_NR_NP',
                              'run analysis pass PassE_AP_NR_NP',
                              'set property as 1'])

    def test_pass_no_return(self):
        """Transformation passes that don't return a DAG raise error."""
        self.passmanager.append(PassJ_Bad_NoReturn())
        self.assertSchedulerRaises(self.circuit, self.passmanager,
                                   ['run transformation pass PassJ_Bad_NoReturn'],
                                   TranspilerError)

    def test_fixed_point_pass(self):
        """A pass set with a do_while parameter that checks for a fixed point."""
        self.passmanager.append(
            [PassK_check_fixed_point_property(),
             PassA_TP_NR_NP(),
             PassF_reduce_dag_property()],
            do_while=lambda property_set: not property_set['property_fixed_point'])
        self.assertScheduler(self.passmanager,
                             ['run analysis pass PassG_calculates_dag_property',
                              'set property as 8 (from dag.property)',
                              'run analysis pass PassK_check_fixed_point_property',
                              'run transformation pass PassA_TP_NR_NP',
                              'run transformation pass PassF_reduce_dag_property',
                              'dag property = 6',
                              'run analysis pass PassG_calculates_dag_property',
                              'set property as 6 (from dag.property)',
                              'run analysis pass PassK_check_fixed_point_property',
                              'run transformation pass PassA_TP_NR_NP',
                              'run transformation pass PassF_reduce_dag_property',
                              'dag property = 5',
                              'run analysis pass PassG_calculates_dag_property',
                              'set property as 5 (from dag.property)',
                              'run analysis pass PassK_check_fixed_point_property',
                              'run transformation pass PassA_TP_NR_NP',
                              'run transformation pass PassF_reduce_dag_property',
                              'dag property = 4',
                              'run analysis pass PassG_calculates_dag_property',
                              'set property as 4 (from dag.property)',
                              'run analysis pass PassK_check_fixed_point_property',
                              'run transformation pass PassA_TP_NR_NP',
                              'run transformation pass PassF_reduce_dag_property',
                              'dag property = 3',
                              'run analysis pass PassG_calculates_dag_property',
                              'set property as 3 (from dag.property)',
                              'run analysis pass PassK_check_fixed_point_property',
                              'run transformation pass PassA_TP_NR_NP',
                              'run transformation pass PassF_reduce_dag_property',
                              'dag property = 2',
                              'run analysis pass PassG_calculates_dag_property',
                              'set property as 2 (from dag.property)',
                              'run analysis pass PassK_check_fixed_point_property',
                              'run transformation pass PassA_TP_NR_NP',
                              'run transformation pass PassF_reduce_dag_property',
                              'dag property = 2',
                              'run analysis pass PassG_calculates_dag_property',
                              'set property as 2 (from dag.property)',
                              'run analysis pass PassK_check_fixed_point_property',
                              'run transformation pass PassA_TP_NR_NP',
                              'run transformation pass PassF_reduce_dag_property',
                              'dag property = 2'])

    def test_fixed_point_pass_max_iteration(self):
        """A pass set with a do_while parameter that checks that
        the max_iteration is raised."""
        self.passmanager.append(
            [PassK_check_fixed_point_property(),
             PassA_TP_NR_NP(),
             PassF_reduce_dag_property()],
            do_while=lambda property_set: not property_set['property_fixed_point'],
            max_iteration=2)
        self.assertSchedulerRaises(self.circuit, self.passmanager,
                                   ['run analysis pass PassG_calculates_dag_property',
                                    'set property as 8 (from dag.property)',
                                    'run analysis pass PassK_check_fixed_point_property',
                                    'run transformation pass PassA_TP_NR_NP',
                                    'run transformation pass PassF_reduce_dag_property',
                                    'dag property = 6',
                                    'run analysis pass PassG_calculates_dag_property',
                                    'set property as 6 (from dag.property)',
                                    'run analysis pass PassK_check_fixed_point_property',
                                    'run transformation pass PassA_TP_NR_NP',
                                    'run transformation pass PassF_reduce_dag_property',
                                    'dag property = 5'], TranspilerError)

    def test_fresh_initial_state(self):
        """New construction gives fresh instance."""
        self.passmanager.append(PassM_AP_NR_NP(argument1=1))
        self.passmanager.append(PassA_TP_NR_NP())
        self.passmanager.append(PassM_AP_NR_NP(argument1=1))
        self.assertScheduler(self.passmanager,
                             ['run analysis pass PassM_AP_NR_NP',
                              'self.argument1 = 2',
                              'run transformation pass PassA_TP_NR_NP',
                              'run analysis pass PassM_AP_NR_NP',
                              'self.argument1 = 2'])

    def test_rollback_if_true(self):
        """ Dump passes with a rollback_if 2 < 3"""
        self.passmanager.append(PassE_AP_NR_NP(3))
        self.passmanager.append([PassN_AP_save_property('property'), PassE_AP_NR_NP(2)],
                                rollback_if=lambda property_set:
                                property_set['property'] < property_set['property_previous'])
        self.assertScheduler(self.passmanager, ['run analysis pass PassE_AP_NR_NP',
                                                'set property as 3',
                                                'run analysis pass PassN_AP_save_property',
                                                'property copied to property_previous',
                                                'run analysis pass PassE_AP_NR_NP',
                                                'set property as 2'])
        self.assertEqual(self.passmanager.property_set['property'], 3)

    def test_rollback_if_false(self):
        """ Dump passes with a rollback_if 2==3"""
        self.passmanager.append(PassE_AP_NR_NP(3))
        self.passmanager.append([PassN_AP_save_property('property'), PassE_AP_NR_NP(2)],
                                rollback_if=lambda property_set:
                                property_set['property'] == property_set['property_previous'])
        self.assertScheduler(self.passmanager, ['run analysis pass PassE_AP_NR_NP',
                                                'set property as 3',
                                                'run analysis pass PassN_AP_save_property',
                                                'property copied to property_previous',
                                                'run analysis pass PassE_AP_NR_NP',
                                                'set property as 2'])
        self.assertEqual(self.passmanager.property_set['property'], 2)


class DoXTimesController(FlowController):
    """A control-flow plugin for running a set of passes an X amount of times."""

    def __init__(self, passes, options, do_x_times=0, **_):
        self.do_x_times = do_x_times
        super().__init__(passes, options)

    def __iter__(self):
        for _ in range(self.do_x_times(self.do_x_times.fenced_property_set)):
            for pass_ in self.passes:
                yield pass_


class TestControlFlowPlugin(SchedulerTestCase):
    """Testing the control flow plugin system."""

    def test_control_flow_plugin(self):
        """Adds a control flow plugin with a single parameter and runs it."""
        FlowController.add_flow_controller('do_x_times', DoXTimesController)
        self.passmanager.append([PassB_TP_RA_PA(), PassC_TP_RA_PA()],
                                do_x_times=lambda x: 3)
        self.assertScheduler(self.passmanager,
                             ['run transformation pass PassA_TP_NR_NP',
                              'run transformation pass PassB_TP_RA_PA',
                              'run transformation pass PassC_TP_RA_PA',
                              'run transformation pass PassB_TP_RA_PA',
                              'run transformation pass PassC_TP_RA_PA',
                              'run transformation pass PassB_TP_RA_PA',
                              'run transformation pass PassC_TP_RA_PA'])

    def test_callable_control_flow_plugin(self):
        """Removes do_while, then adds it back. Checks max_iteration still working."""
        controllers_length = len(FlowController.registered_controllers)
        FlowController.remove_flow_controller('do_while')
        self.assertEqual(controllers_length - 1,
                         len(FlowController.registered_controllers))
        FlowController.add_flow_controller('do_while', DoWhileController)
        self.assertEqual(controllers_length, len(FlowController.registered_controllers))
        self.passmanager.append([PassB_TP_RA_PA(), PassC_TP_RA_PA()],
                                do_while=lambda property_set: True, max_iteration=2)
        self.assertSchedulerRaises(self.circuit, self.passmanager,
                                   ['run transformation pass PassA_TP_NR_NP',
                                    'run transformation pass PassB_TP_RA_PA',
                                    'run transformation pass PassC_TP_RA_PA',
                                    'run transformation pass PassB_TP_RA_PA',
                                    'run transformation pass PassC_TP_RA_PA'],
                                   TranspilerError)

    def test_remove_nonexistent_plugin(self):
        """Tries to remove a plugin that does not exist."""
        self.assertRaises(KeyError, FlowController.remove_flow_controller, "foo")


class TestDumpPasses(SchedulerTestCase):
    """Testing the passes method."""

    def test_passes(self):
        """Dump passes in different FlowControllerLinear"""
        passmanager = PassManager()
        passmanager.append(PassC_TP_RA_PA())
        passmanager.append(PassB_TP_RA_PA())

        expected = [{'flow_controllers': {}, 'passes': [PassC_TP_RA_PA()]},
                    {'flow_controllers': {}, 'passes': [PassB_TP_RA_PA()]}]
        self.assertEqual(expected, passmanager.passes())

    def test_passes_in_linear(self):
        """Dump passes in the same FlowControllerLinear"""
        passmanager = PassManager(passes=[
            PassC_TP_RA_PA(),
            PassB_TP_RA_PA(),
            PassD_TP_NR_NP(argument1=[1, 2]),
            PassB_TP_RA_PA()])

        expected = [{'flow_controllers': {}, 'passes': [PassC_TP_RA_PA(),
                                                        PassB_TP_RA_PA(),
                                                        PassD_TP_NR_NP(argument1=[1, 2]),
                                                        PassB_TP_RA_PA()]}]
        self.assertEqual(expected, passmanager.passes())

    def test_control_flow_plugin(self):
        """Dump passes in a custom flow controller."""
        passmanager = PassManager()
        FlowController.add_flow_controller('do_x_times', DoXTimesController)
        passmanager.append([PassB_TP_RA_PA(), PassC_TP_RA_PA()],
                           do_x_times=lambda x: 3)

        expected = [{'passes': [PassB_TP_RA_PA(), PassC_TP_RA_PA()],
                     'flow_controllers': {'do_x_times'}}]
        self.assertEqual(expected, passmanager.passes())

    def test_conditional_and_loop(self):
        """Dump passes with a conditional and a loop."""
        passmanager = PassManager()
        passmanager.append(PassE_AP_NR_NP(True))
        passmanager.append(
            [PassK_check_fixed_point_property(),
             PassA_TP_NR_NP(),
             PassF_reduce_dag_property()],
            do_while=lambda property_set: not property_set['property_fixed_point'],
            condition=lambda property_set: property_set['property_fixed_point'])

        expected = [{'passes': [PassE_AP_NR_NP(True)], 'flow_controllers': {}},
                    {'passes': [PassK_check_fixed_point_property(),
                                PassA_TP_NR_NP(),
                                PassF_reduce_dag_property()], 'flow_controllers': {'condition',
                                                                                   'do_while'}}]
        self.assertEqual(expected, passmanager.passes())


class StreamHandlerRaiseException(StreamHandler):
    """Handler class that will raise an exception on formatting errors."""

    def handleError(self, record):
        raise sys.exc_info()


class TestLogPasses(QiskitTestCase):
    """Testing the log_passes option."""

    def setUp(self):
        logger = getLogger()
        logger.setLevel('DEBUG')
        self.output = io.StringIO()
        logger.addHandler(StreamHandlerRaiseException(self.output))
        self.circuit = QuantumCircuit(QuantumRegister(1))

    def assertPassLog(self, passmanager, list_of_passes):
        """ Runs the passmanager and checks that the elements in
        passmanager.property_set['pass_log'] match list_of_passes (the names)."""
        transpile(self.circuit, pass_manager=passmanager)
        self.output.seek(0)
        # Filter unrelated log lines
        output_lines = self.output.readlines()
        pass_log_lines = [x for x in output_lines if x.startswith('Pass:')]
        for index, pass_name in enumerate(list_of_passes):
            self.assertTrue(pass_log_lines[index].startswith(
                'Pass: %s -' % pass_name))

    def test_passes(self):
        """Dump passes in different FlowControllerLinear"""
        passmanager = PassManager()
        passmanager.append(PassC_TP_RA_PA())
        passmanager.append(PassB_TP_RA_PA())

        self.assertPassLog(passmanager, ['PassA_TP_NR_NP',
                                         'PassC_TP_RA_PA',
                                         'PassB_TP_RA_PA'])

    def test_passes_in_linear(self):
        """Dump passes in the same FlowControllerLinear"""
        passmanager = PassManager(passes=[
            PassC_TP_RA_PA(),
            PassB_TP_RA_PA(),
            PassD_TP_NR_NP(argument1=[1, 2]),
            PassB_TP_RA_PA()])

        self.assertPassLog(passmanager, ['PassA_TP_NR_NP',
                                         'PassC_TP_RA_PA',
                                         'PassB_TP_RA_PA',
                                         'PassD_TP_NR_NP',
                                         'PassA_TP_NR_NP',
                                         'PassB_TP_RA_PA'])

    def test_control_flow_plugin(self):
        """ Dump passes in a custom flow controller. """
        passmanager = PassManager()
        FlowController.add_flow_controller('do_x_times', DoXTimesController)
        passmanager.append([PassB_TP_RA_PA(), PassC_TP_RA_PA()], do_x_times=lambda x: 3)
        self.assertPassLog(passmanager, ['PassA_TP_NR_NP',
                                         'PassB_TP_RA_PA',
                                         'PassC_TP_RA_PA',
                                         'PassB_TP_RA_PA',
                                         'PassC_TP_RA_PA',
                                         'PassB_TP_RA_PA',
                                         'PassC_TP_RA_PA'])

    def test_conditional_and_loop(self):
        """ Dump passes with a conditional and a loop"""
        passmanager = PassManager()
        passmanager.append(PassE_AP_NR_NP(True))
        passmanager.append(
            [PassK_check_fixed_point_property(),
             PassA_TP_NR_NP(),
             PassF_reduce_dag_property()],
            do_while=lambda property_set: not property_set['property_fixed_point'],
            condition=lambda property_set: property_set['property_fixed_point'])
        self.assertPassLog(passmanager, ['PassE_AP_NR_NP'])


class TestPassManagerReuse(SchedulerTestCase):
    """The PassManager instance should be resusable."""

    def setUp(self):
        self.passmanager = PassManager()
        self.circuit = QuantumCircuit(QuantumRegister(1))

    def test_chain_twice(self):
        """ Run a chain twice."""
        self.passmanager.append(PassC_TP_RA_PA())  # Request: PassA / Preserves: PassA
        self.passmanager.append(PassB_TP_RA_PA())  # Request: PassA / Preserves: PassA

        expected = ['run transformation pass PassA_TP_NR_NP',
                    'run transformation pass PassC_TP_RA_PA',
                    'run transformation pass PassB_TP_RA_PA']

        self.assertScheduler(self.passmanager, expected)
        self.assertScheduler(self.passmanager, expected)

    def test_conditional_twice(self):
        """ Run a conditional twice. """
        self.passmanager.append(PassE_AP_NR_NP(True))
        self.passmanager.append(PassA_TP_NR_NP(),
                                condition=lambda property_set: property_set['property'])

        expected = ['run analysis pass PassE_AP_NR_NP',
                    'set property as True',
                    'run transformation pass PassA_TP_NR_NP']

        self.assertScheduler(self.passmanager, expected)
        self.assertScheduler(self.passmanager, expected)

    def test_fixed_point_twice(self):
        """A fixed point scheduler, twice."""
        self.passmanager.append(
            [PassK_check_fixed_point_property(),
             PassA_TP_NR_NP(),
             PassF_reduce_dag_property()],
            do_while=lambda property_set: not property_set['property_fixed_point'])

        expected = ['run analysis pass PassG_calculates_dag_property',
                    'set property as 8 (from dag.property)',
                    'run analysis pass PassK_check_fixed_point_property',
                    'run transformation pass PassA_TP_NR_NP',
                    'run transformation pass PassF_reduce_dag_property',
                    'dag property = 6',
                    'run analysis pass PassG_calculates_dag_property',
                    'set property as 6 (from dag.property)',
                    'run analysis pass PassK_check_fixed_point_property',
                    'run transformation pass PassA_TP_NR_NP',
                    'run transformation pass PassF_reduce_dag_property',
                    'dag property = 5',
                    'run analysis pass PassG_calculates_dag_property',
                    'set property as 5 (from dag.property)',
                    'run analysis pass PassK_check_fixed_point_property',
                    'run transformation pass PassA_TP_NR_NP',
                    'run transformation pass PassF_reduce_dag_property',
                    'dag property = 4',
                    'run analysis pass PassG_calculates_dag_property',
                    'set property as 4 (from dag.property)',
                    'run analysis pass PassK_check_fixed_point_property',
                    'run transformation pass PassA_TP_NR_NP',
                    'run transformation pass PassF_reduce_dag_property',
                    'dag property = 3',
                    'run analysis pass PassG_calculates_dag_property',
                    'set property as 3 (from dag.property)',
                    'run analysis pass PassK_check_fixed_point_property',
                    'run transformation pass PassA_TP_NR_NP',
                    'run transformation pass PassF_reduce_dag_property',
                    'dag property = 2',
                    'run analysis pass PassG_calculates_dag_property',
                    'set property as 2 (from dag.property)',
                    'run analysis pass PassK_check_fixed_point_property',
                    'run transformation pass PassA_TP_NR_NP',
                    'run transformation pass PassF_reduce_dag_property',
                    'dag property = 2',
                    'run analysis pass PassG_calculates_dag_property',
                    'set property as 2 (from dag.property)',
                    'run analysis pass PassK_check_fixed_point_property',
                    'run transformation pass PassA_TP_NR_NP',
                    'run transformation pass PassF_reduce_dag_property',
                    'dag property = 2']

        self.assertScheduler(self.passmanager, expected)
        self.assertScheduler(self.passmanager, expected)


class TestPassManagerReplace(SchedulerTestCase):
    """Test PassManager.replace"""

    def setUp(self):
        self.circuit = QuantumCircuit(QuantumRegister(1))

    def test_replace0(self):
        """ Test passmanager.replace(0, ...)."""
        passmanager = PassManager()
        passmanager.append(PassC_TP_RA_PA())  # Request: PassA / Preserves: PassA
        passmanager.append(PassB_TP_RA_PA())  # Request: PassA / Preserves: PassA

        passmanager.replace(0, PassB_TP_RA_PA())

        expected = ['run transformation pass PassA_TP_NR_NP',
                    'run transformation pass PassB_TP_RA_PA']
        self.assertScheduler(passmanager, expected)

    def test_replace1(self):
        """ Test passmanager.replace(1, ...)."""
        passmanager = PassManager()
        passmanager.append(PassC_TP_RA_PA())  # Request: PassA / Preserves: PassA
        passmanager.append(PassB_TP_RA_PA())  # Request: PassA / Preserves: PassA

        passmanager.replace(1, PassC_TP_RA_PA())

        expected = ['run transformation pass PassA_TP_NR_NP',
                    'run transformation pass PassC_TP_RA_PA']
        self.assertScheduler(passmanager, expected)

    def test_setitem(self):
        """ Test passmanager[1] = ..."""
        passmanager = PassManager()
        passmanager.append(PassC_TP_RA_PA())  # Request: PassA / Preserves: PassA
        passmanager.append(PassB_TP_RA_PA())  # Request: PassA / Preserves: PassA

        passmanager[1] = PassC_TP_RA_PA()

        expected = ['run transformation pass PassA_TP_NR_NP',
                    'run transformation pass PassC_TP_RA_PA']
        self.assertScheduler(passmanager, expected)

    def test_replace_with_conditional(self):
        """ Replace a pass with a conditional pass. """
        passmanager = PassManager()
        passmanager.append(PassE_AP_NR_NP(False))
        passmanager.append(PassB_TP_RA_PA())

        passmanager.replace(1, PassA_TP_NR_NP(),
                            condition=lambda property_set: property_set['property'])

        expected = ['run analysis pass PassE_AP_NR_NP',
                    'set property as False']
        self.assertScheduler(passmanager, expected)

    def test_replace_error(self):
        """ Replace a non-existing index. """
        passmanager = PassManager()
        passmanager.append(PassB_TP_RA_PA())

        with self.assertRaises(TranspilerError):
            passmanager.replace(99, PassA_TP_NR_NP())


if __name__ == '__main__':
    unittest.main()
