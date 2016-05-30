#!/usr/bin/env python
"""Test for client comms."""


import StringIO
import time
import urllib2


from grr.client import comms
from grr.lib import flags
from grr.lib import test_lib
from grr.lib import utils


def _make_http_exception(code=500, msg="Error"):
  """A helper for creating a HTTPError exception."""
  return urllib2.HTTPError(url="", code=code, msg=msg, hdrs=[], fp=None)


class URLLibInstrumentor(object):
  """Instrument the urllib2 library."""

  def __init__(self):
    self.time = 0
    self.current_opener = None
    # Record the actions in order.
    self.actions = []

    # These are the responses we will do.
    self.responses = []

  def install_opener(self, opener):
    self.current_opener = opener

  def _extract_proxy(self, opener):
    """Deduce the proxy location for the urllib opener."""
    for handler in opener.handlers:
      if isinstance(handler, urllib2.ProxyHandler):
        return handler.proxies.get("http")

  def _extract_url(self, request):
    if isinstance(request, basestring):
      return request
    return request.get_full_url()

  def urlopen(self, request, **_):
    # We only care about how urllib2 will try to connect - the proxy and the
    # URL.
    self.actions.append([
        self.time, self._extract_url(request), self._extract_proxy(
            self.current_opener)
    ])
    if self.responses:
      result = self.responses.pop(0)
    else:
      result = _make_http_exception(404, "404 Not found")

    if isinstance(result, IOError):
      raise result

    return StringIO.StringIO(result)

  def sleep(self, timeout):
    self.time += timeout

  def instrument(self):
    """Install the mocks required.

    Returns:
       A context manager that when exits restores the mocks.
    """
    self.actions = []
    return utils.MultiStubber(
        (urllib2, "install_opener", self.install_opener),
        (urllib2, "urlopen", self.urlopen), (time, "sleep", self.sleep))


class URLFilter(URLLibInstrumentor):
  """Emulate only a single server url that works."""

  def urlopen(self, request, **kwargs):
    url = self._extract_url(request)
    try:
      return super(URLFilter, self).urlopen(request, **kwargs)
    except IOError:
      # If request is from server2 - return a valid response. Assume, server2 is
      # reachable from all proxies.
      if "server2" in url:
        return StringIO.StringIO("Good")

      raise


class MockHTTPManager(comms.HTTPManager):

  def _GetBaseURLs(self):
    return ["http://server1/", "http://server2/", "http://server3/"]

  def _GetProxies(self):
    """Do not test the proxy gathering logic itself."""
    return ["proxy1", "proxy2", "proxy3"]


class HTTPManagerTest(test_lib.GRRBaseTest):
  """Tests the HTTP Manager."""

  def MakeRequest(self, instrumentor, manager, path, verify_cb=lambda x: True):
    with utils.MultiStubber(
        (urllib2, "install_opener", instrumentor.install_opener),
        (urllib2, "urlopen", instrumentor.urlopen),
        (time, "sleep", instrumentor.sleep)):
      return manager.OpenServerEndpoint(path, verify_cb=verify_cb)

  def testBaseURLConcatenation(self):
    instrumentor = URLLibInstrumentor()
    with instrumentor.instrument():
      manager = MockHTTPManager()
      manager.OpenServerEndpoint("/control")

    # Make sure that the URL is concatenated properly (no //).
    self.assertEqual(instrumentor.actions[0][1], "http://server1/control")

  def testProxySearch(self):
    """Check that all proxies will be searched in order."""
    # Do not specify a response - all requests will return a 404 message.
    instrumentor = URLLibInstrumentor()
    with instrumentor.instrument():
      manager = MockHTTPManager()
      result = manager.OpenURL("http://www.google.com/")

    # Three requests are made.
    self.assertEqual(len(instrumentor.actions), 3)
    self.assertEqual([x[2] for x in instrumentor.actions], manager.proxies)

    # Result is an error since no requests succeeded.
    self.assertEqual(result.code, 404)

  def testVerifyCB(self):
    """Check that we can handle captive portals via the verify CB.

    Captive portals do not cause an exception but return bad data.
    """

    def verify_cb(http_object):
      return http_object.data == "Good"

    instrumentor = URLLibInstrumentor()

    # First request is an exception, next is bad and the last is good.
    instrumentor.responses = [_make_http_exception(code="404"), "Bad", "Good"]
    with instrumentor.instrument():
      manager = MockHTTPManager()
      result = manager.OpenURL("http://www.google.com/", verify_cb=verify_cb)

    self.assertEqual(result.data, "Good")

  def testURLSwitching(self):
    """Ensure that the manager switches URLs to one that works."""
    # Only server2 works and returns Good response.
    instrumentor = URLFilter()
    with instrumentor.instrument():
      manager = MockHTTPManager()
      result = manager.OpenServerEndpoint("control")

    # The result is correct.
    self.assertEqual(result.data, "Good")
    self.assertEqual(instrumentor.actions,
                     # First search for server1 through all proxies.
                     [[0, "http://server1/control", "proxy1"],
                      [0, "http://server1/control", "proxy2"],
                      [0, "http://server1/control", "proxy3"],

                      # Now search for server2 through all proxies.
                      [0, "http://server2/control", "proxy1"]])

  def testTemporaryFailure(self):
    """If the front end gives an intermittent 500, we must back off."""
    instrumentor = URLLibInstrumentor()
    # First response good, then a 500 error, then another good response.
    instrumentor.responses = ["Good", _make_http_exception(code=500),
                              "Also Good"]

    manager = MockHTTPManager()
    with instrumentor.instrument():
      # First request - should be fine.
      result = manager.OpenServerEndpoint("control")

    self.assertEqual(result.data, "Good")

    with instrumentor.instrument():
      # Second request - should appear fine.
      result = manager.OpenServerEndpoint("control")

    self.assertEqual(result.data, "Also Good")

    # But we actually made two requests.
    self.assertEqual(len(instrumentor.actions), 2)

    # And we waited 60 seconds to make the second one.
    self.assertEqual(instrumentor.actions[0][0], 0)
    self.assertEqual(instrumentor.actions[1][0], manager.error_poll_min)

    # Make sure that the manager cleared its consecutive_connection_errors.
    self.assertEqual(manager.consecutive_connection_errors, 0)

  def test406Errors(self):
    """Ensure that 406 enrollment requests are propagated immediately.

    Enrollment responses (406) are sent by the server when the client is not
    suitable enrolled. The http manager should treat those as correct responses
    and stop searching for proxy/url combinations in order to allow the client
    to commence enrollment workflow.
    """
    instrumentor = URLLibInstrumentor()
    instrumentor.responses = [_make_http_exception(code=406)]

    manager = MockHTTPManager()
    with instrumentor.instrument():
      # First request - should raise a 406 error.
      result = manager.OpenServerEndpoint("control")

    self.assertEqual(result.code, 406)

    # We should not search for proxy/url combinations.
    self.assertEqual(len(instrumentor.actions), 1)

    # A 406 message is not considered an error.
    self.assertEqual(manager.consecutive_connection_errors, 0)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
