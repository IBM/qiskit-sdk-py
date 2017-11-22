import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../..'))
from qiskit.transpiler import StageBase, StageInputOutput, StageError
import qiskit.mapper as mapper

class CouplingStage(StageBase):
    def __init__(self):
        pass

    def get_name(self, name):
        return 'CouplingStage'

    def handle_request(self, input):
        if not self._check_preconditions(input):
            return input

        coupling = input.get('coupling')
        dag_circuit = input.get('dag_circuit')

        dag_output =  mapper.direction_mapper(dag_circuit, coupling)

        input.insert('dag_circuit', dag_output)
        return input

    def _check_preconditions(self, input):
        if not isinstance(input, StageInputOutput):
            raise StageError('Input instance not supported!')

        if not input.exists(['coupling','dag_circuit'])
            return False

        return True