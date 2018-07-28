# -*- coding: utf-8 -*-

# Copyright 2017, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""Shared functionality and helpers for the unit tests."""

from enum import Enum
import functools
import inspect
import logging
import os
import unittest
from unittest.util import safe_repr
from qiskit import __path__ as qiskit_path
from qiskit.backends.ibmq import IBMQProvider
from qiskit.wrapper.credentials import discover_credentials, get_account_name
from qiskit.wrapper.defaultqiskitprovider import DefaultQISKitProvider
from vcr import VCR
from vcr.persisters.filesystem import FilesystemPersister
import json

class Path(Enum):
    """Helper with paths commonly used during the tests."""
    # Main SDK path:    qiskit/
    SDK = qiskit_path[0]
    # test.python path: qiskit/test/python/
    TEST = os.path.dirname(__file__)
    # Examples path:    examples/
    EXAMPLES = os.path.join(SDK, '../examples')
    # Schemas path:     qiskit/schemas
    SCHEMAS = os.path.join(SDK, 'schemas')


class QiskitTestCase(unittest.TestCase):
    """Helper class that contains common functionality."""

    @classmethod
    def setUpClass(cls):
        cls.moduleName = os.path.splitext(inspect.getfile(cls))[0]
        cls.log = logging.getLogger(cls.__name__)

        # Set logging to file and stdout if the LOG_LEVEL environment variable
        # is set.
        if os.getenv('LOG_LEVEL'):
            # Set up formatter.
            log_fmt = ('{}.%(funcName)s:%(levelname)s:%(asctime)s:'
                       ' %(message)s'.format(cls.__name__))
            formatter = logging.Formatter(log_fmt)

            # Set up the file handler.
            log_file_name = '%s.log' % cls.moduleName
            file_handler = logging.FileHandler(log_file_name)
            file_handler.setFormatter(formatter)
            cls.log.addHandler(file_handler)

            # Set the logging level from the environment variable, defaulting
            # to INFO if it is not a valid level.
            level = logging._nameToLevel.get(os.getenv('LOG_LEVEL'),
                                             logging.INFO)
            cls.log.setLevel(level)

    def tearDown(self):
        # Reset the default provider, as in practice it acts as a singleton
        # due to importing the wrapper from qiskit.
        from qiskit.wrapper import _wrapper
        _wrapper._DEFAULT_PROVIDER = DefaultQISKitProvider()

    @staticmethod
    def _get_resource_path(filename, path=Path.TEST):
        """ Get the absolute path to a resource.

        Args:
            filename (string): filename or relative path to the resource.
            path (Path): path used as relative to the filename.
        Returns:
            str: the absolute path to the resource.
        """
        return os.path.normpath(os.path.join(path.value, filename))

    def assertNoLogs(self, logger=None, level=None):
        """
        Context manager to test that no message is sent to the specified
        logger and level (the opposite of TestCase.assertLogs()).
        """
        # pylint: disable=invalid-name
        return _AssertNoLogsContext(self, logger, level)

    def assertDictAlmostEqual(self, dict1, dict2, delta=None, msg=None,
                              places=None, default_value=0):
        """
        Assert two dictionaries with numeric values are almost equal.

        Fail if the two dictionaries are unequal as determined by
        comparing that the difference between values with the same key are
        not greater than delta (default 1e-8), or that difference rounded
        to the given number of decimal places is not zero. If a key in one
        dictionary is not in the other the default_value keyword argument
        will be used for the missing value (default 0). If the two objects
        compare equal then they will automatically compare almost equal.

        Args:
            dict1 (dict): a dictionary.
            dict2 (dict): a dictionary.
            delta (number): threshold for comparison (defaults to 1e-8).
            msg (str): return a custom message on failure.
            places (int): number of decimal places for comparison.
            default_value (number): default value for missing keys.

        Raises:
            TypeError: raises TestCase failureException if the test fails.
        """
        # pylint: disable=invalid-name
        if dict1 == dict2:
            # Shortcut
            return
        if delta is not None and places is not None:
            raise TypeError("specify delta or places not both")

        if places is not None:
            success = True
            standard_msg = ''
            # check value for keys in target
            keys1 = set(dict1.keys())
            for key in keys1:
                val1 = dict1.get(key, default_value)
                val2 = dict2.get(key, default_value)
                if round(abs(val1 - val2), places) != 0:
                    success = False
                    standard_msg += '(%s: %s != %s), ' % (safe_repr(key),
                                                          safe_repr(val1),
                                                          safe_repr(val2))
            # check values for keys in counts, not in target
            keys2 = set(dict2.keys()) - keys1
            for key in keys2:
                val1 = dict1.get(key, default_value)
                val2 = dict2.get(key, default_value)
                if round(abs(val1 - val2), places) != 0:
                    success = False
                    standard_msg += '(%s: %s != %s), ' % (safe_repr(key),
                                                          safe_repr(val1),
                                                          safe_repr(val2))
            if success is True:
                return
            standard_msg = standard_msg[:-2] + ' within %s places' % places

        else:
            if delta is None:
                delta = 1e-8  # default delta value
            success = True
            standard_msg = ''
            # check value for keys in target
            keys1 = set(dict1.keys())
            for key in keys1:
                val1 = dict1.get(key, default_value)
                val2 = dict2.get(key, default_value)
                if abs(val1 - val2) > delta:
                    success = False
                    standard_msg += '(%s: %s != %s), ' % (safe_repr(key),
                                                          safe_repr(val1),
                                                          safe_repr(val2))
            # check values for keys in counts, not in target
            keys2 = set(dict2.keys()) - keys1
            for key in keys2:
                val1 = dict1.get(key, default_value)
                val2 = dict2.get(key, default_value)
                if abs(val1 - val2) > delta:
                    success = False
                    standard_msg += '(%s: %s != %s), ' % (safe_repr(key),
                                                          safe_repr(val1),
                                                          safe_repr(val2))
            if success is True:
                return
            standard_msg = standard_msg[:-2] + ' within %s delta' % delta

        msg = self._formatMessage(msg, standard_msg)
        raise self.failureException(msg)


class _AssertNoLogsContext(unittest.case._AssertLogsContext):
    """A context manager used to implement TestCase.assertNoLogs()."""

    # pylint: disable=inconsistent-return-statements
    def __exit__(self, exc_type, exc_value, tb):
        """
        This is a modified version of TestCase._AssertLogsContext.__exit__(...)
        """
        self.logger.handlers = self.old_handlers
        self.logger.propagate = self.old_propagate
        self.logger.setLevel(self.old_level)
        if exc_type is not None:
            # let unexpected exceptions pass through
            return False

        if self.watcher.records:
            msg = 'logs of level {} or higher triggered on {}:\n'.format(
                logging.getLevelName(self.level), self.logger.name)
            for record in self.watcher.records:
                msg += 'logger %s %s:%i: %s\n' % (record.name, record.pathname,
                                                  record.lineno,
                                                  record.getMessage())

            self._raiseFailure(msg)


def slow_test(func):
    """
    Decorator that signals that the test takes minutes to run.

    Args:
        func (callable): test function to be decorated.

    Returns:
        callable: the decorated function.
    """

    @functools.wraps(func)
    def _(*args, **kwargs):
        if SKIP_SLOW_TESTS:
            raise unittest.SkipTest('Skipping slow tests')
        return func(*args, **kwargs)

    return _


def requires_qe_access(func):
    """
    Decorator that signals that the test uses the online API:
        * determines if the test should be skipped by checking environment
            variables.
        * if the test is not skipped, it reads `QE_TOKEN` and `QE_URL` from
            `Qconfig.py`, environment variables or qiskitrc.
        * if the test is not skipped, it appends `QE_TOKEN` and `QE_URL` as
            arguments to the test function.
    Args:
        func (callable): test function to be decorated.

    Returns:
        callable: the decorated function.
    """
    func = vcr.use_cassette()(func)

    @functools.wraps(func)
    def _(*args, **kwargs):
        # pylint: disable=invalid-name
        if SKIP_ONLINE_TESTS:
            raise unittest.SkipTest('Skipping online tests')

        # Cleanup the credentials, as this file is shared by the tests.
        from qiskit.wrapper import _wrapper
        _wrapper._DEFAULT_PROVIDER = DefaultQISKitProvider()

        # Attempt to read the standard credentials.
        account_name = get_account_name(IBMQProvider)
        discovered_credentials = discover_credentials()
        if account_name in discovered_credentials.keys():
            credentials = discovered_credentials[account_name]
            kwargs.update({
                'QE_TOKEN': credentials.get('token'),
                'QE_URL': credentials.get('url'),
                'hub': credentials.get('hub'),
                'group': credentials.get('group'),
                'project': credentials.get('project'),
            })
        else:
            raise Exception('Could not locate valid credentials')

        return func(*args, **kwargs)

    return _


def _is_ci_fork_pull_request():
    """
    Check if the tests are being run in a CI environment and if it is a pull
    request.

    Returns:
        bool: True if the tests are executed inside a CI tool, and the changes
            are not against the "master" branch.
    """
    if os.getenv('TRAVIS'):
        # Using Travis CI.
        if os.getenv('TRAVIS_PULL_REQUEST_BRANCH'):
            return True
    elif os.getenv('APPVEYOR'):
        # Using AppVeyor CI.
        if os.getenv('APPVEYOR_PULL_REQUEST_NUMBER'):
            return True
    return False


SKIP_ONLINE_TESTS = os.getenv('SKIP_ONLINE_TESTS', _is_ci_fork_pull_request())
SKIP_SLOW_TESTS = os.getenv('SKIP_SLOW_TESTS', True) not in ['false', 'False', '-1']

class IdRemoverPersister(FilesystemPersister):

    @staticmethod
    def getResponsesWith(stringToFind, cassette_dict):
        requests_indeces = [i for i, x in enumerate(cassette_dict['requests']) if stringToFind in x.path]
        return [cassette_dict['responses'][i] for i in requests_indeces]

    @staticmethod
    def getNewId(field, path, id_tracker, _type=str):
        if _type == float:
            return 0.42
        if _type == int:
            return 42
        dummy_name = 'dummy%s%s' % (path.replace('/', ''), field)
        count = len(list(filter(lambda x: str(x).startswith(dummy_name), id_tracker.values())))
        return "%s%02d" % (dummy_name, count + 1)

    @staticmethod
    def getMachingDicts(dataDict, mapList):
        ret = []
        if len(mapList) == 0:
            return ret
        if isinstance(dataDict, list):
            [ ret.extend(IdRemoverPersister.getMachingDicts(i, mapList)) for i in dataDict]
        if isinstance(dataDict, dict):
            if mapList[0] in dataDict.keys():
                if len(mapList) == 1:
                    return [dataDict]
                else:
                    ret.extend(IdRemoverPersister.getMachingDicts(dataDict[mapList[0]],mapList[1:]))
        return ret

    @staticmethod
    def removeIdInAJSON(jsonobj, field, path, id_tracker):
        mapList = field.split('.')
        for machingDict in IdRemoverPersister.getMachingDicts(jsonobj, mapList):
            try:
                oldId = machingDict[mapList[-1]]
                if not oldId in id_tracker:
                    newId = IdRemoverPersister.getNewId(field, path, id_tracker, type(oldId))
                    id_tracker[oldId] = newId
                machingDict[mapList[-1]] = id_tracker[oldId]
            except KeyError:
                pass

    @staticmethod
    def removeIdsInAResponse(response, fields, path, id_tracker):
        body = json.loads(response['body']['string'].decode('utf-8'))
        for field in fields:
            IdRemoverPersister.removeIdInAJSON(body, field, path, id_tracker)
        response['body']['string'] = json.dumps(body).encode('utf-8')

    @staticmethod
    def removeIds(ids2remove, cassette_dict):
        id_tracker = {} # {oldId: newId}
        for path, fields in ids2remove.items():
            responses = IdRemoverPersister.getResponsesWith(path, cassette_dict)
            for response in responses:
                IdRemoverPersister.removeIdsInAResponse(response, fields, path, id_tracker)
        for oldId, newId in id_tracker.items():
            if not isinstance(oldId, str):
                continue
            for request in cassette_dict['requests']:
                request.uri = request.uri.replace(oldId,newId)

    @staticmethod
    def save_cassette(cassette_path, cassette_dict, serializer):
        ids2remove = {'api/users/loginWithToken': ['id',
                                                   'userId',
                                                   'created'],
                      'api/Jobs': ['id',
                                   'userId',
                                   'creationDate',
                                   'qasms.executionId',
                                   'qasms.result.date',
                                   'qasms.result.data.time',
                                   'qasms.result.data.additionalData.seed'],
                      'api/Backends/ibmqx5/queue/status': ['lengthQueue'],
                      'api/Backends/ibmqx4/queue/status': ['lengthQueue']
                      }
        IdRemoverPersister.removeIds(ids2remove, cassette_dict)
        super(IdRemoverPersister, IdRemoverPersister).save_cassette(cassette_path,
                                                                    cassette_dict,
                                                                    serializer)

def purge_headers(headers):
    headerList = list()
    for item in headers:
        if not isinstance(item, tuple):
            item = (item, None)
        headerList.append((item[0], item[1]))

    def before_record_response(response):
        for (header, value) in headerList:
            try:
                if value:
                    response['headers'][header] = value
                else:
                    del response['headers'][header]
            except KeyError:
                pass
        return response

    return before_record_response


vcr = VCR(
    cassette_library_dir='test/cassettes',
    record_mode='once',
    match_on=['uri', 'method'],
    filter_headers=['x-qx-client-application', 'User-Agent'],
    filter_query_parameters=[('access_token','dummyapiusersloginWithTokenid01')],
    filter_post_data_parameters=[('apiToken', 'apiToken_dummy')],
    decode_compressed_response=True,
    before_record_response=purge_headers(['Date',
                                          ('Set-Cookie', 'dummy_cookie'),
                                          'X-Global-Transaction-ID',
                                          'Etag',
                                          'Content-Security-Policy',
                                          'X-Content-Security-Policy',
                                          'X-Webkit-Csp',
                                          'content-length'])
)

vcr.register_persister(IdRemoverPersister)
