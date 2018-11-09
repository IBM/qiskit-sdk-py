# -*- coding: utf-8 -*-

# Copyright 2017, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""This module implements the abstract base class for backend modules.

To create add-on backend modules subclass the Backend class in this module.
Doing so requires that the required backend interface is implemented.
"""
import warnings
from abc import ABC, abstractmethod

from marshmallow.fields import String, Boolean, Integer
from marshmallow.validate import Range, Regexp

import qiskit
from qiskit._qiskiterror import QISKitError
from qiskit.validation import BaseModel, BaseSchema, bind_schema


class BaseBackend(ABC):
    """Base class for backends."""

    @abstractmethod
    def __init__(self, configuration, provider=None):
        """Base class for backends.

        This method should initialize the module and its configuration, and
        raise an exception if a component of the module is
        not available.

        Args:
            configuration (dict): configuration dictionary
            provider (BaseProvider): provider responsible for this backend

        Raises:
            FileNotFoundError if backend executable is not available.
            QISKitError: if there is no name in the configuration
        """
        if 'name' not in configuration:
            raise QISKitError('backend does not have a name.')
        self._configuration = configuration
        self.provider = provider

    @abstractmethod
    def run(self, qobj):
        """Run a Qobj on the the backend."""
        pass

    def configuration(self):
        """Return backend configuration"""
        return self._configuration

    def calibration(self):
        """Return backend calibration"""
        warnings.warn("Backends will no longer return a calibration dictionary,"
                      "use backend.properties() instead.", DeprecationWarning)
        return {}

    def parameters(self):
        """Return backend parameters"""
        warnings.warn("Backends will no longer return a parameters dictionary, "
                      "use backend.properties() instead.", DeprecationWarning)
        return {}

    def properties(self):
        """Return backend properties"""
        return {}

    def status(self):
        """Return backend status"""
        return {'backend_name': self.name(),
                #  Backend version in the form X.X.X
                'backend_version': qiskit.__version__,
                #  Backend operational and accepting jobs (true/false)
                'operational': True,
                'pending_jobs': 0,
                'status_msg': ''}

    def name(self):
        """Return backend name"""
        return self._configuration['name']

    def __str__(self):
        return self.name()

    def __repr__(self):
        """Official string representation of a Backend.

        Note that, by Qiskit convention, it is consciously *not* a fully valid
        Python expression. Subclasses should provide 'a string of the form
        <...some useful description...>'. [0]

        [0] https://docs.python.org/3/reference/datamodel.html#object.__repr__
        """
        return "<{}('{}') from {}()>".format(self.__class__.__name__,
                                             self.name(),
                                             self.provider)


class BackendStatusSchema(BaseSchema):
    """Schema for BackendStatus."""

    # Required fields.
    backend_name = String(required=True)
    backend_version = String(required=True,
                             validate=Regexp('[0-9]+.[0-9]+.[0-9]+$'))
    operational = Boolean(required=True)
    pending_jobs = Integer(required=True,
                           validate=Range(min=0))
    status_msg = String(required=True)


@bind_schema(BackendStatusSchema)
class BackendStatus(BaseModel):
    """Backend Status."""

    schema_cls = BackendStatusSchema

    def __init__(self, backend_name, backend_version, operational,
                 pending_jobs, status_msg,
                 **kwargs):
        self.backend_name = backend_name
        self.backend_version = backend_version
        self.operational = operational
        self.pending_jobs = pending_jobs
        self.status_msg = status_msg

        kwargs.update(self.__dict__)
        super().__init__(**kwargs)
