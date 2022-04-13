#!/usr/bin/env python
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
    # `/bin` might be symlink to `/usr/bin`.
    self.assertTrue("/bin/bash" in paths or "/usr/bin/bash" in paths)
    self.assertTrue("/bin/cat" in paths or "/usr/bin/cat" in paths)
    self.assertTrue("/bin/chmod" in paths or "/usr/bin/chmod" in paths)
    self.assertTrue("/bin/cp" in paths or "/usr/bin/cp" in paths)
    self.assertTrue("/bin/rm" in paths or "/usr/bin/rm" in paths)
    self.assertTrue("/bin/sleep" in paths or "/usr/bin/sleep" in paths)

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

  def testWindowsBackslashEscape(self):
    args = self.grr_api.types.CreateFlowArgs("TimelineFlow")
    args.root = "C:\\Windows".encode("utf-8")

    flow = self.RunFlowAndWait("TimelineFlow", args=args)

    with temp.AutoTempFilePath(suffix=".body") as temp_filepath:
      body = flow.GetCollectedTimelineBody(backslash_escape=True)
      body.WriteToFile(temp_filepath)

      with io.open(temp_filepath, mode="r", encoding="utf-8") as temp_filedesc:
        content = temp_filedesc.read().lower()

    self.assertIn("|C:\\\\Windows\\\\explorer.exe|".lower(), content)
    self.assertIn("|C:\\\\Windows\\\\notepad.exe|".lower(), content)
    self.assertIn("|C:\\\\Windows\\\\regedit.exe|".lower(), content)
    self.assertIn("|C:\\\\Windows\\\\System32\\\\dwm.exe|".lower(), content)


def assertBodyEntrySanity(  # pylint: disable=invalid-name
    test: absltest.TestCase,
    entry: Sequence[Text],
) -> None:
  """Asserts that given row of a body file is sane."""
  # Size should be non-negative (some files might be empty, though).
  test.assertGreaterEqual(int(entry[6]), 0)

  # All timestamps should be positive or zero (in some pathological cases).
  test.assertGreaterEqual(float(entry[7]), 0.0)
  test.assertGreaterEqual(float(entry[8]), 0.0)
  test.assertGreaterEqual(float(entry[9]), 0.0)

  # All timestamps should be older than now.
  now_secs = rdfvalue.RDFDatetime.Now().AsMicrosecondsSinceEpoch() / 1e6
  test.assertLessEqual(float(entry[7]), now_secs)
  test.assertLessEqual(float(entry[8]), now_secs)
  test.assertLessEqual(float(entry[9]), now_secs)
