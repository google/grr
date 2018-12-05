#!/usr/bin/env python
"""Tests for windows paths detection logic."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from grr_response_core.lib import flags
from grr_response_core.path_detection import windows
from grr.test_lib import test_lib


class RunDllExtractorTest(test_lib.GRRBaseTest):
  """Tests for RunDllExtractor."""

  def setUp(self):
    super(RunDllExtractorTest, self).setUp()
    self.extractor = windows.RunDllExtractor()

  def testDoesNothingIfFirstComponentIsNotRunDll(self):
    """Test it does nothing if the first component is not 'rundll'."""
    self.assertEqual(self.extractor.Extract(["a", "b"]), [])

  def testReturnsSecondOutOfTwoComponentsIfFirstOneIsRunDll(self):
    """Test it returns second out of 2 components if the first is 'rundll'."""
    self.assertEqual(self.extractor.Extract(["rundll32.exe", "b"]), ["b"])

  def testRunDllCheckIsCaseInsensitive(self):
    """Test it returns second out of 2 components if the first is 'rundll'."""
    self.assertEqual(self.extractor.Extract(["rUndll32.EXE", "b"]), ["b"])

  def testReturnsAllComponentsExceptForTheFirstOneIfFirstOneIsRunDll(self):
    """Test it returns all components except for the first 'rundll'."""
    self.assertEqual(
        self.extractor.Extract(["rundll32.exe", "b", "c", "d"]), ["b c d"])

  def testReturnsThirdOutOfThreeComponentsIfFirstTwoAreRunDll(self):
    """Test it returns 3rd out of 2 components if the first two are rundll."""
    self.assertEqual(
        self.extractor.Extract([r"C:\some", r"path\rundll32.exe", "b"]), ["b"])

  def testStripsFunctionName(self):
    """Test it strips the function name."""
    self.assertEqual(
        self.extractor.Extract(["rundll32.exe", "b,FuncName"]), ["b"])


class ExecutableExtractorTest(test_lib.GRRBaseTest):
  """Tests for ExecutableExtractor."""

  def setUp(self):
    super(ExecutableExtractorTest, self).setUp()
    self.extractor = windows.ExecutableExtractor()

  def testIgnoresPathWithoutExecutableExtensions(self):
    """Test it ignores a path without executable extensions."""
    self.assertEqual(self.extractor.Extract(["a", "b", "c"]), [])

  def testReturnsPathIfExecutableExtensionIsFound(self):
    """Test it returns a path if executable extension is found."""
    self.assertEqual(self.extractor.Extract(["a", "b.exe", "c"]), ["a b.exe"])

  def testExtractionIsCaseInsensitive(self):
    """Test the extraction is case insensitive."""
    self.assertEqual(self.extractor.Extract(["a", "b.ExE", "c"]), ["a b.ExE"])


class EnvVarsPostProcessorTest(test_lib.GRRBaseTest):
  """Tests for EnvVarsPostProcessorTest."""

  def testDoesNothingIfMappingIsEmpty(self):
    """Test it does nothing if the mapping is empty."""
    processor = windows.EnvVarsPostProcessor({})
    self.assertEqual(processor.Process("a"), ["a"])

  def testReplacesOneVariable(self):
    """Test it correctly replaces one variable."""
    processor = windows.EnvVarsPostProcessor({"foo": "bar"})
    self.assertEqual(
        processor.Process(r"C:\WINDOWS\%foo%\something"),
        [r"C:\WINDOWS\bar\something"])

  def testReplacesTwoVariables(self):
    """Test it correctly replaces two variables."""
    processor = windows.EnvVarsPostProcessor({"foo": "bar", "blah": "blahblah"})
    self.assertEqual(
        processor.Process(r"C:\WINDOWS\%foo%\%blah%\something"),
        [r"C:\WINDOWS\bar\blahblah\something"])

  def testVariableReplacementIsCaseInsensitive(self):
    """Test variable replacement is case insensitive."""
    processor = windows.EnvVarsPostProcessor({"foo": "bar"})
    self.assertEqual(
        processor.Process(r"C:\WINDOWS\%FoO%\something"),
        [r"C:\WINDOWS\bar\something"])

  def testGeneratesMultipleReplacementsIfReplacementIsList(self):
    """Test it generates multiple replacements if replacement is a list."""
    processor = windows.EnvVarsPostProcessor({"foo": ["bar", "blah"]})
    self.assertEqual(
        set(processor.Process(r"C:\WINDOWS\%foo%\something")),
        set([r"C:\WINDOWS\bar\something", r"C:\WINDOWS\blah\something"]))

  def testVariableValueIsStableInASinglePath(self):
    """Test it keeps variable value stable in a single path."""
    processor = windows.EnvVarsPostProcessor({"foo": ["bar", "blah"]})
    self.assertEqual(
        set(processor.Process(r"C:\WINDOWS\%foo%\%foo%\something")),
        set([
            r"C:\WINDOWS\bar\bar\something", r"C:\WINDOWS\blah\blah\something"
        ]))

  def testGeneratesProductIfTwoReplacementsHaveMultipleValues(self):
    """Test it generates a product if two replacements have multiple values."""
    processor = windows.EnvVarsPostProcessor({
        "foo": ["bar1", "bar2"],
        "blah": ["blah1", "blah2"]
    })
    self.assertEqual(
        set(processor.Process(r"C:\WINDOWS\%foo%\%blah%\something")),
        set([
            r"C:\WINDOWS\bar1\blah1\something",
            r"C:\WINDOWS\bar1\blah2\something",
            r"C:\WINDOWS\bar2\blah1\something",
            r"C:\WINDOWS\bar2\blah2\something"
        ]))

  def testReplacesSystemRootPrefixWithSystemRootVariable(self):
    """Test it replaces system root prefix with a system root variable."""
    processor = windows.EnvVarsPostProcessor({"systemroot": "blah"})
    self.assertEqual(
        processor.Process(r"\SystemRoot\foo\bar"), [r"blah\foo\bar"])

  def testReplacesSystem32PrefixWithSystemRootVariable(self):
    """Test it replaces system32 prefix with a system root variable."""
    processor = windows.EnvVarsPostProcessor({"systemroot": "blah"})
    self.assertEqual(
        processor.Process(r"System32\foo\bar"), [r"blah\system32\foo\bar"])


class WindowsRegistryExecutablePathsDetectorTest(test_lib.GRRBaseTest):
  """Tests for CreateWindowsRegistryExecutablePathsDetector() detector."""

  def testExtractsPathsFromNonRunDllStrings(self):
    """Test it extracts paths from non-rundll strings."""
    fixture = [(r"C:\Program Files\Realtek\Audio\blah.exe -s",
                r"C:\Program Files\Realtek\Audio\blah.exe"),
               (r"'C:\Program Files\Realtek\Audio\blah.exe' -s",
                r"C:\Program Files\Realtek\Audio\blah.exe"),
               (r"C:\Program Files\NVIDIA Corporation\nwiz.exe /quiet /blah",
                r"C:\Program Files\NVIDIA Corporation\nwiz.exe")]

    for in_str, result in fixture:
      self.assertEqual(list(windows.DetectExecutablePaths([in_str])), [result])

  def testExctactsPathsFromRunDllStrings(self):
    """Test it extracts paths from rundll strings."""
    fixture = [
        (r"rundll32.exe C:\Windows\system32\advpack.dll,DelNodeRunDLL32",
         r"C:\Windows\system32\advpack.dll"),
        (r"rundll32.exe 'C:\Program Files\Realtek\Audio\blah.exe',blah",
         r"C:\Program Files\Realtek\Audio\blah.exe"),
        (r"'rundll32.exe' 'C:\Program Files\Realtek\Audio\blah.exe',blah",
         r"C:\Program Files\Realtek\Audio\blah.exe")
    ]

    for in_str, result in fixture:
      self.assertEqual(
          set(windows.DetectExecutablePaths([in_str])),
          set([result, "rundll32.exe"]))

  def testReplacesEnvironmentVariable(self):
    """Test it replaces environment variables."""
    mapping = {
        "programfiles": r"C:\Program Files",
    }
    fixture = [(r"%ProgramFiles%\Realtek\Audio\blah.exe -s",
                r"C:\Program Files\Realtek\Audio\blah.exe"),
               (r"'%ProgramFiles%\Realtek\Audio\blah.exe' -s",
                r"C:\Program Files\Realtek\Audio\blah.exe")]

    for in_str, result in fixture:
      self.assertEqual(
          list(windows.DetectExecutablePaths([in_str], mapping)), [result])

  def testReplacesEnvironmentVariablesWithMultipleMappings(self):
    """Test it replaces environment variables with multiple mappings."""

    # TODO(hanuszczak): Raw unicode literals in Python 2 are broken since they
    # do not consider "\u" to be two characters ("\" and "u") but treat it is as
    # a unicode escape sequence. This behaviour is fixed in Python 3 so once the
    # codebase does not have to support Python 2 anymore, these escaped literals
    # can be rewritten with raw ones.

    mapping = {
        "appdata": [
            "C:\\Users\\foo\\Application Data",
            "C:\\Users\\bar\\Application Data",
        ]
    }

    fixture = [(r"%AppData%\Realtek\Audio\blah.exe -s", [
        "C:\\Users\\foo\\Application Data\\Realtek\\Audio\\blah.exe",
        "C:\\Users\\bar\\Application Data\\Realtek\\Audio\\blah.exe"
    ]), (r"'%AppData%\Realtek\Audio\blah.exe' -s", [
        "C:\\Users\\foo\\Application Data\\Realtek\\Audio\\blah.exe",
        "C:\\Users\\bar\\Application Data\\Realtek\\Audio\\blah.exe"
    ])]

    for in_str, result in fixture:
      self.assertEqual(
          set(windows.DetectExecutablePaths([in_str], mapping)), set(result))


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
