# This code is part of Qiskit.
#
# (C) Copyright IBM 2017, 2019.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

# pylint: disable=invalid-name
"""
Decompose a single-qubit unitary via Euler angles.
"""
import warnings
import math
import numpy as np
import scipy.linalg as la

from qiskit.circuit.quantumcircuit import QuantumCircuit
from qiskit.circuit.library.standard_gates import (UGate, PhaseGate, RXGate, RYGate, RZGate,
                                                   SXGate, RGate, U1Gate, U2Gate, U3Gate)
from qiskit.exceptions import QiskitError
from qiskit.quantum_info.operators.predicates import is_unitary_matrix

DEFAULT_ATOL = 1e-12


class OneQubitEulerDecomposer:
    r"""A class for decomposing 1-qubit unitaries into Euler angle rotations.

    The resulting decomposition is parameterized by 3 Euler rotation angle
    parameters :math:`(\theta, \phi, \lambda)`, and a phase parameter
    :math:`\gamma`. The value of the parameters for an input unitary depends
    on the decomposition basis. Allowed bases and the resulting circuits are
    shown in the following table. Note that for the non-Euler bases (U, PSX,
    RR), the ZYZ euler parameters are used.

    .. list-table:: Supported circuit bases
        :widths: auto
        :header-rows: 1

        * - Basis
          - Euler Angle Basis
          - Decomposition Circuit
        * - 'ZYZ'
          - :math:`Z(\phi) Y(\theta) Z(\lambda)`
          - :math:`e^{i\gamma} R_Z(\phi).R_Y(\theta).R_Z(\lambda)`
        * - 'ZXZ'
          - :math:`Z(\phi) X(\theta) Z(\lambda)`
          - :math:`e^{i\gamma} R_Z(\phi).R_X(\theta).R_Z(\lambda)`
        * - 'XYX'
          - :math:`X(\phi) Y(\theta) X(\lambda)`
          - :math:`e^{i\gamma} R_X(\phi).R_Y(\theta).R_X(\lambda)`
        * - 'U'
          - :math:`Z(\phi) Y(\theta) Z(\lambda)`
          - :math:`e^{i\gamma} U(\theta,\phi,\lambda)`
        * - 'PSX'
          - :math:`Z(\phi) Y(\theta) Z(\lambda)`
          - :math:`e^{i\gamma} U_1(\phi+\pi).R_X\left(\frac{\pi}{2}\right).`
            :math:`U_1(\theta+\pi).R_X\left(\frac{\pi}{2}\right).U_1(\lambda)`
        * - 'RR'
          - :math:`Z(\phi) Y(\theta) Z(\lambda)`
          - :math:`e^{i\gamma} R\left(-\pi,\frac{\phi-\lambda+\pi}{2}\right).`
            :math:`R\left(\theta+\pi,\frac{\pi}{2}-\lambda\right)`
    """

    def __init__(self, basis='U'):
        """Initialize decomposer

        Supported bases are: 'U', 'PSX', 'RR', 'ZYZ', 'ZXZ', 'XYX'.

        Args:
            basis (str): the decomposition basis [Default: 'U']

        Raises:
            QiskitError: If input basis is not recognized.
        """
        self.basis = basis  # sets: self._basis, self._params, self._circuit

    def __call__(self,
                 unitary,
                 simplify=True,
                 atol=DEFAULT_ATOL):
        """Decompose single qubit gate into a circuit.

        Args:
            unitary (Operator or Gate or array): 1-qubit unitary matrix
            simplify (bool): reduce gate count in decomposition [Default: True].
            atol (bool): absolute tolerance for checking angles when simplifing
                         returnd circuit [Default: 1e-12].

        Returns:
            QuantumCircuit: the decomposed single-qubit gate circuit

        Raises:
            QiskitError: if input is invalid or synthesis fails.
        """
        if hasattr(unitary, 'to_operator'):
            # If input is a BaseOperator subclass this attempts to convert
            # the object to an Operator so that we can extract the underlying
            # numpy matrix from `Operator.data`.
            unitary = unitary.to_operator().data
        elif hasattr(unitary, 'to_matrix'):
            # If input is Gate subclass or some other class object that has
            # a to_matrix method this will call that method.
            unitary = unitary.to_matrix()
        # Convert to numpy array incase not already an array
        unitary = np.asarray(unitary, dtype=complex)

        # Check input is a 2-qubit unitary
        if unitary.shape != (2, 2):
            raise QiskitError("OneQubitEulerDecomposer: "
                              "expected 2x2 input matrix")
        if not is_unitary_matrix(unitary):
            raise QiskitError("OneQubitEulerDecomposer: "
                              "input matrix is not unitary.")
        theta, phi, lam, _ = self._params(unitary)
        circuit = self._circuit(theta, phi, lam,
                                simplify=simplify,
                                atol=atol)
        return circuit

    @property
    def basis(self):
        """The decomposition basis."""
        return self._basis

    @basis.setter
    def basis(self, basis):
        """Set the decomposition basis."""
        basis_methods = {
            'U': (self._params_u, self._circuit_u),
            'U3': (self._params_u, self._circuit_u3),
            'U1U2U3': (self._params_u, self._circuit_u1u2u3),
            'PSX': (self._params_psx, self._circuit_psx),
            'RR': (self._params_zyz, self._circuit_rr),
            'ZYZ': (self._params_zyz, self._circuit_zyz),
            'ZXZ': (self._params_zxz, self._circuit_zxz),
            'XYX': (self._params_xyx, self._circuit_xyx)
        }
        if basis == 'U1X':
            warnings.warn('Deprecated U1X basis, use PSX (phase + square-root(X)) instead.',
                          DeprecationWarning)
            basis = 'PSX'
        if basis not in basis_methods:
            raise QiskitError("OneQubitEulerDecomposer: unsupported basis {}".format(basis))
        self._basis = basis
        self._params, self._circuit = basis_methods[self._basis]

    def angles(self, unitary):
        """Return the Euler angles for input array.

        Args:
            unitary (np.ndarray): 2x2 unitary matrix.

        Returns:
            tuple: (theta, phi, lambda).
        """
        theta, phi, lam, _ = self._params(unitary)
        return theta, phi, lam

    def angles_and_phase(self, unitary):
        """Return the Euler angles and phase for input array.

        Args:
            unitary (np.ndarray): 2x2 unitary matrix.

        Returns:
            tuple: (theta, phi, lambda, phase).
        """
        return self._params(unitary)

    @staticmethod
    def _params_zyz(mat):
        """Return the euler angles and phase for the ZYZ basis."""
        # We rescale the input matrix to be special unitary (det(U) = 1)
        # This ensures that the quaternion representation is real
        coeff = la.det(mat)**(-0.5)
        phase = -np.angle(coeff)
        su_mat = coeff * mat  # U in SU(2)
        # OpenQASM SU(2) parameterization:
        # U[0, 0] = exp(-i(phi+lambda)/2) * cos(theta/2)
        # U[0, 1] = -exp(-i(phi-lambda)/2) * sin(theta/2)
        # U[1, 0] = exp(i(phi-lambda)/2) * sin(theta/2)
        # U[1, 1] = exp(i(phi+lambda)/2) * cos(theta/2)
        theta = 2 * math.atan2(abs(su_mat[1, 0]), abs(su_mat[0, 0]))
        phiplambda = 2 * np.angle(su_mat[1, 1])
        phimlambda = 2 * np.angle(su_mat[1, 0])
        phi = (phiplambda + phimlambda) / 2.0
        lam = (phiplambda - phimlambda) / 2.0
        return _mod2pi(theta), _mod2pi(phi), _mod2pi(lam), _mod2pi(phase)

    @staticmethod
    def _params_zxz(mat):
        """Return the euler angles and phase for the ZXZ basis."""
        theta, phi, lam, phase = OneQubitEulerDecomposer._params_zyz(mat)
        return (_mod2pi(theta), _mod2pi(phi + np.pi / 2),
                _mod2pi(lam - np.pi / 2), _mod2pi(phase))

    @staticmethod
    def _params_xyx(mat):
        """Return the euler angles and phase for the XYX basis."""
        # We use the fact that
        # Rx(a).Ry(b).Rx(c) = H.Rz(a).Ry(-b).Rz(c).H
        mat_zyz = 0.5 * np.array(
            [[
                mat[0, 0] + mat[0, 1] + mat[1, 0] + mat[1, 1],
                mat[0, 0] - mat[0, 1] + mat[1, 0] - mat[1, 1]
            ],
             [
                 mat[0, 0] + mat[0, 1] - mat[1, 0] - mat[1, 1],
                 mat[0, 0] - mat[0, 1] - mat[1, 0] + mat[1, 1]
             ]],
            dtype=complex)
        theta, phi, lam, phase = OneQubitEulerDecomposer._params_zyz(mat_zyz)
        return _mod2pi(-theta), _mod2pi(phi), _mod2pi(lam), _mod2pi(phase)

    @staticmethod
    def _params_u(mat):
        """Return the euler angles and phase for the U basis."""
        # The determinant of U gate depends on its params
        # via det(u(theta, phi, lam)) = exp(1j*(phi+lam))
        # Since the phase is wrt to a SU matrix we must rescale
        # phase to correct this
        theta, phi, lam, phase = OneQubitEulerDecomposer._params_zyz(mat)
        return (_mod2pi(theta), _mod2pi(phi), _mod2pi(lam),
                _mod2pi(phase - 0.5 * (phi + lam)))

    @staticmethod
    def _params_psx(mat):
        """Return the euler angles and phase for the PSX basis."""
        # The determinant of this decomposition depends on its params
        # Since the phase is wrt to a SU matrix we must rescale
        # phase to correct this
        theta, phi, lam, phase = OneQubitEulerDecomposer._params_zyz(mat)
        return (_mod2pi(theta), _mod2pi(phi), _mod2pi(lam),
                _mod2pi(phase - 0.5 * (theta + phi + lam)))

    @staticmethod
    def _circuit_zyz(theta,
                     phi,
                     lam,
                     simplify=True,
                     atol=DEFAULT_ATOL):
        circuit = QuantumCircuit(1)
        if simplify and np.isclose(theta, 0.0, atol=atol):
            circuit.append(RZGate(phi + lam), [0])
            return circuit
        if not simplify or not np.isclose(lam, 0.0, atol=atol):
            circuit.append(RZGate(lam), [0])
        if not simplify or not np.isclose(theta, 0.0, atol=atol):
            circuit.append(RYGate(theta), [0])
        if not simplify or not np.isclose(phi, 0.0, atol=atol):
            circuit.append(RZGate(phi), [0])
        return circuit

    @staticmethod
    def _circuit_zxz(theta,
                     phi,
                     lam,
                     simplify=False,
                     atol=DEFAULT_ATOL):
        if simplify and np.isclose(theta, 0.0, atol=atol):
            circuit = QuantumCircuit(1)
            circuit.append(RZGate(phi + lam), [0])
            return circuit
        circuit = QuantumCircuit(1)
        if not simplify or not np.isclose(lam, 0.0, atol=atol):
            circuit.append(RZGate(lam), [0])
        if not simplify or not np.isclose(theta, 0.0, atol=atol):
            circuit.append(RXGate(theta), [0])
        if not simplify or not np.isclose(phi, 0.0, atol=atol):
            circuit.append(RZGate(phi), [0])
        return circuit

    @staticmethod
    def _circuit_xyx(theta,
                     phi,
                     lam,
                     simplify=True,
                     atol=DEFAULT_ATOL):
        circuit = QuantumCircuit(1)
        if simplify and np.isclose(theta, 0.0, atol=atol):
            circuit.append(RXGate(phi + lam), [0])
            return circuit
        if not simplify or not np.isclose(lam, 0.0, atol=atol):
            circuit.append(RXGate(lam), [0])
        if not simplify or not np.isclose(theta, 0.0, atol=atol):
            circuit.append(RYGate(theta), [0])
        if not simplify or not np.isclose(phi, 0.0, atol=atol):
            circuit.append(RXGate(phi), [0])
        return circuit

    @staticmethod
    def _circuit_u(theta,
                   phi,
                   lam,
                   simplify=True,
                   atol=DEFAULT_ATOL):
        # pylint: disable=unused-argument
        circuit = QuantumCircuit(1)
        circuit.append(UGate(theta, phi, lam), [0])
        return circuit

    @staticmethod
    def _circuit_u3(theta,
                    phi,
                    lam,
                    simplify=True,
                    atol=DEFAULT_ATOL):
        # pylint: disable=unused-argument
        circuit = QuantumCircuit(1)
        circuit.append(U3Gate(theta, phi, lam), [0])
        return circuit

    @staticmethod
    def _circuit_u1u2u3(theta,
                        phi,
                        lam,
                        simplify=True,
                        atol=DEFAULT_ATOL):
        # pylint: disable=unused-argument
        circuit = QuantumCircuit(1)
        new_op = U3Gate(theta, phi, lam)
        if simplify and np.isclose(theta, [0., 2*np.pi], atol=atol).any():
            if np.isclose(_mod2pi(phi+lam), [0., 2*np.pi], atol=atol).any():
                new_op = None
            else:
                new_op = U1Gate(_mod2pi(phi+lam))
        elif simplify and np.isclose(theta, [np.pi/2, 3*np.pi/2], atol=atol).any():
            new_op = U2Gate(_mod2pi(phi+theta-np.pi/2), _mod2pi(lam+theta-np.pi/2))
        if new_op is not None:
            circuit.append(new_op, [0])
        return circuit

    @staticmethod
    def _circuit_psx(theta,
                     phi,
                     lam,
                     simplify=True,
                     atol=DEFAULT_ATOL):
        # Shift theta and phi so decomposition is
        # Phase(phi+pi).SX.Phase(theta+pi).SX.Phase(lam)
        theta = _mod2pi(theta + np.pi)
        phi = _mod2pi(phi + np.pi)
        print('theta, phi ', theta, phi)
        circuit = QuantumCircuit(1)
        # Check for decomposition into minimimal number required SX gates
        if simplify and np.isclose(abs(theta), np.pi, atol=atol):
            if np.isclose(_mod2pi(lam + phi + theta), [0., 2*np.pi], atol=atol).any():
                pass
            else:
                circuit.append(PhaseGate(_mod2pi(lam + phi + theta)), [0])
        elif simplify and np.isclose(abs(theta), [np.pi/2, 3*np.pi/2], atol=atol).any():
            circuit.append(PhaseGate(_mod2pi(lam + theta)), [0])
            circuit.append(SXGate(), [0])
            circuit.append(PhaseGate(_mod2pi(phi + theta)), [0])
        else:
            circuit.append(PhaseGate(lam), [0])
            circuit.append(SXGate(), [0])
            circuit.append(PhaseGate(theta), [0])
            circuit.append(SXGate(), [0])
            circuit.append(PhaseGate(phi), [0])
        return circuit

    @staticmethod
    def _circuit_rr(theta,
                    phi,
                    lam,
                    simplify=True,
                    atol=DEFAULT_ATOL):
        circuit = QuantumCircuit(1)
        if not simplify or not np.isclose(theta, -np.pi, atol=atol):
            circuit.append(RGate(theta + np.pi, np.pi / 2 - lam), [0])
        circuit.append(RGate(-np.pi, 0.5 * (phi - lam + np.pi)), [0])
        return circuit


def _mod2pi(angle):
    if angle >= 0:
        return np.mod(angle, 2*np.pi)
    else:
        return np.mod(angle, -2*np.pi)
