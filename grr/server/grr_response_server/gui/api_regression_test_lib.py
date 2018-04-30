#!/usr/bin/env python
"""Base test classes for API handlers tests."""

import abc
import json
import logging
import os
import re
import socket
import sys


import psutil
import pytest

from grr.lib import flags
from grr.lib import registry
from grr.lib import utils
from grr.server.grr_response_server.gui import api_auth_manager
# This import guarantees that all API-related RDF types will get imported
# (as they're all references by api_call_router).
# pylint: disable=unused-import
from grr.server.grr_response_server.gui import api_call_router
# pylint: enable=unused-import
from grr.server.grr_response_server.gui import api_regression_http
from grr.server.grr_response_server.gui import webauth
from grr.test_lib import test_lib

flags.DEFINE_string(
    "generate", "",
    "Generate golden regression data for tests using a given connection type.")


class ApiRegressionTestMetaclass(registry.MetaclassRegistry):
  """Automatica test classes generation through a metaclass."""

  connection_mixins = {}

  @classmethod
  def RegisterConnectionMixin(cls, mixin):
    cls.connection_mixins[mixin.connection_type] = mixin

  def __init__(cls, name, bases, env_dict):  # pylint: disable=no-self-argument
    registry.MetaclassRegistry.__init__(cls, name, bases, env_dict)

    has_mixin = False
    for mixin in cls.connection_mixins.values():
      if issubclass(cls, mixin):
        has_mixin = True
        break

    # ApiRegressionTest is a base class, so it doesn't make sense to generate
    # _http_v1/_http_v2 classes for it.
    # Generating classes from already generated classes would lead to infinite
    # recursion. Skipping the generated ones.
    if name == "ApiRegressionTest" or has_mixin:
      return

    for mixin in ApiRegressionTestMetaclass.connection_mixins.values():
      if (mixin.skip_legacy_dynamic_proto_tests and
          getattr(cls, "uses_legacy_dynamic_protos", False)):
        continue

      cls_name = "%s_%s" % (name, mixin.connection_type)
      test_cls = type(
          cls_name,
          (mixin, cls, test_lib.GRRBaseTest),
          # pylint: disable=protected-access
          {"testForRegression": lambda x: x._testForRegression()})
      module = sys.modules[cls.__module__]
      setattr(module, cls_name, test_cls)


ApiRegressionTestMetaclass.RegisterConnectionMixin(
    api_regression_http.HttpApiV1RegressionTestMixin)
ApiRegressionTestMetaclass.RegisterConnectionMixin(
    api_regression_http.HttpApiV2RegressionTestMixin)
ApiRegressionTestMetaclass.RegisterConnectionMixin(
    api_regression_http.HttpApiV2RelationalDBRegressionTestMixin)


@pytest.mark.small
@pytest.mark.api_regression
class ApiRegressionTest(test_lib.GRRBaseTest):
  """Base class for API handlers regression tests.

  Regression tests are supposed to implement a single abstract Run() method.

  In the Run() implementation they're supposed to set up necessary environment
  and do a number of Check() calls. Every Check() call fetches a particular URL
  and keeps the data. Then, if this test class is used as part of a test suite,
  generated data will be compared with ones in the api regression data file and
  exception will be raised if they're different.

  Alternatively, if this class is used in
  api_handlers_regression_data_generate.py, then generated data will be
  aggregated with data from other test classes and printed to the stdout.

  """

  __metaclass__ = ApiRegressionTestMetaclass

  # Name of the ApiCallRouter's method that's tested in this class.
  api_method = None
  # Handler class that's used to handle the requests.
  handler = None

  # The api_regression label can be used to exclude/include API regression
  # tests from/into test runs.

  # TODO(user): gpylint claims "Use of super on an old style class", but
  # this class is obviously not an old-style class.
  # pylint: disable=super-on-old-class
  def setUp(self):  # pylint: disable=invalid-name
    """Set up test method."""
    super(ApiRegressionTest, self).setUp()

    if not self.__class__.api_method:
      raise ValueError("%s.api_method has to be set." % self.__class__.__name__)

    if not self.__class__.handler:
      raise ValueError("%s.handler has to be set." % self.__class__.__name__)

    self.checks = []

    p = psutil.Process(os.getpid())
    self.syscalls_stubber = utils.MultiStubber(
        (socket, "gethostname", lambda: "test.host"),
        (os, "getpid", lambda: 42), (psutil, "Process", lambda _=None: p))
    self.syscalls_stubber.Start()

    self.token.username = "api_test_user"
    webauth.WEBAUTH_MANAGER.SetUserName(self.token.username)

    # Force creation of new APIAuthorizationManager.
    api_auth_manager.APIACLInit.InitApiAuthManager()

    self.config_overrider = test_lib.ConfigOverrider({
        # For regression tests we want to use a fixed version number instead of
        # current one. Otherwise regression data would have to be re-generated
        # each time GRR version is increased.
        "Source.version_major": 1,
        "Source.version_minor": 2,
        "Source.version_revision": 3,
        "Source.version_release": 4,
        "Source.version_string": "1.2.3.4",
        "Source.version_numeric": 1234,
    })
    self.config_overrider.Start()

  # TODO(user): gpylint claims "Use of super on an old style class", but
  # this class is obviously not an old-style class.
  def tearDown(self):  # pylint: disable=invalid-name
    """Tear down test method."""
    super(ApiRegressionTest, self).tearDown()
    self.config_overrider.Start()
    self.syscalls_stubber.Stop()

  def _Replace(self, content, replace=None):
    """Applies replace function to a given content."""

    # replace the values of all tracebacks by <traceback content>
    regex = re.compile(r'"traceBack": "Traceback[^"\\]*(?:\\.[^"\\]*)*"',
                       re.DOTALL)
    content = regex.sub('"traceBack": "<traceback content>"', content)

    if replace:
      if hasattr(replace, "__call__"):
        replace = replace()

      # We reverse sort replacements by length to avoid cases when
      # replacements include each other and therefore order
      # of replacements affects the result.
      for substr in sorted(replace, key=len, reverse=True):
        content = content.replace(substr, replace[substr])

    return content

  @property
  def golden_file_class_name(self):
    """Returns a test class name to be used when working with a golden file."""

    test_class_name = self.__class__.__name__
    try:
      conn_type = getattr(self.__class__, "use_golden_files_of")
    except AttributeError:
      pass
    else:
      test_class_name = (
          test_class_name[:-len(self.__class__.connection_type)] + conn_type)

    return test_class_name

  def Check(self, method, args=None, replace=None):
    """Does the regression check."""
    router = api_auth_manager.API_AUTH_MGR.GetRouterForUser(self.token.username)
    mdata = router.GetAnnotatedMethods()[method]

    check = self.HandleCheck(
        mdata, args=args, replace=lambda s: self._Replace(s, replace=replace))

    check["test_class"] = self.golden_file_class_name
    check["api_method"] = method

    self.checks.append(check)

  @abc.abstractmethod
  def Run(self):
    """Sets up test envionment and does Check() calls."""
    pass

  def _testForRegression(self):  # pylint: disable=invalid-name
    """Checks whether there's a regression.

    This method is intentionally protected so that the test runner doesn't
    detect any tests in base regression classes. ApiRegressionTestMetaclass
    creates a public testForRegression method for generated regression
    classes.
    """
    self.maxDiff = 65536  # pylint: disable=invalid-name

    with open(self.output_file_name, "rb") as fd:
      prev_data = json.load(fd)

    checks = prev_data[self.__class__.handler.__name__]
    relevant_checks = []
    for check in checks:
      if check["test_class"] == self.golden_file_class_name:
        relevant_checks.append(check)

    self.Run()
    # Make sure that this test has generated some checks.
    self.assertTrue(self.checks)

    checks_str = json.dumps(
        self.checks, indent=2, sort_keys=True, separators=(",", ": "))
    prev_checks_str = json.dumps(
        relevant_checks, indent=2, sort_keys=True, separators=(",", ": "))

    self.assertMultiLineEqual(prev_checks_str, checks_str)


class ApiRegressionGoldenOutputGenerator(object):
  """Helper class used to generate regression tests golden files."""

  def __init__(self, connection_type):
    super(ApiRegressionGoldenOutputGenerator, self).__init__()

    self.connection_type = connection_type

  def _GroupRegressionTestsByHandler(self):
    result = {}
    for cls in ApiRegressionTest.classes.values():
      if issubclass(cls, ApiRegressionTest) and getattr(cls, "HandleCheck",
                                                        None):
        result.setdefault(cls.handler, []).append(cls)

    return result

  def Generate(self):
    """Prints generated 'golden' output to the stdout."""

    sample_data = {}

    tests = self._GroupRegressionTestsByHandler()
    for handler, test_classes in tests.items():
      for test_class in sorted(test_classes, key=lambda cls: cls.__name__):
        if getattr(test_class, "connection_type", "") != self.connection_type:
          continue

        # If a test is meant to use other tests data, there's nothing to
        # generate.
        if getattr(test_class, "use_golden_files_of", ""):
          continue

        test_class.setUpClass()
        try:
          test_instance = test_class()
          test_instance.setUp()
          try:
            test_instance.Run()
            sample_data.setdefault(handler.__name__,
                                   []).extend(test_instance.checks)
          finally:
            try:
              test_instance.tearDown()
            except Exception as e:  # pylint: disable=broad-except
              logging.exception(e)
        finally:
          try:
            test_class.tearDownClass()
          except Exception as e:  # pylint: disable=broad-except
            logging.exception(e)

    json_sample_data = json.dumps(
        sample_data, indent=2, sort_keys=True, separators=(",", ": "))
    print json_sample_data


def main(argv=None):
  if flags.FLAGS.generate:
    ApiRegressionGoldenOutputGenerator(flags.FLAGS.generate).Generate()
  else:
    test_lib.main(argv)
