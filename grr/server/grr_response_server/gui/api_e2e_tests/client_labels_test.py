#!/usr/bin/env python
"""Tests for API client and labels-related API calls."""


from grr.lib import flags
from grr_response_proto import objects_pb2
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server.aff4_objects import aff4_grr
from grr.server.grr_response_server.gui import api_e2e_test_lib
from grr.test_lib import test_lib


class ApiClientLibLabelsTest(api_e2e_test_lib.ApiE2ETest):
  """Tests VFS operations part of GRR Python API client library."""

  def setUp(self):
    super(ApiClientLibLabelsTest, self).setUp()
    self.client_urn = self.SetupClient(0)

  def testAddLabels(self):
    client_ref = self.api.Client(client_id=self.client_urn.Basename())
    self.assertEqual(list(client_ref.Get().data.labels), [])

    with test_lib.FakeTime(42):
      client_ref.AddLabels(["foo", "bar"])

    self.assertEqual(
        sorted(client_ref.Get().data.labels, key=lambda l: l.name), [
            objects_pb2.ClientLabel(name="bar", owner=self.token.username),
            objects_pb2.ClientLabel(name="foo", owner=self.token.username)
        ])

  def testRemoveLabels(self):
    with test_lib.FakeTime(42):
      with aff4.FACTORY.Open(
          self.client_urn,
          aff4_type=aff4_grr.VFSGRRClient,
          mode="rw",
          token=self.token) as client_obj:
        client_obj.AddLabels(["bar", "foo"])

    client_ref = self.api.Client(client_id=self.client_urn.Basename())
    self.assertEqual(
        sorted(client_ref.Get().data.labels, key=lambda l: l.name), [
            objects_pb2.ClientLabel(name="bar", owner=self.token.username),
            objects_pb2.ClientLabel(name="foo", owner=self.token.username)
        ])

    client_ref.RemoveLabel("foo")
    self.assertEqual(
        sorted(client_ref.Get().data.labels, key=lambda l: l.name),
        [objects_pb2.ClientLabel(name="bar", owner=self.token.username)])


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
