# -*- coding: utf-8 -*-

# Copyright 2018, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""Schema and Model for schema-conformant Results.

TODO: Note this file is temporary, and will be removed before 0.7, replacing
      qiskit.qobj.result and qiskit.result.
"""

from marshmallow.fields import Boolean, DateTime, Integer, List, Nested, Raw, String
from marshmallow.validate import Length, OneOf, Regexp, Range

from qiskit.validation.base import BaseModel, BaseSchema, ObjSchema, bind_schema
from qiskit.validation.fields import Complex, ByType
from qiskit.validation.validate import PatternProperties


class ExperimentResultDataSchema(BaseSchema):
    """Schema for ExperimentResultData."""

    counts = Nested(ObjSchema,
                    validate=PatternProperties(
                        {Regexp('^0x([0-9A-Fa-f])+$'): Integer()}))
    snapshots = Nested(ObjSchema)
    memory = List(Raw(),
                  validate=Length(min=1))
    statevector = List(List(Complex(),
                            validate=Length(min=1)))
    unitary = List(List(List(Complex(),
                             validate=Length(min=1)),
                        validate=Length(min=1)),
                   validate=Length(min=1))


class ExperimentResultSchema(BaseSchema):
    """Schema for ExperimentResult."""

    # Required fields.
    shots = ByType([Integer(), List(Integer(validate=Range(min=1)),
                                    validate=Length(equal=2))],
                   required=True)
    success = Boolean(required=True)
    data = Nested(ExperimentResultDataSchema, required=True)

    # Optional fields.
    status = String()
    seed = Integer()
    meas_return = String(validate=OneOf(['single', 'avg']))
    header = Nested(ObjSchema)


class ResultSchema(BaseSchema):
    """Schema for Result."""

    # Required fields.
    backend_name = String(required=True)
    backend_version = String(required=True,
                             validate=Regexp('[0-9]+.[0-9]+.[0-9]+$'))
    qobj_id = String(required=True)
    job_id = String(required=True)
    success = Boolean(required=True)
    results = Nested(ExperimentResultSchema, required=True, many=True)

    # Optional fields.
    date = DateTime()
    status = String()
    header = Nested(ObjSchema)


@bind_schema(ExperimentResultDataSchema)
class ExperimentResultData(BaseModel):
    """Model for ExperimentResultData.

    Please note that this class only describes the required fields. For the
    full description of the model, please check
    ``ExperimentResultDataSchema``.
    """
    pass


@bind_schema(ExperimentResultSchema)
class ExperimentResult(BaseModel):
    """Model for ExperimentResult.

    Please note that this class only describes the required fields. For the
    full description of the model, please check ``ExperimentResultSchema``.

    Attributes:
        shots (int or tuple): the starting and ending shot for this data.
        success (bool): if true, we can trust results for this experiment.
        data (ExperimentResultData): results information.
    """

    def __init__(self, shots, success, data, **kwargs):
        self.shots = shots
        self.success = success
        self.data = data

        super().__init__(**kwargs)


@bind_schema(ResultSchema)
class Result(BaseModel):
    """Model for Results.

    Please note that this class only describes the required fields. For the
    full description of the model, please check ``ResultSchema``.

    Attributes:
        backend_name (str): backend name.
        backend_version (str): backend version, in the form X.Y.Z.
        qobj_id (str): user-generated Qobj id.
        job_id (str): unique execution id from the backend.
        success (bool): True if complete input qobj executed correctly. (Implies
            each experiment success)
        results (ExperimentResult): corresponding results for array of
            experiments of the input qobj
    """

    def __init__(self, backend_name, backend_version, qobj_id, job_id, success,
                 results, **kwargs):
        self.backend_name = backend_name
        self.backend_version = backend_version
        self.qobj_id = qobj_id
        self.job_id = job_id
        self.success = success
        self.results = results

        super().__init__(**kwargs)
