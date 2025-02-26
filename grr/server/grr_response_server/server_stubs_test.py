#!/usr/bin/env python
"""Tests for server stubs for client actions."""

from absl import app

from grr_response_client import client_actions
from grr_response_server import action_registry
from grr.test_lib import client_action_test_lib
from grr.test_lib import test_lib


class ClientActionStubTest(
    client_action_test_lib.WithAllClientActionsMixin, test_lib.GRRBaseTest
):

  def testThereIsStubForEveryClientAction(self):
    # Check that some real ActionPlugin classes got imported.
    self.assertNotEmpty(client_actions.REGISTRY)

    # Check that there's >0 server stubs.
    self.assertNotEmpty(action_registry.ACTION_STUB_BY_ID)

    for name, cls in client_actions.REGISTRY.items():
      self.assertIn(name, action_registry.ACTION_STUB_BY_ID)

      stub_cls = action_registry.ACTION_STUB_BY_ID[name]
      self.assertEqual(
          cls.in_rdfvalue,
          stub_cls.in_rdfvalue,
          "%s in_rdfvalue differs from the stub: %s vs %s"
          % (name, cls.in_rdfvalue, stub_cls.in_rdfvalue),
      )
      if stub_cls.in_rdfvalue is not None:
        self.assertEqual(
            stub_cls.in_proto,
            stub_cls.in_rdfvalue.protobuf,
            "stub %s in_proto type does not match in_rdfvalue.protobuf type: %s"
            " vs %s" % (name, stub_cls.in_proto, stub_cls.in_rdfvalue.protobuf),
        )
      self.assertEqual(
          cls.out_rdfvalues,
          stub_cls.out_rdfvalues,
          "%s out_rdfvalues differ from the stub: %s vs %s"
          % (name, cls.out_rdfvalues, stub_cls.out_rdfvalues),
      )


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
