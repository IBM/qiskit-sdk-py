# -*- coding: utf-8 -*-

# Copyright 2018, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

# pylint: disable=invalid-name,super-init-not-called

"""Dummy passes used by Transpiler testing"""

import logging
from qiskit.transpiler.passes import FixedPoint

from qiskit.transpiler import TransformationPass, AnalysisPass

logger = "LocalLogger"


class DummyTP(TransformationPass):
    """ A dummy transformation pass."""

    def run(self, dag):
        logging.getLogger(logger).info('run transformation pass %s', self.name())
        return dag


class DummyAP(AnalysisPass):
    """ A dummy analysis pass."""

    def run(self, dag):
        logging.getLogger(logger).info('run analysis pass %s', self.name())


class PassA_TP_NR_NP(DummyTP):
    """ A dummy pass without any requires/preserves.
    TP: Transformation Pass
    NR: No requires
    NP: No preserves
    """

    def __init__(self):
        super().__init__()
        self.preserves.append(self)  # preserves itself (idempotence)


class PassB_TP_RA_PA(DummyTP):
    """ A dummy pass that requires PassA_TP_NR_NP and preserves it.
    TP: Transformation Pass
    RA: Requires PassA
    PA: Preserves PassA
    """

    def __init__(self):
        super().__init__()
        self.requires.append(PassA_TP_NR_NP())
        self.preserves.append(PassA_TP_NR_NP())
        self.preserves.append(self)  # preserves itself (idempotence)


class PassC_TP_RA_PA(DummyTP):
    """ A dummy pass that requires PassA_TP_NR_NP and preserves it.
    TP: Transformation Pass
    RA: Requires PassA
    PA: Preserves PassA
    """

    def __init__(self):
        super().__init__()
        self.requires.append(PassA_TP_NR_NP())
        self.preserves.append(PassA_TP_NR_NP())
        self.preserves.append(self)  # preserves itself (idempotence)


class PassD_TP_NR_NP(DummyTP):
    """ A dummy transfomation pass that takes an argument.
    TP: Transformation Pass
    NR: No Requires
    NP: No Preserves
    """

    def __init__(self, argument1=None, argument2=None):
        super().__init__()
        self.argument1 = argument1
        self.argument2 = argument2
        self.preserves.append(self)  # preserves itself (idempotence)

    def run(self, dag):
        super().run(dag)
        logging.getLogger(logger).info('argument %s', self.argument1)
        return dag


class PassE_AP_NR_NP(DummyAP):
    """ A dummy analysis pass that takes an argument.
    AP: Analysis Pass
    NR: No Requires
    NP: No Preserves
    """

    def __init__(self, argument1):
        super().__init__()
        self.argument1 = argument1

    def run(self, dag):
        super().run(dag)
        self.property_set['property'] = self.argument1
        logging.getLogger(logger).info('set property as %s', self.property_set['property'])


class PassF_reduce_dag_property(DummyTP):
    """ A dummy transformation pass that (sets and) reduces a property in the DAG.
    NI: Non-idempotent transformation pass
    NR: No Requires
    NP: No Preserves
    """

    def run(self, dag):
        super().run(dag)
        if not hasattr(dag, 'property'):
            dag.property = 8
        dag.property = round(dag.property * 0.8)
        logging.getLogger(logger).info('dag property = %i', dag.property)
        return dag


class PassG_calculates_dag_property(DummyAP):
    """ A dummy transformation pass that "calculates" property in the DAG.
    AP: Analysis Pass
    NR: No Requires
    NP: No Preserves
    """

    def run(self, dag):
        super().run(dag)
        if hasattr(dag, 'property'):
            self.property_set['property'] = dag.property
        else:
            self.property_set['property'] = 8
        logging.getLogger(logger).info('set property as %s (from dag.property)',
                                       self.property_set['property'])


class PassH_Bad_TP(DummyTP):
    """ A dummy transformation pass tries to modify the property set.
    NR: No Requires
    NP: No Preserves
    """

    def run(self, dag):
        super().run(dag)
        self.property_set['property'] = "value"
        logging.getLogger(logger).info('set property as %s', self.property_set['property'])
        return dag


class PassI_Bad_AP(DummyAP):
    """ A dummy analysis pass tries to modify the dag.
    NR: No Requires
    NP: No Preserves
    """

    def run(self, dag):
        super().run(dag)
        cx_runs = dag.collect_runs(["cx"])

        # Convert to ID so thatcan be checked if in correct order
        cx_runs_ids = set()
        for run in cx_runs:
            curr = []
            for node in run:
                curr.append(node._node_id)
            cx_runs_ids.add(tuple(curr))

        logging.getLogger(logger).info('cx_runs: %s', cx_runs_ids)
        dag._remove_op_node(cx_runs.pop()[0])
        logging.getLogger(logger).info('done removing')


class PassJ_Bad_NoReturn(DummyTP):
    """ A bad dummy transformation pass that does not return a DAG.
    NR: No Requires
    NP: No Preserves
    """

    def run(self, dag):
        super().run(dag)
        return "Something else than DAG"


class PassK_check_fixed_point_property(DummyAP, FixedPoint):
    """ A dummy analysis pass that checks if a property reached a fixed point. The results is saved
    in property_set['fixed_point'][<property>] as a boolean
    AP: Analysis Pass
    R: PassG_calculates_dag_property()
    """

    def __init__(self):
        FixedPoint.__init__(self, 'property')
        self.requires.append(PassG_calculates_dag_property())

    def run(self, dag):
        for base in PassK_check_fixed_point_property.__bases__:
            base.run(self, dag)
