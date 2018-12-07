#!/usr/bin/env python
"""Test for client comms."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import time


from builtins import range  # pylint: disable=redefined-builtin
import mock
import queue
import requests

from grr_response_client import comms
from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.util import compatibility
from grr.test_lib import test_lib


def _make_http_response(code=200):
  """A helper for creating HTTP responses."""
  response = requests.Response()
  response.status_code = code
  return response


def _make_404():
  return _make_http_response(404)


def _make_200(content):
  response = _make_http_response(200)
  response._content = content
  return response


class RequestsInstrumentor(object):
  """Instrument the `requests` library."""

  def __init__(self):
    self.time = 0
    self.current_opener = None
    # Record the actions in order.
    self.actions = []

    # These are the responses we will do.
    self.responses = []

  def request(self, **request_options):
    self.actions.append([self.time, request_options])
    if self.responses:
      response = self.responses.pop(0)
      if isinstance(response, IOError):
        raise response
      return response
    else:
      return _make_404()

  def sleep(self, timeout):
    self.time += timeout

  def instrument(self):
    """Install the mocks required.

    Returns:
       A context manager that when exits restores the mocks.
    """
    self.actions = []
    return utils.MultiStubber((requests, "request", self.request),
                              (time, "sleep", self.sleep))


class URLFilter(RequestsInstrumentor):
  """Emulate only a single server url that works."""

  def request(self, url=None, **kwargs):
    # If request is from server2 - return a valid response. Assume, server2 is
    # reachable from all proxies.
    response = super(URLFilter, self).request(url=url, **kwargs)
    if "server2" in url:
      return _make_200("Good")
    return response


class MockHTTPManager(comms.HTTPManager):

  def _GetBaseURLs(self):
    return ["http://server1/", "http://server2/", "http://server3/"]

  def _GetProxies(self):
    """Do not test the proxy gathering logic itself."""
    return ["proxy1", "proxy2", "proxy3"]


class HTTPManagerTest(test_lib.GRRBaseTest):
  """Tests the HTTP Manager."""

  def MakeRequest(self, instrumentor, manager, path, verify_cb=lambda x: True):
    with utils.MultiStubber((requests, "request", instrumentor.request),
                            (time, "sleep", instrumentor.sleep)):
      return manager.OpenServerEndpoint(path, verify_cb=verify_cb)

  def testBaseURLConcatenation(self):
    instrumentor = RequestsInstrumentor()
    with instrumentor.instrument():
      manager = MockHTTPManager()
      manager.OpenServerEndpoint("/control")

    # Make sure that the URL is concatenated properly (no //).
    self.assertEqual(instrumentor.actions[0][1]["url"],
                     "http://server1/control")

  def testProxySearch(self):
    """Check that all proxies will be searched in order."""
    # Do not specify a response - all requests will return a 404 message.
    instrumentor = RequestsInstrumentor()
    with instrumentor.instrument():
      manager = MockHTTPManager()
      result = manager.OpenURL("http://www.google.com/")

    # Three requests are made.
    proxies = [x[1]["proxies"]["https"] for x in instrumentor.actions]
    self.assertEqual(proxies, manager.proxies)

    # Result is an error since no requests succeeded.
    self.assertEqual(result.code, 404)

  def testVerifyCB(self):
    """Check that we can handle captive portals via the verify CB.

    Captive portals do not cause an exception but return bad data.
    """

    def verify_cb(http_object):
      return http_object.data == "Good"

    instrumentor = RequestsInstrumentor()

    # First request is an exception, next is bad and the last is good.
    instrumentor.responses = [_make_404(), _make_200("Bad"), _make_200("Good")]
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

    queries = [
        (x[1]["url"], x[1]["proxies"]["http"]) for x in instrumentor.actions
    ]

    self.assertEqual(
        queries,
        # First search for server1 through all proxies.
        [
            ("http://server1/control", "proxy1"),
            ("http://server1/control", "proxy2"),
            ("http://server1/control", "proxy3"),

            # Now search for server2 through all proxies.
            ("http://server2/control", "proxy1")
        ])

  def testTemporaryFailure(self):
    """If the front end gives an intermittent 500, we must back off."""
    instrumentor = RequestsInstrumentor()
    # First response good, then a 500 error, then another good response.
    instrumentor.responses = [
        _make_200("Good"),
        _make_http_response(code=500),
        _make_200("Also Good")
    ]

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
    self.assertLen(instrumentor.actions, 2)

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
    instrumentor = RequestsInstrumentor()
    instrumentor.responses = [_make_http_response(code=406)]

    manager = MockHTTPManager()
    with instrumentor.instrument():
      # First request - should raise a 406 error.
      result = manager.OpenServerEndpoint("control")

    self.assertEqual(result.code, 406)

    # We should not search for proxy/url combinations.
    self.assertLen(instrumentor.actions, 1)

    # A 406 message is not considered an error.
    self.assertEqual(manager.consecutive_connection_errors, 0)

  def testConnectionErrorRecovery(self):
    instrumentor = RequestsInstrumentor()

    # When we can't connect at all (server not listening), we get a
    # requests.exceptions.ConnectionError but the response object is None.
    err_response = requests.ConnectionError("Error", response=None)
    instrumentor.responses = [err_response, _make_200("Good")]
    with instrumentor.instrument():
      manager = MockHTTPManager()
      result = manager.OpenServerEndpoint("control")

    self.assertEqual(result.data, "Good")


class SizeLimitedQueueTest(test_lib.GRRBaseTest):

  def testSizeLimitedQueue(self):

    limited_queue = comms.SizeLimitedQueue(
        maxsize=10000000, heart_beat_cb=lambda: None)

    msg_a = rdf_flows.GrrMessage(name="A")
    msg_b = rdf_flows.GrrMessage(name="B")
    msg_c = rdf_flows.GrrMessage(name="C")

    for _ in range(10):
      limited_queue.Put(msg_a)
      limited_queue.Put(msg_b)
      limited_queue.Put(msg_c)

    result = limited_queue.GetMessages()
    self.assertCountEqual(list(result.job), [msg_c] * 10 + [msg_a, msg_b] * 10)

    # Tests a partial Get().
    for _ in range(7):
      limited_queue.Put(msg_a)
      limited_queue.Put(msg_b)
      limited_queue.Put(msg_c)

    result = limited_queue.GetMessages(
        soft_size_limit=len(msg_a.SerializeToString()) * 5 - 1)

    self.assertLen(list(result.job), 5)

    for _ in range(3):
      limited_queue.Put(msg_a)
      limited_queue.Put(msg_b)
      limited_queue.Put(msg_c)

    # Append the remaining messages to the same result.
    result.job.Extend(limited_queue.GetMessages().job)
    self.assertCountEqual(list(result.job), [msg_c] * 10 + [msg_a, msg_b] * 10)

  def testSizeLimitedQueueOverflow(self):

    msg_a = rdf_flows.GrrMessage(name="A")
    msg_b = rdf_flows.GrrMessage(name="B")
    msg_c = rdf_flows.GrrMessage(name="C")
    msg_d = rdf_flows.GrrMessage(name="D")

    limited_queue = comms.SizeLimitedQueue(
        maxsize=3 * len(msg_a.SerializeToString()), heart_beat_cb=lambda: None)

    limited_queue.Put(msg_a, block=False)
    limited_queue.Put(msg_b, block=False)
    limited_queue.Put(msg_c, block=False)
    with self.assertRaises(queue.Full):
      limited_queue.Put(msg_d, block=False)

  def testSizeLimitedQueueHeartbeat(self):

    msg_a = rdf_flows.GrrMessage(name="A")
    msg_b = rdf_flows.GrrMessage(name="B")
    msg_c = rdf_flows.GrrMessage(name="C")
    msg_d = rdf_flows.GrrMessage(name="D")

    heartbeat = mock.Mock()

    limited_queue = comms.SizeLimitedQueue(
        maxsize=3 * len(msg_a.SerializeToString()), heart_beat_cb=heartbeat)

    limited_queue.Put(msg_a)
    limited_queue.Put(msg_b)
    limited_queue.Put(msg_c)
    with self.assertRaises(queue.Full):
      limited_queue.Put(msg_d, timeout=1)

    self.assertTrue(heartbeat.called)


class GRRClientWorkerTest(test_lib.GRRBaseTest):
  """Tests the GRRClientWorker class."""

  def setUp(self):
    super(GRRClientWorkerTest, self).setUp()
    # GRRClientWorker starts a stats collector thread that will send replies
    # shortly after starting up. Those replies interfere with the test below so
    # we disable the ClientStatsCollector thread here.
    with utils.Stubber(comms.GRRClientWorker,
                       "StartStatsCollector", lambda self: None):
      self.client_worker = comms.GRRClientWorker(
          internal_nanny_monitoring=False)

  def testSendReplyHandlesFalseyPrimitivesCorrectly(self):
    self.client_worker.SendReply(rdfvalue.RDFDatetime(0))
    messages = self.client_worker.Drain().job

    self.assertLen(messages, 1)
    self.assertEqual(messages[0].args_rdf_name,
                     compatibility.GetName(rdfvalue.RDFDatetime))
    self.assertIsInstance(messages[0].payload, rdfvalue.RDFDatetime)
    self.assertEqual(messages[0].payload, rdfvalue.RDFDatetime(0))


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
