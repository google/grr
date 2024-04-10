#!/usr/bin/env python
"""Test for client comms."""

from absl import app

from grr_response_client import comms
from grr_response_core.lib import rdfvalue
from grr.test_lib import test_lib


class GRRClientWorkerTest(test_lib.GRRBaseTest):
  """Tests the GRRClientWorker class."""

  def setUp(self):
    super().setUp()
    self.client_worker = comms.GRRClientWorker()

  def testSendReplyHandlesFalseyPrimitivesCorrectly(self):
    self.client_worker.SendReply(rdfvalue.RDFDatetime(0))
    messages = self.client_worker.Drain().job

    self.assertLen(messages, 1)
    self.assertEqual(messages[0].args_rdf_name, rdfvalue.RDFDatetime.__name__)
    self.assertIsInstance(messages[0].payload, rdfvalue.RDFDatetime)
    self.assertEqual(messages[0].payload, rdfvalue.RDFDatetime(0))


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
