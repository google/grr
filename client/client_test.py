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

"""Test for client."""



from grr.client import conf
from grr.client import conf as flags
# Need to import client to add the flags.
from grr.client import actions

# Load all the standard actions
from grr.client import client_actions
from grr.client import comms
from grr.lib import test_lib
from grr.proto import jobs_pb2


FLAGS = flags.FLAGS


class MockAction(actions.ActionPlugin):
  in_protobuf = jobs_pb2.PrintStr
  out_protobuf = jobs_pb2.PrintStr

  def Run(self, message):
    self.SendReply(jobs_pb2.PrintStr(
        data="Received Message: %s. Data %s" % (message.data, "x" * 100)))


class RaiseAction(actions.ActionPlugin):
  """A mock action which raises an error."""
  in_protobuf = jobs_pb2.PrintStr
  out_protobuf = jobs_pb2.PrintStr

  def Run(self, message):
    raise RuntimeError("I dont like %s" % message.data)


class TestedContext(comms.GRRContext):
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
    # Push a request on it
    message = jobs_pb2.GrrMessage(
        name="MockAction",
        session_id=self.session_id,
        auth_state=jobs_pb2.GrrMessage.AUTHENTICATED,
        args=jobs_pb2.PrintStr(data="hello").SerializeToString(),
        request_id=1)

    self.context.HandleMessage(message)

    # Check the response - one data and one status

    message_list = self.context.Drain().job
    self.assertEqual(message_list[0].session_id, self.session_id)
    self.assertEqual(message_list[0].response_id, 1)
    self.assert_("hello" in message_list[0].args)
    self.assertEqual(message_list[1].response_id, 2)
    self.assertEqual(message_list[1].type, jobs_pb2.GrrMessage.STATUS)

  def testHandleError(self):
    """Test handling of a request which raises."""
    # Push a request on it
    message = jobs_pb2.GrrMessage(
        name="RaiseAction",
        session_id=self.session_id,
        auth_state=jobs_pb2.GrrMessage.AUTHENTICATED,
        request_id=1)

    self.context.HandleMessage(message)

    # Check the response - one data and one status
    message_list = self.context.Drain().job
    self.assertEqual(message_list[0].session_id, self.session_id)
    self.assertEqual(message_list[0].response_id, 1)
    status = jobs_pb2.GrrStatus()
    status.ParseFromString(message_list[0].args)
    self.assert_("RuntimeError" in status.error_message)
    self.assertNotEqual(status.status, jobs_pb2.GrrStatus.OK)

  def testUnauthenticated(self):
    """What happens if an unauthenticated message is sent to the client?

    RuntimeError needs to be issued, and the client needs to send a
    GrrStatus message with the traceback in it.
    """
    # Push a request on it
    message = jobs_pb2.GrrMessage(
        name="MockAction",
        session_id=self.session_id,
        auth_state=jobs_pb2.GrrMessage.UNAUTHENTICATED,
        request_id=1)

    self.context.HandleMessage(message)
    # We expect to receive an GrrStatus to indicate an exception was
    # raised:
    # Check the response - one data and one status
    message_list = self.context.Drain().job
    self.assertEqual(len(message_list), 1)
    self.assertEqual(message_list[0].session_id, self.session_id)
    self.assertEqual(message_list[0].response_id, 1)
    status = jobs_pb2.GrrStatus()
    status.ParseFromString(message_list[0].args)
    self.assert_("not Authenticated" in status.error_message)
    self.assert_("RuntimeError" in status.error_message)
    self.assertNotEqual(status.status, jobs_pb2.GrrStatus.OK)


class TestedProcessSeparatedContext(comms.ProcessSeparatedContext):
  def LoadCertificates(self):
    pass


class TestProcessSeparatedContext(BasicContextTests):
  """Test the process separated context."""
  to_test_context = TestedProcessSeparatedContext

  def setUp(self):
    comms.SlaveContext.LoadCertificates = lambda self: None
    BasicContextTests.setUp(self)

  def tearDown(self):
    self.context.Terminate()

  def testSegFault(self):
    """What happens if our slave crashes?"""
    # Push a request on it
    message = jobs_pb2.GrrMessage(
        name="KillSlave",
        session_id=self.session_id,
        auth_state=jobs_pb2.GrrMessage.AUTHENTICATED,
        request_id=1)

    self.context.HandleMessage(message)

    # We expect to receive an GrrStatus to indicate an exception was
    # raised:
    # Check the response - one data and one status
    message_list = self.context.Drain().job
    self.assertEqual(len(message_list), 1)
    self.assertEqual(message_list[0].session_id, self.session_id)
    status = jobs_pb2.GrrStatus()
    status.ParseFromString(message_list[0].args)
    self.assert_("Slave crashed" in status.error_message)
    self.assertNotEqual(status.status, jobs_pb2.GrrStatus.OK)


def main(argv):
  test_lib.main(argv)

if __name__ == "__main__":
  conf.StartMain(main)
