#!/usr/bin/env python
# Copyright 2010 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for the client."""

import tempfile


from grr.client import conf
from grr.client import conf as flags
# Need to import client to add the flags.
from grr.client import actions

# Load all the standard actions.
# pylint: disable=W0611
from grr.client import client_actions
# pylint: enable=W0611
from grr.client import comms
from grr.lib import rdfvalue
from grr.lib import test_lib


FLAGS = flags.FLAGS


class MockAction(actions.ActionPlugin):
  in_rdfvalue = rdfvalue.LogMessage
  out_rdfvalue = rdfvalue.LogMessage

  def Run(self, message):
    self.SendReply(rdfvalue.EchoRequest(
        data="Received Message: %s. Data %s" % (message.data, "x" * 100)))


class RaiseAction(actions.ActionPlugin):
  """A mock action which raises an error."""
  in_rdfvalue = rdfvalue.LogMessage
  out_rdfvalue = rdfvalue.LogMessage

  def Run(self, unused_args):
    raise RuntimeError("I dont like.")


class TestedContext(comms.GRRClientWorker):
  """We test a simpler Context without crypto here."""

  def LoadCertificates(self):
    self.certs_loaded = True


class BasicContextTests(test_lib.GRRBaseTest):
  """Test the GRR contexts."""
  session_id = "1234"
  to_test_context = TestedContext

  def setUp(self):
    self.context = self.to_test_context()
    self.context.LoadCertificates()

  def testHandleMessage(self):
    """Test handling of a normal request with a response."""
    args = rdfvalue.LogMessage(data="hello")
    # Push a request on it
    message = rdfvalue.GRRMessage(
        name="MockAction",
        session_id=self.session_id,
        auth_state=rdfvalue.GRRMessage.Enum("AUTHENTICATED"),
        payload=args,
        request_id=1)

    self.context.HandleMessage(message)

    # Check the response - one data and one status

    message_list = self.context.Drain().job

    self.assertEqual(message_list[0].session_id, self.session_id)
    self.assertEqual(message_list[0].response_id, 1)
    self.assert_("hello" in message_list[0].args)
    self.assertEqual(message_list[1].response_id, 2)
    self.assertEqual(message_list[1].type, rdfvalue.GRRMessage.Enum("STATUS"))

  def testHandleError(self):
    """Test handling of a request which raises."""
    # Push a request on it
    message = rdfvalue.GRRMessage(
        name="RaiseAction",
        session_id=self.session_id,
        auth_state=rdfvalue.GRRMessage.Enum("AUTHENTICATED"),
        request_id=1)

    self.context.HandleMessage(message)

    # Check the response - one data and one status
    message_list = self.context.Drain().job
    self.assertEqual(message_list[0].session_id, self.session_id)
    self.assertEqual(message_list[0].response_id, 1)
    status = rdfvalue.GrrStatus(message_list[0].args)
    self.assert_("RuntimeError" in status.error_message)
    self.assertNotEqual(status.status, rdfvalue.GrrStatus.Enum("OK"))

  def testUnauthenticated(self):
    """What happens if an unauthenticated message is sent to the client?

    RuntimeError needs to be issued, and the client needs to send a
    GrrStatus message with the traceback in it.
    """
    # Push a request on it
    message = rdfvalue.GRRMessage(
        name="MockAction",
        session_id=self.session_id,
        auth_state=rdfvalue.GRRMessage.Enum("UNAUTHENTICATED"),
        request_id=1)

    self.context.HandleMessage(message)
    # We expect to receive an GrrStatus to indicate an exception was
    # raised:
    # Check the response - one data and one status
    message_list = self.context.Drain().job
    self.assertEqual(len(message_list), 1)
    self.assertEqual(message_list[0].session_id, self.session_id)
    self.assertEqual(message_list[0].response_id, 1)
    status = rdfvalue.GrrStatus(message_list[0].args)
    self.assert_("not Authenticated" in status.error_message)
    self.assert_("RuntimeError" in status.error_message)
    self.assertNotEqual(status.status, rdfvalue.GrrStatus.Enum("OK"))

  def testPriorities(self):
    for i in range(10):
      message = rdfvalue.GRRMessage(
          name="MockAction",
          session_id=self.session_id + str(i),
          auth_state=rdfvalue.GRRMessage.Enum("UNAUTHENTICATED"),
          request_id=1,
          priority=i%3)
      self.context.HandleMessage(message)
    message_list = self.context.Drain(max_size=1000000).job
    self.assertEqual(len(message_list), 10)
    self.assertEqual([m.priority for m in message_list],
                     [2, 2, 2, 1, 1, 1, 0, 0, 0, 0])

  def testSizeQueue(self):

    queue = comms.SizeQueue(maxsize=10000000)

    for _ in range(10):
      queue.Put("A", 1)
      queue.Put("B", 1)
      queue.Put("C", 2)

    result = []
    for item in queue.Get():
      result.append(item)
    self.assertEqual(result, ["C"] * 10 + ["A", "B"] * 10)

    # Tests a partial Get().
    for _ in range(7):
      queue.Put("A", 1)
      queue.Put("B", 1)
      queue.Put("C", 2)

    result = []
    for item in queue.Get():
      result.append(item)
      if len(result) == 5:
        break

    self.assertEqual(result, ["C"] * 5)

    for _ in range(3):
      queue.Put("A", 1)
      queue.Put("B", 1)
      queue.Put("C", 2)

    for item in queue.Get():
      result.append(item)
    self.assertEqual(result, ["C"] * 10 + ["A", "B"] * 10)


def main(argv):
  _, FLAGS.nanny_logfile = tempfile.mkstemp()
  test_lib.main(argv)

if __name__ == "__main__":
  conf.StartMain(main)
