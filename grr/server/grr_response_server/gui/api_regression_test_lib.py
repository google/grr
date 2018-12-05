#!/usr/bin/env python
"""Base test classes for API handlers tests."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import abc
import json
import logging
import os
import re
import socket
import sys


from future.utils import iteritems
from future.utils import itervalues
from future.utils import with_metaclass
import psutil
import pytest

from grr_response_core.lib import flags
from grr_response_core.lib import registry
from grr_response_core.lib import utils
from grr_response_core.lib.util import compatibility
from grr_response_server import data_store
from grr_response_server import flow
from grr_response_server.gui import api_auth_manager
# This import guarantees that all API-related RDF types will get imported
# (as they're all references by api_call_router).
# pylint: disable=unused-import
from grr_response_server.gui import api_call_router
# pylint: enable=unused-import
from grr_response_server.gui import api_regression_http
from grr_response_server.gui import webauth
from grr.test_lib import test_lib
from grr.test_lib import testing_startup

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
    for mixin in itervalues(cls.connection_mixins):
      if issubclass(cls, mixin):
        has_mixin = True
        break

    # ApiRegressionTest is a base class, so it doesn't make sense to generate
    # _http_v1/_http_v2 classes for it.
    # Generating classes from already generated classes would lead to infinite
    # recursion. Skipping the generated ones.
    if name == "ApiRegressionTest" or has_mixin:
      return

    for mixin in itervalues(ApiRegressionTestMetaclass.connection_mixins):
      if (mixin.skip_legacy_dynamic_proto_tests and
          getattr(cls, "uses_legacy_dynamic_protos", False)):
        continue

      # Do not generate combinations where the mixin demands relational db reads
      # but the test is aff4 only.
      if (getattr(cls, "aff4_only_test", False) and
          getattr(mixin, "read_from_relational_db", False)):
        continue

      # Some tests don't work yet with relational flows enabled.
      if (getattr(cls, "aff4_flows_only_test", False) and
          getattr(mixin, "relational_db_flows", False)):
        continue

      cls_name = "%s_%s" % (name, mixin.connection_type)
      test_cls = compatibility.MakeType(
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
ApiRegressionTestMetaclass.RegisterConnectionMixin(
    api_regression_http.HttpApiV2RelationalFlowsRegressionTestMixin)


@pytest.mark.small
@pytest.mark.api_regression
class ApiRegressionTest(
    with_metaclass(ApiRegressionTestMetaclass, test_lib.GRRBaseTest)):
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

  def Check(self, method, args=None, replace=None, api_post_process_fn=None):
    """Does the regression check.

    Args:
      method: Name of the API method to call.
      args: RDF protobuf containing arguments for the API method.
      replace: Can be either: 1) A dict containing strings which, if they occur
        in the raw API response, will be replaced with the strings they map to.
        2) A zero-argument function that returns a replacements dict like the
        one described in 1).
      api_post_process_fn: A function which, if provided, will be called with
        the results of parsing the API response, allowing modification of the
        results before they are compared with golden datasets.
    """
    router = api_auth_manager.API_AUTH_MGR.GetRouterForUser(self.token.username)
    mdata = router.GetAnnotatedMethods()[method]

    check = self.HandleCheck(
        mdata, args=args, replace=lambda s: self._Replace(s, replace=replace))

    check["test_class"] = self.golden_file_class_name
    check["api_method"] = method

    if api_post_process_fn is not None:
      api_post_process_fn(check)

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
    for cls in itervalues(ApiRegressionTest.classes):
      if issubclass(cls, ApiRegressionTest) and getattr(cls, "HandleCheck",
                                                        None):
        result.setdefault(cls.handler, []).append(cls)

    return result

  def Generate(self):
    """Prints generated 'golden' output to the stdout."""

    sample_data = {}

    tests = self._GroupRegressionTestsByHandler()
    for handler, test_classes in iteritems(tests):
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
    print(json_sample_data)


def GetFlowTestReplaceDict(client_id=None,
                           flow_id=None,
                           replacement_flow_id="W:ABCDEF"):
  """Creates and returns a replacement dict for flow regression tests."""
  replace = {}
  if data_store.RelationalDBFlowsEnabled():
    if client_id and flow_id:
      # New style session ids need to be converted.
      old_style_id = "%s/%s" % (client_id, flow_id)
      new_style_id = "%s/flows/%s" % (client_id, replacement_flow_id)
      replace[old_style_id] = new_style_id

  if flow_id:
    replace[flow_id] = replacement_flow_id

  return replace


def StartFlow(client_id, flow_cls, flow_args=None, token=None):
  """A test helper function to start a flow."""
  # TODO(amoser): Once AFF4 is removed, this method should be moved to
  # flow_test_lib.
  if data_store.RelationalDBFlowsEnabled():
    return flow.StartFlow(
        creator=token and token.username,
        flow_cls=flow_cls,
        flow_args=flow_args,
        client_id=client_id)
  else:
    return flow.StartAFF4Flow(
        flow_name=compatibility.GetName(flow_cls),
        notify_to_user=True,
        client_id=client_id,
        args=flow_args,
        token=token).Basename()


def main(argv=None):
  testing_startup.TestInit()
  if flags.FLAGS.generate:
    testing_startup.TestInit()
    ApiRegressionGoldenOutputGenerator(flags.FLAGS.generate).Generate()
  else:
    test_lib.main(argv)
