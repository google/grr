#!/usr/bin/env python
# Lint as: python3
"""E2E tests for the timeline flow."""
import csv
import io
from typing import Sequence
from typing import Text

from absl.testing import absltest

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.util import temp
from grr_response_proto.api import timeline_pb2
from grr_response_test.end_to_end_tests import test_base


class TestTimelineLinux(test_base.EndToEndTest):
  """A class with Linux-specific timeline tests."""

  platforms = [test_base.EndToEndTest.Platform.LINUX]

  def testUsrBin(self):
    args = self.grr_api.types.CreateFlowArgs("TimelineFlow")
    args.root = "/bin/".encode("utf-8")

    flow = self.RunFlowAndWait("TimelineFlow", args=args)

    with temp.AutoTempFilePath(suffix=".body") as temp_filepath:
      timeline_format = timeline_pb2.ApiGetCollectedTimelineArgs.Format.BODY

      body = flow.GetCollectedTimeline(timeline_format)
      body.WriteToFile(temp_filepath)

      with io.open(temp_filepath, mode="r", encoding="utf-8") as temp_filedesc:
        entries = list(csv.reader(temp_filedesc, delimiter="|"))

    paths = [entry[1] for entry in entries]
    self.assertIn("/bin/bash", paths)
    self.assertIn("/bin/cat", paths)
    self.assertIn("/bin/chmod", paths)
    self.assertIn("/bin/cp", paths)
    self.assertIn("/bin/rm", paths)
    self.assertIn("/bin/sleep", paths)

    for entry in entries:
      assertBodyEntrySanity(self, entry)


class TestTimelineWindows(test_base.EndToEndTest):
  """A class with Windows-specific timeline tests."""

  platforms = [test_base.EndToEndTest.Platform.WINDOWS]

  def testWindows(self):
    args = self.grr_api.types.CreateFlowArgs("TimelineFlow")
    args.root = "C:\\Windows".encode("utf-8")

    flow = self.RunFlowAndWait("TimelineFlow", args=args)

    with temp.AutoTempFilePath(suffix=".body") as temp_filepath:
      timeline_format = timeline_pb2.ApiGetCollectedTimelineArgs.Format.BODY

      body = flow.GetCollectedTimeline(timeline_format)
      body.WriteToFile(temp_filepath)

      with io.open(temp_filepath, mode="r", encoding="utf-8") as temp_filedesc:
        entries = list(csv.reader(temp_filedesc, delimiter="|"))

    paths = [entry[1].lower() for entry in entries]
    self.assertIn("C:\\Windows\\explorer.exe".lower(), paths)
    self.assertIn("C:\\Windows\\notepad.exe".lower(), paths)
    self.assertIn("C:\\Windows\\regedit.exe".lower(), paths)
    self.assertIn("C:\\Windows\\System32\\dwm.exe".lower(), paths)

    for entry in entries:
      assertBodyEntrySanity(self, entry)


def assertBodyEntrySanity(  # pylint: disable=invalid-name
    test: absltest.TestCase,
    entry: Sequence[Text],
) -> None:
  """Asserts that given row of a body file is sane."""
  # Size should be non-negative (some files might be empty, though).
  test.assertGreaterEqual(int(entry[6]), 0)

  # All timestamps should be positive.
  test.assertGreater(int(entry[7]), 0)
  test.assertGreater(int(entry[8]), 0)
  test.assertGreater(int(entry[9]), 0)

  # All timestamps should be older than now.
  now = rdfvalue.RDFDatetime.Now()
  test.assertLessEqual(int(entry[7]), now.AsSecondsSinceEpoch())
  test.assertLessEqual(int(entry[8]), now.AsSecondsSinceEpoch())
  test.assertLessEqual(int(entry[9]), now.AsSecondsSinceEpoch())
