import qiskit.extensions.standard
from IBMQuantumExperience import RegisterSizeError

from ._qiskiterror import QISKitError
from ._classicalregister import ClassicalRegister
from ._quantumregister import QuantumRegister
from ._quantumcircuit import QuantumCircuit
from ._gate import Gate
from ._compositegate import CompositeGate
from ._instruction import Instruction
from ._instructionset import InstructionSet
<<<<<<< HEAD
from ._jobprocessor import JobProcessor
from ._quantumjob import QuantumJob
=======
from ._qiskiterror import QISKitError
from ._jobprocessor import JobProcessor, QuantumJob
>>>>>>> Redone the corrections that were harmeless in the previously reverted commit
from ._quantumprogram import QuantumProgram
from ._result import Result


__version__ = '0.4.0'

