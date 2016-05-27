#!/usr/bin/env python
"""Tests for grr.lib.output_plugin."""


from grr.lib import aff4
from grr.lib import flags
from grr.lib import flow_runner
from grr.lib import hunts
from grr.lib import output_plugin
from grr.lib import test_lib
from grr.lib.hunts import standard


class TestOutputPlugin(output_plugin.OutputPlugin):

  def ProcessResponses(self, responses):
    pass


class TestOutputPluginVerifier(output_plugin.OutputPluginVerifier):

  def VerifyHuntOutput(self, plugin, hunt):
    if hunt.GetRunner().args.description == "raise":
      raise RuntimeError("oh no")

    return output_plugin.OutputPluginVerificationResult(
        status_message=hunt.GetRunner().args.description)


class OutputPluginVerifierTest(test_lib.GRRBaseTest):
  """Tests for OutputPluginVerifier."""

  def _CreateHunt(self, description):
    output_plugins = [output_plugin.OutputPluginDescriptor(
        plugin_name="TestOutputPlugin")]
    with hunts.GRRHunt.StartHunt(
        hunt_name=standard.GenericHunt.__name__,
        flow_runner_args=flow_runner.FlowRunnerArgs(flow_name="GetFile"),
        output_plugins=output_plugins,
        description=description,
        client_rate=0,
        token=self.token) as hunt:
      return hunt

  def _GetPlugin(self, hunt):
    results_metadata = aff4.FACTORY.Open(
        hunt.urn.Add("ResultsMetadata"),
        token=self.token)
    descriptor, state = results_metadata.Get(
        results_metadata.Schema.OUTPUT_PLUGINS).values()[0]
    return descriptor.GetPluginForState(state)

  def setUp(self):
    super(OutputPluginVerifierTest, self).setUp()
    self.verifier = TestOutputPluginVerifier()

  def testMultiVerifyHuntOutputCallsVerifyHuntOutputIteratively(self):
    hunt1 = self._CreateHunt("desc1")
    plugin1 = self._GetPlugin(hunt1)

    hunt2 = self._CreateHunt("desc2")
    plugin2 = self._GetPlugin(hunt2)

    hunt3 = self._CreateHunt("desc3")
    plugin3 = self._GetPlugin(hunt3)

    results = list(self.verifier.MultiVerifyHuntOutput([(plugin1, hunt1), (
        plugin2, hunt2), (plugin3, hunt3)]))

    self.assertEqual(len(results), 3)

    self.assertEqual(results[0][0], hunt1.urn)
    self.assertEqual(results[0][1].status_message, "desc1")

    self.assertEqual(results[1][0], hunt2.urn)
    self.assertEqual(results[1][1].status_message, "desc2")

    self.assertEqual(results[2][0], hunt3.urn)
    self.assertEqual(results[2][1].status_message, "desc3")

  def testMultiVerifyHuntOutputRaisesIfVerifyHuntOutputRaises(self):
    # TestOutputPluginVerifier will raise on this one.
    hunt1 = self._CreateHunt("raise")
    plugin1 = self._GetPlugin(hunt1)

    with self.assertRaises(output_plugin.MultiVerifyHuntOutputError):
      _ = list(self.verifier.MultiVerifyHuntOutput([(plugin1, hunt1)]))

  def testMultiVerifyHuntOutputContinuesVerifyingIfExceptionOccurs(self):
    hunt1 = self._CreateHunt("desc1")
    plugin1 = self._GetPlugin(hunt1)

    hunt2 = self._CreateHunt("raise")
    plugin2 = self._GetPlugin(hunt2)

    hunt3 = self._CreateHunt("desc3")
    plugin3 = self._GetPlugin(hunt3)

    results = []
    with self.assertRaisesRegexp(output_plugin.MultiVerifyHuntOutputError,
                                 "oh no"):
      for hunt_urn, verification_result in self.verifier.MultiVerifyHuntOutput(
          [(plugin1, hunt1), (plugin2, hunt2), (plugin3, hunt3)]):
        results.append((hunt_urn, verification_result))

    self.assertEqual(len(results), 2)

    self.assertEqual(results[0][0], hunt1.urn)
    self.assertEqual(results[0][1].status_message, "desc1")

    self.assertEqual(results[1][0], hunt3.urn)
    self.assertEqual(results[1][1].status_message, "desc3")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
