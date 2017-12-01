import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../..'))
from qiskit.transpiler import StageBase, StageInputOutput, StageError
import qiskit.mapper as mapper

class CxCancellationStage(StageBase):
    def __init__(self):
        pass

    def get_name(self, name):
        return 'CxCancellationStage'

    def handle_request(self, input):
        dag_circuit = input.get('dag_circuit')

        input.insert('dag_circuit',
            mapper.cx_cancellation(dag_circuit))

        return input

    def check_precondition(self, input):
        if not isinstance(input, StageInputOutput):
            raise StageError('Input instance not supported!')

        if not input.exists('dag_circuit'):
            return False

        return True