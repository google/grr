#!/usr/bin/env python
"""Tests for server stubs for client actions."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from future.utils import iteritems

from grr_response_client import actions
# pylint: disable=unused-import
from grr_response_client.client_actions import registry_init
# pylint: enable=unused-import

from grr_response_core.lib import flags
from grr_response_server import server_stubs
from grr.test_lib import test_lib


class ClientActionStubTest(test_lib.GRRBaseTest):

  def testThereIsStubForEveryClientAction(self):
    # Check that some real ActionPlugin classes got imported.
    self.assertTrue(actions.ActionPlugin.classes)

    # Check that there's >0 server stubs.
    self.assertTrue(server_stubs.ClientActionStub.classes)

    for name, cls in iteritems(actions.ActionPlugin.classes):
      # Skip actions defined in tests.
      if "_test" in cls.__module__ or "test_lib" in cls.__module__:
        continue

      self.assertTrue(
          name in server_stubs.ClientActionStub.classes,
          "%s.%s client action stub is missing" % (cls.__module__, name))

      stub_cls = server_stubs.ClientActionStub.classes[name]
      self.assertEqual(
          cls.in_rdfvalue, stub_cls.in_rdfvalue,
          "%s in_rdfvalue differs from the stub: %s vs %s" %
          (name, cls.in_rdfvalue, stub_cls.in_rdfvalue))
      self.assertEqual(
          cls.out_rdfvalues, stub_cls.out_rdfvalues,
          "%s out_rdfvalues differ from the stub: %s vs %s" %
          (name, cls.out_rdfvalues, stub_cls.out_rdfvalues))


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
