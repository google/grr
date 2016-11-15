#!/usr/bin/env python
"""Base test classes for API handlers tests."""



import abc
import json
import os
import re
import socket
import urlparse

from google.protobuf import json_format

from grr import gui
from grr.gui import api_auth_manager
from grr.gui import api_call_router_without_checks
from grr.gui import api_value_renderers
from grr.gui import http_api
from grr.lib import test_lib
from grr.lib import utils

DOCUMENT_ROOT = os.path.join(os.path.dirname(gui.__file__), "static")


class NullAPIAuthorizationManager(object):
  """Authorization manager that allows everything. Used for testing only."""

  def GetRouterForUser(self, unused_username):
    return api_call_router_without_checks.ApiCallRouterWithoutChecks()


class ApiCallHandlerTest(test_lib.GRRBaseTest):

  def setUp(self):
    super(ApiCallHandlerTest, self).setUp()
    # The user we use for API tests.
    self.token.username = "api_test_user"


class ApiCallHandlerRegressionTest(test_lib.GRRBaseTest):
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

  __abstract = True  # pylint: disable=g-bad-name

  # Name of the ApiCallRouter's method that's tested in this class.
  api_method = None
  # Handler class that's used to handle the requests.
  handler = None

  # If True, API v2, won't be tested. Needed for cases when API JSON output
  # usable: i.e. contains dynamic fields encoded as bytes without proper
  # type information.
  skip_v2_tests = False

  def setUp(self):
    super(ApiCallHandlerRegressionTest, self).setUp()
    api_auth_manager.APIACLInit.InitApiAuthManager()

    if not self.__class__.api_method:
      raise ValueError("%s.api_method has to be set." % self.__class__.__name__)

    if not self.__class__.handler:
      raise ValueError("%s.handler has to be set." % self.__class__.__name__)

    self.checks = []

    self.syscalls_stubber = utils.MultiStubber(
        (socket, "gethostname", lambda: "test.host"),
        (os, "getpid", lambda: 42))
    self.syscalls_stubber.Start()

    self.use_api_v2 = False

    self.token.username = "api_test_user"

  def tearDown(self):
    super(ApiCallHandlerRegressionTest, self).tearDown()
    self.syscalls_stubber.Stop()

  def NoAuthorizationChecks(self):
    return utils.Stubber(api_auth_manager, "API_AUTH_MGR",
                         NullAPIAuthorizationManager())

  def Check(self, method, url, payload=None, replace=None):
    """Records output of a given url accessed with a given method.

    Args:
      method: HTTP method. May be "GET" or "POST".
      url: String repesenting an url.
      payload: JSON-able payload that will be sent when "POST" method is used.
      replace: Dictionary of key->value pairs. In the recorded JSON output
               every "key" string will be replaced with its "value"
               counterpart. This way we can properly handle dynamically
               generated values (like hunts IDs) in the regression data.
    Raises:
      ValueError: if unsupported method argument is passed. Currently only
                  "GET", "POST", "DELETE" and "PATCH" are supported.
      RuntimeError: if request was handled by an unexpected API method (
                  every test is annotated with an "api_method" attribute
                  that points to the expected API method).
    """
    if self.use_api_v2:
      url = url.replace("/api/", "/api/v2/")

    parsed_url = urlparse.urlparse(url)
    request = utils.DataObject(
        method=method,
        scheme="http",
        path=parsed_url.path,
        environ={"SERVER_NAME": "foo.bar",
                 "SERVER_PORT": 1234},
        user=self.token.username,
        body="")
    request.META = {"CONTENT_TYPE": "application/json"}

    if method == "GET":
      request.GET = dict(urlparse.parse_qsl(parsed_url.query))
    elif method in ["POST", "DELETE", "PATCH"]:
      # NOTE: this is a temporary trick. Payloads in regression tests
      # are using the API v1 (non-proto3) format. Here we're reparsing
      # them and serializing as proto3 JSON.
      # TODO(user): Make regression tests payload format-agnostic.
      # I.e. use protobuf and API client library to send requests.
      if self.use_api_v2 and payload:
        router_matcher = http_api.RouterMatcher()
        _, metadata, _ = router_matcher.MatchRouter(request)

        rdf_args = metadata.args_type()
        rdf_args.FromDict(payload)
        proto_args = metadata.args_type.protobuf()
        proto_args.ParseFromString(rdf_args.SerializeToString())

        request.body = json_format.MessageToJson(proto_args)
        payload = json.loads(request.body)
      else:
        request.body = json.dumps(payload or "")
    else:
      raise ValueError("Unsupported method: %s." % method)

    with self.NoAuthorizationChecks():
      http_response = http_api.RenderHttpResponse(request)

    api_method = http_response["X-API-Method"]
    if api_method != self.__class__.api_method:
      raise RuntimeError("Request was handled by an unexpected method. "
                         "Expected %s, got %s." % (self.__class__.api_method,
                                                   api_method))

    if hasattr(http_response, "streaming_content"):
      # We don't know the nature of response content, but we force it to be
      # unicode. It's a strategy that's good enough for testing purposes.
      content = utils.SmartUnicode("".join(http_response.streaming_content))
    else:
      content = http_response.content

    xssi_token = ")]}'\n"
    if content.startswith(xssi_token):
      content = content[len(xssi_token):]

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
        repl = replace[substr]

        if hasattr(substr, "sub"):  # regex
          content = substr.sub(repl, content)
          url = substr.sub(repl, url)
        else:
          content = content.replace(substr, repl)
          url = url.replace(substr, repl)

    # We treat streaming content purely as strings and don't expect it to
    # contain JSON data.
    if hasattr(http_response, "streaming_content"):
      parsed_content = content
    else:
      parsed_content = json.loads(content)

    check_result = dict(
        api_method=api_method,
        method=method,
        url=url,
        test_class=self.__class__.__name__,
        response=parsed_content)

    if payload:
      check_result["request_payload"] = payload

    # Type stripping only makes sense for version 1 of the API.
    if not self.use_api_v2:
      stripped_content = api_value_renderers.StripTypeInfo(parsed_content)
      if parsed_content != stripped_content:
        check_result["type_stripped_response"] = stripped_content

    self.checks.append(check_result)

  @abc.abstractmethod
  def Run(self):
    """Sets up test envionment and does Check() calls."""
    pass

  def _testForRegression(self, fname=None, use_api_v2=False):
    """Checks whether there's a regression."""
    self.maxDiff = 65536  # pylint: disable=invalid-name

    with open(fname, "rb") as fd:
      prev_data = json.load(fd)

    checks = prev_data[self.__class__.handler.__name__]
    relevant_checks = []
    for check in checks:
      if check["test_class"] == self.__class__.__name__:
        relevant_checks.append(check)

    self.use_api_v2 = use_api_v2
    self.Run()
    # Make sure that this test has generated some checks.
    self.assertTrue(self.checks)

    checks_str = json.dumps(
        self.checks, indent=2, sort_keys=True, separators=(",", ": "))
    prev_checks_str = json.dumps(
        relevant_checks, indent=2, sort_keys=True, separators=(",", ": "))

    self.assertMultiLineEqual(prev_checks_str, checks_str)

  def testForRegression(self):
    self._testForRegression(
        os.path.join(DOCUMENT_ROOT,
                     "angular-components/docs/api-docs-examples.json"),
        use_api_v2=False)

  def testForRegressionApiV2(self):
    if not self.__class__.skip_v2_tests:
      self._testForRegression(
          os.path.join(DOCUMENT_ROOT,
                       "angular-components/docs/api-v2-docs-examples.json"),
          use_api_v2=True)
