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

from time import time

class EquivalenceCheckerResult():
    def __init__(self, success, equivalent, time_taken,
                 circname1, circname2, error_msg):
        self.success = success
        self.time_taken = time_taken
        self.equivalent = equivalent
        self.circname1 = circname1
        self.circname2 = circname2
        self.error_msg = error_msg

class EquivalenceChecker():
    def run(self, circ1, circ2):
        start = time()
        
        from qiskit.quantum_info.operators import Operator
        equivalent = None
        success = True
        error_msg = ''

        ops = []
        circs = [circ1, circ2]

        for circ in circs:
            try:
                op = Operator(circ)
                ops.append(op)
            except Exception as e:
                error_msg += 'Circuit ' + circ.name + ' is invalid: ' + str(e) + '\n'
                success = False

        if success:
            try:
                equivalent = (ops[0] == ops[1])
            except:
                error_msg = e
                success = False

        time_taken = time() - start
        return EquivalenceCheckerResult(success, equivalent, time_taken,
                                        circ1.name, circ2.name, error_msg)
