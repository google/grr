#!/usr/bin/env python
"""This modules contains tests for AFF4 API renderers."""



# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.gui.api_plugins import hunt as hunt_plugin

from grr.lib import flags
from grr.lib import hunts
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils


class ApiHuntsListRendererTest(test_lib.GRRBaseTest):
  """Test for ApiAff4Renderer."""

  def CreateSampleHunt(self, description):
    hunts.GRRHunt.StartHunt(
        hunt_name="GenericHunt",
        description=description,
        flow_runner_args=rdfvalue.FlowRunnerArgs(
            flow_name="GetFile"),
        flow_args=rdfvalue.GetFileArgs(
            pathspec=rdfvalue.PathSpec(
                path="/tmp/evil.txt",
                pathtype=rdfvalue.PathSpec.PathType.OS,
                )
            ),
        regex_rules=[], output_plugins=[], client_rate=0, token=self.token)

  def setUp(self):
    super(ApiHuntsListRendererTest, self).setUp()
    self.renderer = hunt_plugin.ApiHuntsListRenderer()

  def testRendersListOfHuntObjects(self):
    for i in range(10):
      self.CreateSampleHunt("hunt_%d" % i)

    result = self.renderer.Render(utils.DataObject(token=self.token))
    descriptions = set(r["description"] for r in result)

    self.assertEqual(len(descriptions), 10)
    for i in range(10):
      self.assertTrue("hunt_%d" % i in descriptions)

  def testHuntListIsSortedInReversedCreationTimestampOrder(self):
    for i in range(10):
      with test_lib.FakeTime(i * 1000):
        self.CreateSampleHunt("hunt_%d" % i)

    result = self.renderer.Render(utils.DataObject(token=self.token))
    create_times = [r["create_time"] for r in result]

    self.assertEqual(len(create_times), 10)
    for index, expected_time in enumerate(reversed(range(10))):
      self.assertEqual(create_times[index], expected_time * 1000000000)

  def testRendersSubrangeOfListOfHuntObjects(self):
    for i in range(10):
      with test_lib.FakeTime(i * 1000):
        self.CreateSampleHunt("hunt_%d" % i)

    result = self.renderer.Render(utils.DataObject(
        offset=2, count=2, token=self.token))
    create_times = [r["create_time"] for r in result]

    self.assertEqual(len(create_times), 2)
    self.assertEqual(create_times[0], 7 * 1000000000)
    self.assertEqual(create_times[1], 6 * 1000000000)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
