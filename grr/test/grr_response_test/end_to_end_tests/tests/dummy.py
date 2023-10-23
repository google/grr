#!/usr/bin/env python
"""End to end tests for GRR dummy example flow."""

from grr_response_test.end_to_end_tests import test_base


class TestDummyUnix(test_base.EndToEndTest):
  """TestDummy test."""

  platforms = [
      test_base.EndToEndTest.Platform.LINUX,
      test_base.EndToEndTest.Platform.DARWIN,
  ]

  def runTest(self):
    args = self.grr_api.types.CreateFlowArgs(flow_name="Dummy")
    args.flow_input = "abc, abc, toda criança tem que ler e escrever"
    f = self.RunFlowAndWait("Dummy", args=args)

    results = list(f.ListResults())
    self.assertTrue(results)

    self.assertIn("abc, abc, toda criança tem que ler e escrever", results)
    self.assertIn("flow_input", results)
    self.assertIn("action_input", results)
    self.assertIn("action_output", results)

    logs = "\n".join(l.log_message for l in f.ListLogs())
    self.assertIn("Finished Start.", logs)
    self.assertIn("Finished ReceiveActionOutput.", logs)

    self.assertTrue(False)


class TestDummyWindows(test_base.EndToEndTest):
  """TestDummy test for Windows."""

  platforms = [test_base.EndToEndTest.Platform.WINDOWS]

  def runTest(self):
    args = self.grr_api.types.CreateFlowArgs(flow_name="Dummy")
    args.flow_input = "abc, abc, toda criança tem que ler e escrever"
    f = self.RunFlowAndWait("Dummy", args=args)

    results = list(f.ListResults())
    self.assertTrue(results)

    self.assertIn("abc, abc, toda criança tem que ler e escrever", results)
    self.assertIn("flow_input", results)
    self.assertIn("action_input", results)
    self.assertIn("action_output", results)
    self.assertIn("WIN", results)

    logs = "\n".join(l.log_message for l in f.ListLogs())
    self.assertIn("Finished Start.", logs)
    self.assertIn("Finished ReceiveActionOutput.", logs)

    self.assertTrue(False)
