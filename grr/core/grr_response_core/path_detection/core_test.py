#!/usr/bin/env python
"""Tests core paths detection logic."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from builtins import range  # pylint: disable=redefined-builtin

from grr_response_core.lib import flags
from grr_response_core.path_detection import core
from grr.test_lib import test_lib


class SplitIntoComponentsTest(test_lib.GRRBaseTest):
  """Tests for SplitIntoComponents function."""

  def testSplitsBySpaceInTrivialCases(self):
    """Test it splits components by space in trivial cases."""
    self.assertEqual(
        core.SplitIntoComponents(r"C:\Program Files\Realtek\Audio\blah.exe -s"),
        [r"C:\Program", r"Files\Realtek\Audio\blah.exe", r"-s"])
    self.assertEqual(
        core.SplitIntoComponents(
            r"rundll32.exe C:\Windows\system32\advpack.dll,DelNodeRunDLL32"),
        [r"rundll32.exe", r"C:\Windows\system32\advpack.dll,DelNodeRunDLL32"])

  def testStripsDoubleQuotes(self):
    """Test it strips double quotes."""
    self.assertEqual(
        core.SplitIntoComponents(
            "\"C:\\Program Files\\Realtek\\Audio\\blah.exe\""),
        [r"C:\Program Files\Realtek\Audio\blah.exe"])

  def testStripsSingleQuotes(self):
    """Test it strips single quotes."""
    self.assertEqual(
        core.SplitIntoComponents(r"'C:\Program Files\Realtek\Audio\blah.exe'"),
        [r"C:\Program Files\Realtek\Audio\blah.exe"])

  def testStripsSingleQuotesEvenIfFirstComponentIsNotQuoted(self):
    """Test it strips single quotes even if first component is not quoted."""
    self.assertEqual(
        core.SplitIntoComponents(
            r"rundll32.exe 'C:\Program Files\Realtek\Audio\blah.exe'"),
        [r"rundll32.exe", r"C:\Program Files\Realtek\Audio\blah.exe"])

  def testStripsSingleQuotesEvenIfThereIsCommaAfterQuote(self):
    """Test it strips single quotes even if there's a comma after the quote."""
    self.assertEqual(
        core.SplitIntoComponents(
            r"rundll32.exe 'C:\Program Files\Realtek\Audio\blah.exe',SomeFunc"),
        [r"rundll32.exe", r"C:\Program Files\Realtek\Audio\blah.exe,SomeFunc"])

  def testStripsDoubleQuotesEvenIfFirstComponentIsNotQuoted(self):
    """Test it strips double quotes even first component is not quoted."""
    self.assertEqual(
        core.SplitIntoComponents(
            "rundll32.exe "
            "\"C:\\Program Files\\Realtek\\Audio\\blah.exe\""),
        [r"rundll32.exe", r"C:\Program Files\Realtek\Audio\blah.exe"])

  def testStripsDoubleQuotesEvenIfThereIsCommaAfterQuote(self):
    """Test it strips double quotes even if there's a comma after the quote."""
    self.assertEqual(
        core.SplitIntoComponents(
            "rundll32.exe "
            "\"C:\\Program Files\\Realtek\\Audio\\blah.exe\",SomeFunc"),
        [r"rundll32.exe", r"C:\Program Files\Realtek\Audio\blah.exe,SomeFunc"])


class TestExtractor(core.Extractor):
  """Test extractor class."""

  def __init__(self, multiplier=1):
    super(TestExtractor, self).__init__()
    self.multiplier = multiplier

  def Extract(self, components):
    last_component = components[-1]
    return ["%s_%d" % (last_component, i) for i in range(self.multiplier)]


class TestPostProcessor(core.PostProcessor):
  """Test post processor that adds a suffix to the path."""

  def __init__(self, suffix, count=1):
    super(TestPostProcessor, self).__init__()
    self.suffix = suffix
    self.count = count

  def Process(self, path):
    return [path + self.suffix * (i + 1) for i in range(self.count)]


class DetectorTest(test_lib.GRRBaseTest):
  """Tests for the Detector class."""

  def testReturnsWhatSingleExtractorReturns(self):
    """Test it returns what a single extractor returns."""
    detector = core.Detector(extractors=[TestExtractor()])
    self.assertEqual(detector.Detect("a b"), set(["b_0"]))

  def testReturnsCombinedResultsFromTwoExtractors(self):
    """Test it returns combined results from two extractors."""
    detector = core.Detector(
        extractors=[TestExtractor(multiplier=2),
                    TestExtractor(multiplier=3)])
    self.assertEqual(detector.Detect("a b"), set(["b_0", "b_1", "b_2"]))

  def testAppliesPostProcessorToExtractedPaths(self):
    """Test it applies the post processor to extracted paths."""
    detector = core.Detector(
        extractors=[TestExtractor(multiplier=2)],
        post_processors=[TestPostProcessor("_bar")])
    self.assertEqual(detector.Detect("a b"), set(["b_0_bar", "b_1_bar"]))

  def testPostProcessorMayReturnMultipleProcessedPaths(self):
    """Test the post processor may return multiple processed paths."""
    detector = core.Detector(
        extractors=[TestExtractor(multiplier=2)],
        post_processors=[TestPostProcessor("_bar", count=2)])
    self.assertEqual(
        detector.Detect("a b"),
        set(["b_0_bar", "b_1_bar", "b_0_bar_bar", "b_1_bar_bar"]))

  def testAppliesMultiplePostProcessorsToExtractedPaths(self):
    """Test it applies mutliple post processors to extracted paths."""
    detector = core.Detector(
        extractors=[TestExtractor(multiplier=2)],
        post_processors=[TestPostProcessor("_foo"),
                         TestPostProcessor("_bar")])
    self.assertEqual(
        detector.Detect("a b"), set(["b_0_foo_bar", "b_1_foo_bar"]))


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
