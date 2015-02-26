#!/usr/bin/env python
"""Base test classes for API renderers tests."""



# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

import abc
import json
import os
import urlparse

from grr.gui import api_call_renderers

from grr.lib import flags
from grr.lib import test_lib
from grr.lib import utils


# To update regression data use the following command line:
# grr/gui/api_renderers_regression_data_generate.py > \
#   ./grr/gui/static/angular-components/docs/api-docs-examples.json
flags.DEFINE_string(
    "api_regression_data",
    "grr/gui/static/angular-components/docs/api-docs-examples.json",
    "Base path for GRR static files.")


class ApiCallRendererRegressionTest(test_lib.GRRBaseTest):
  """Base class for API renderers regression tests.

  Regression tests are supposed to implement a single abstract Run() method.

  In the Run() implementation they're supposed to set up necessary
  environment and do a number of Check() calls. Every Check() call fetches
  a particular URL and keeps the data. Then, if this test class is used
  as part of a test suite, generated data will be compared with ones in
  flags.FLAGS.api_regression_data file and exception will be raised if
  they're different.

  Alternatively, if this class is used in
  api_renderers_regression_data_generate.py, then generated data will be
  aggregated with data from other test classes and printed to the stdout.
  """

  __abstract = True  # pylint: disable=g-bad-name

  # Name of the ApiCallRenderer that's tested in this class.
  renderer = None

  def setUp(self):
    super(ApiCallRendererRegressionTest, self).setUp()
    self.checks = []

  def Check(self, method, url, replace=None):
    """Records output of a given url accessed with a given method.

    Args:
      method: HTTP method. Currently, only "GET" is supported.
      url: String repesenting an url.
      replace: Dictionary of key->value pairs. In the recorded JSON output
               every "key" string will be replaced with its "value"
               counterpart. This way we can properly handle dynamically
               generated values (like hunts IDs) in the regression data.
    Raises:
      ValueError: if unsupported method argument is passed. Currently only
                  "GET" is supported.
    """
    parsed_url = urlparse.urlparse(url)
    request = utils.DataObject(method=method,
                               scheme="http",
                               path=parsed_url.path,
                               environ={"SERVER_NAME": "foo.bar",
                                        "SERVER_PORT": 1234},
                               user="test")

    if method == "GET":
      request.GET = dict(urlparse.parse_qsl(parsed_url.query))
      request.META = {}

      http_response = api_call_renderers.RenderHttpResponse(request)
      content = http_response.content

      xssi_token = ")]}'\n"
      if content.startswith(xssi_token):
        content = content[len(xssi_token):]

      if replace:
        for substr, repl in replace.items():
          content = content.replace(substr, repl)
          url = url.replace(substr, repl)

      parsed_content = json.loads(content)
      self.checks.append(dict(method=method, url=url,
                              test_class=self.__class__.__name__,
                              response=parsed_content))
    else:
      raise ValueError("Unsupported method: %s." % method)

  @abc.abstractmethod
  def Run(self):
    """Sets up test envionment and does Check() calls."""
    pass

  def testForRegression(self):
    """Checks whether there's a regression."""
    self.maxDiff = 65536  # pylint: disable=invalid-name

    with open(os.path.join(flags.FLAGS.api_regression_data), "r") as fd:
      prev_data = json.load(fd)

    checks = prev_data[self.renderer]
    relevant_checks = []
    for check in checks:
      if check["test_class"] == self.__class__.__name__:
        relevant_checks.append(check)

    self.Run()
    # Make sure that this test has generated some checks.
    self.assertTrue(self.checks)

    checks_str = json.dumps(self.checks, indent=2, sort_keys=True,
                            separators=(",", ": "))
    prev_checks_str = json.dumps(relevant_checks, indent=2, sort_keys=True,
                                 separators=(",", ": "))
    self.assertMultiLineEqual(prev_checks_str, checks_str)
