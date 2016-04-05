#!/usr/bin/env python
"""Tests for config_lib classes."""

import copy
import os
import StringIO

from grr.lib import config_lib
from grr.lib import flags
from grr.lib import test_lib
from grr.lib import type_info
from grr.lib import utils


class YamlConfigTest(test_lib.GRRBaseTest):
  """Test the Yaml config file support."""

  @flags.FlagOverrider(disallow_missing_config_definitions=True)
  def testParsing(self):
    conf = config_lib.GrrConfigManager()

    conf.DEFINE_list("Section1.test_list", ["a", "b"], "A test integer.")
    conf.DEFINE_integer("Section1.test", 0, "An integer")
    conf.DEFINE_integer("Section1.test2", 0, "An integer")
    self.assertRaises(config_lib.MissingConfigDefinitionError, conf.Initialize,
                      parser=config_lib.YamlParser, data="""
                      Section2.test: 2
                      """)

    conf.DEFINE_string("Section2.test", "", "A string")
    conf.DEFINE_context("Client Context")
    conf.DEFINE_context("Windows Context")
    conf.Initialize(parser=config_lib.YamlParser, data="""

# Configuration options can be written as long hand, dot separated parameters.
Section1.test: 2
Section1.test_list: x,y
Section2.test: 3%(Section1.test)

Client Context:
  Section1.test: 6
  Section1.test2: 1

  Windows Context:
    Section1.test: 10

Windows Context:
  Section1.test: 5
  Section1.test2: 2

""")

    self.assertEqual(conf["Section1.test"], 2)

    # Test interpolation works.
    self.assertEqual(conf["Section2.test"], "32")
    self.assertEqual(conf["Section1.test_list"], ["x", "y"])

    self.assertEqual(conf.Get("Section1.test_list",
                              context=["Client Context", "Windows Context"]),
                     ["x", "y"])

    # Test that contexts affect option selection.
    self.assertEqual(
        conf.Get("Section1.test", context=["Client Context"]), 6)

    self.assertEqual(
        conf.Get("Section1.test", context=["Windows Context"]), 5)

    context = ["Client Context", "Windows Context"]
    self.assertEqual(
        conf.Get("Section1.test", context=context), 10)

    context = ["Windows Context", "Client Context"]
    # Order of the context parameters should not matter.
    self.assertEqual(
        conf.Get("Section1.test", context=context), 10)

  def testConflictingContexts(self):
    """Test that conflicting contexts are resolved by precedence."""
    conf = config_lib.GrrConfigManager()

    conf.DEFINE_integer("Section1.test", 0, "An integer")
    conf.DEFINE_context("Client Context")
    conf.DEFINE_context("Platform:Windows")
    conf.DEFINE_context("Extra Context")
    conf.Initialize(parser=config_lib.YamlParser, data="""

Section1.test: 2

Client Context:
  Section1.test: 6

Platform:Windows:
  Section1.test: 10

Extra Context:
  Section1.test: 15
""")

    # Without contexts.
    self.assertEqual(conf.Get("Section1.test"), 2)

    # When running in the client context only.
    self.assertEqual(conf.Get("Section1.test", context=["Client Context"]), 6)

    # Later defined contexts (i.e. with later calls to AddContext()) are
    # stronger than earlier contexts. For example, contexts set the command line
    # --context option are stronger than contexts set by the running binary,
    # since they are added last.
    self.assertEqual(
        conf.Get("Section1.test",
                 context=["Client Context", "Platform:Windows"]),
        10)

    self.assertEqual(
        conf.Get("Section1.test",
                 context=["Platform:Windows", "Client Context"]),
        6)

  def testRemoveContext(self):
    """Test that conflicting contexts are resolved by precedence."""
    conf = config_lib.GrrConfigManager()

    conf.DEFINE_integer("Section1.test", 0, "An integer")
    conf.DEFINE_integer("Section1.test2", 9, "An integer")
    conf.DEFINE_context("Client Context")
    conf.DEFINE_context("Platform:Windows")
    conf.DEFINE_context("Extra Context")
    conf.Initialize(parser=config_lib.YamlParser, data="""

Section1.test: 2

Client Context:
  Section1.test: 6
  Section1.test2: 8

Platform:Windows:
  Section1.test: 10

Extra Context:
  Section1.test: 15
""")

    # Should be defaults, no contexts added
    self.assertEqual(conf.Get("Section1.test"), 2)
    self.assertEqual(conf.Get("Section1.test2"), 9)

    # Now with Client Context
    conf.AddContext("Client Context")
    self.assertEqual(conf.Get("Section1.test"), 6)
    self.assertEqual(conf.Get("Section1.test2"), 8)

    # Should be back to defaults
    conf.RemoveContext("Client Context")
    self.assertEqual(conf.Get("Section1.test"), 2)
    self.assertEqual(conf.Get("Section1.test2"), 9)

    # Now with Windows Context, test2 is still default
    conf.AddContext("Platform:Windows")
    self.assertEqual(conf.Get("Section1.test"), 10)
    self.assertEqual(conf.Get("Section1.test2"), 9)

    # Should be back to defaults
    conf.RemoveContext("Platform:Windows")
    self.assertEqual(conf.Get("Section1.test"), 2)
    self.assertEqual(conf.Get("Section1.test2"), 9)

  def testBackslashes(self):
    conf = config_lib.GrrConfigManager()

    conf.DEFINE_string("Section1.parameter", "", "A test.")
    conf.DEFINE_string("Section1.parameter2", "", "A test.")
    conf.DEFINE_string("Section1.parameter3", "", "A test.")

    conf.Initialize(parser=config_lib.YamlParser, data=r"""

Section1.parameter: |
   a\\b\\c\\d

Section1.parameter2: |
   %(parameter)\\e

Section1.parameter3: |
   \%(a\\b\\c\\d\)
""")

    self.assertEqual(conf.Get("Section1.parameter"), "a\\b\\c\\d")
    self.assertEqual(conf.Get("Section1.parameter2"), "a\\b\\c\\d\\e")
    self.assertEqual(conf.Get("Section1.parameter3"), "%(a\\b\\c\\d)")


class ConfigLibTest(test_lib.GRRBaseTest):
  """Tests for config functionality."""

  def testInit(self):
    """Testing initialization of a ConfigManager."""
    conf = config_lib.CONFIG

    # Check that the linux client have a different value from the windows
    # client.
    self.assertEqual(conf.Get("MemoryDriver.device_path",
                              context=("Client Context", "Platform:Linux")),
                     "/dev/pmem")

    self.assertEqual(conf.Get("MemoryDriver.device_path",
                              context=("Client Context", "Platform:Windows")),
                     r"\\.\pmem")

  def testSet(self):
    """Test setting options."""
    # Test access methods.
    conf = config_lib.GrrConfigManager()
    conf.DEFINE_string("NewSection1.new_option1", "Default Value", "Help")
    conf.initialized = True

    conf.Set("NewSection1.new_option1", "New Value1")

    self.assertEqual(conf["NewSection1.new_option1"], "New Value1")

  def testSave(self):
    """Save the config and ensure it still works."""
    conf = config_lib.GrrConfigManager()
    config_file = os.path.join(self.temp_dir, "writeback.yaml")
    conf.SetWriteBack(config_file)
    conf.DEFINE_string("NewSection1.new_option1", "Default Value", "Help")

    conf.Set("NewSection1.new_option1", "New Value1")

    conf.Write()

    new_conf = config_lib.GrrConfigManager()
    new_conf.DEFINE_string("NewSection1.new_option1", "Default Value", "Help")

    new_conf.Initialize(config_file)

    self.assertEqual(new_conf["NewSection1.new_option1"], "New Value1")

  def testErrorDetection(self):
    """Check that invalid config files are detected immediately."""
    test_conf = """
[Section1]
test = val2"""
    conf = config_lib.GrrConfigManager()
    # Define test as an integer.
    conf.DEFINE_integer("Section1.test", 54, "A test integer.")

    conf.Initialize(data=test_conf)

    # This should raise since the config file is incorrect.
    errors = conf.Validate("Section1")
    self.assertTrue(
        "Invalid value val2 for Integer" in str(errors["Section1.test"]))

  def testEmptyClientPrivateKey(self):
    """Check an empty client private_key passes."""
    # Clone a test config object from the global config so it knows about Client
    # options.
    conf = config_lib.CONFIG.MakeNewConfig()
    conf.Initialize(data="""
[Client]
private_key =
driver_signing_public_key = -----BEGIN PUBLIC KEY-----
    MFwwDQYJKoZIhvcNAQEBBQADSwAwSAJBALnfFW1FffeKPs5PLUhFOSkNrr9TDCOD
    QAI3WluLh0sW7/ro93eoIZ0FbipnTpzGkPpriONbSOXmxWNTo0b9ma8CAwEAAQ==
    -----END PUBLIC KEY-----
executable_signing_public_key = -----BEGIN PUBLIC KEY-----
    MFwwDQYJKoZIhvcNAQEBBQADSwAwSAJBALnfFW1FffeKPs5PLUhFOSkNrr9TDCOD
    QAI3WluLh0sW7/ro93eoIZ0FbipnTpzGkPpriONbSOXmxWNTo0b9ma8CAwEAAQ==
    -----END PUBLIC KEY-----
""")
    errors = conf.Validate(["Client"])
    self.assertItemsEqual(errors.keys(), [])

  def testEmptyClientKeys(self):
    """Check that empty other keys fail."""
    conf = config_lib.CONFIG.MakeNewConfig()
    conf.Initialize(data="""
[Client]
private_key =
driver_signing_public_key =
executable_signing_public_key =

[CA]
certificate =
""")
    errors = conf.Validate(["Client"])
    self.assertItemsEqual(errors.keys(),
                          ["Client.driver_signing_public_key",
                           "Client.executable_signing_public_key"])

  def testGet(self):
    conf = config_lib.GrrConfigManager()
    conf.DEFINE_string("Section1.foobar", "test", "A test string.")
    conf.DEFINE_string("Section1.foobaz", None, "An empty default string.")
    conf.DEFINE_string("Section1.foobin", "", "An empty default string.")
    conf.initialized = True
    self.assertEqual(conf.Get("Section1.foobar"), "test")
    self.assertEqual(conf.Get("Section1.foobar", default=None), None)
    conf.Initialize(data="""
[Section1]
foobar = X
""")
    self.assertEqual(conf.Get("Section1.foobar", default=None), "X")

    # This not being None is a little surprising, but probably not a big deal
    self.assertEqual(conf.Get("Section1.foobaz"), "")
    self.assertEqual(conf.Get("Section1.foobin"), "")

  def testAddOption(self):
    """Test that we can add options."""
    conf = config_lib.GrrConfigManager()

    conf.DEFINE_string("Section1.foobar", "test", "A test string.")
    conf.DEFINE_string("Section1.test", "test", "A test string.")

    conf.DEFINE_string("Section1.interpolated", "", "An interpolated string.")

    # This entry is not correct - the default is invalid.
    conf.DEFINE_integer("Section1.broken_int", "string", "A test integer.")

    conf.DEFINE_string("Section1.system", None, "The basic operating system.")
    conf.DEFINE_integer("Section1.test_int", 54, "A test integer.")
    conf.DEFINE_list("Section1.test_list", ["a", "b"], "A test integer.")
    conf.DEFINE_list("Section1.test_list2", ["a", "b"], "A test integer.")

    conf.DEFINE_integer("Section2.test_int", None, "A test integer.")
    conf.DEFINE_string("Section2.interpolated", "", "An interpolated string.")

    conf.DEFINE_integer("Section3.test_int", None, "A test integer.")
    conf.DEFINE_string("Section3.interpolated", "", "An interpolated string.")
    conf.Initialize(data="""
[Section1]
foobar = X
test_list = x,y

[Section2]
test_int = 34
interpolated = %(Section1.foobar)Y

[Section3]
test_int = 1
interpolated = %(%(Section1.foobar)|lower)Y

""")

    # The default value is invalid.
    errors = conf.Validate("Section1")
    self.assertIn("Invalid value string for Integer",
                  str(errors["Section1.broken_int"]))

    # Section not specified:
    self.assertRaises(config_lib.UnknownOption, conf.__getitem__, "a")

    # Test direct access.
    self.assertEqual(conf["Section1.foobar"], "X")
    self.assertEqual(conf["Section1.test_list"], ["x", "y"])
    self.assertEqual(conf["Section1.test_list2"], ["a", "b"])

    # Test default access.
    self.assertEqual(conf["Section1.test"], "test")

    # Test interpolation with full section name.
    self.assertEqual(conf["Section2.interpolated"], "XY")

    # Check that default values are typed.
    self.assertEqual(conf["Section1.test_int"], 54)

    # Test filter functions.
    self.assertEqual(conf["Section3.interpolated"], "xY")

  def testConstants(self):
    """Test that we can add options."""
    conf = config_lib.GrrConfigManager()
    conf.initialized = False

    conf.DEFINE_constant_string("Section1.const", "test", "A test string.")

    # We should be able to read this while the config is not initialized.
    self.assertEqual(conf["Section1.const"], "test")

    data = """
[Section1]
const = New string
"""

    # Modification of constant values is an error.
    self.assertRaises(config_lib.ConstModificationError, conf.Set,
                      "Section1.const", "New string")
    self.assertRaises(config_lib.ConstModificationError, conf.SetRaw,
                      "Section1.const", "New string")
    self.assertRaises(config_lib.ConstModificationError, conf.Initialize,
                      data=data)

  @flags.FlagOverrider(disallow_missing_config_definitions=True)
  def testBadConfigRaises(self):
    conf = config_lib.GrrConfigManager()
    conf.initialized = False
    data = """
Section1.test: 2
"""
    # This config option isn't defined, so it should raise
    with self.assertRaises(config_lib.MissingConfigDefinitionError):
      conf.Initialize(parser=config_lib.YamlParser, data=data)

  @flags.FlagOverrider(disallow_missing_config_definitions=True)
  def testConfigOptionsDefined(self):
    """Test that all config options in use are defined."""
    # We need to use the actual config_lib.CONFIG variable since that is where
    # all the variables are already defined.
    conf = config_lib.CONFIG.MakeNewConfig()

    # Check our actual config validates
    configpath = os.path.normpath(
        os.path.dirname(__file__) + "/../config/grr-server.yaml")
    conf.Initialize(filename=configpath)

  def _DefineStringName(self, conf, name):
    conf.DEFINE_string(name, "", "A test.")

  def testUnbalancedParenthesis(self):
    conf = config_lib.GrrConfigManager()
    name_list = ["Section1.foobar", "Section1.foo", "Section1.foo1",
                 "Section1.foo2", "Section1.foo3", "Section1.foo4",
                 "Section1.foo5", "Section1.foo6", "Section1.interpolation1",
                 "Section1.interpolation2", "Section1.literal"]
    for name in name_list:
      self._DefineStringName(conf, name)

    conf.Initialize(data=r"""
[Section1]
foobar = X
foo = %(Section1.foobar)
foo1 = %(foo

# Unbalanced parenthesis
foo2 = foo)

# Unbalanced parenthesis is ok if escaped.
foo3 = foo\)

# Or if enclosed in a literal block.
foo6 = %{foo)}

foo4 = %{%(hello)}
foo5 = %{hello

# Literal blocks can also appear inside filter interpolations to prevent
# automatic expansions.

# This pull the environment variable "sectionX"
interpolation1 = %(section%(Section1.foobar)|env)

# But this means literally section%(Section1.foo):
interpolation2 = %(section%{%(Section1.foo)}|env)

literal = %{aff4:/C\.(?P<path>.\{1,16\}?)($|/.*)}

""")

    # Test direct access.
    self.assertEqual(conf["Section1.foo"], "X")
    self.assertRaises(config_lib.ConfigFormatError,
                      conf.__getitem__, "Section1.foo1")

    self.assertRaises(config_lib.ConfigFormatError,
                      conf.__getitem__, "Section1.foo2")

    self.assertEqual(conf["Section1.foo3"], "foo)")

    # Test literal expansion.
    self.assertEqual(conf["Section1.foo4"], "%(hello)")

    self.assertRaises(config_lib.ConfigFormatError,
                      conf.__getitem__, "Section1.foo5")

    self.assertEqual(conf["Section1.foo6"], "foo)")

    # The Env filter forces uppercase on args.
    os.environ["sectionX".upper()] = "1"
    os.environ["section%(Section1.foo)".upper()] = "2"

    self.assertEqual(conf["Section1.interpolation1"], "1")
    self.assertEqual(conf["Section1.interpolation2"], "2")

    # Test that Set() escapes - i.e. reading the value back will return exactly
    # the same as we wrote:
    conf.Set("Section1.foo6", "%(Section1.foo3)")
    self.assertEqual(conf["Section1.foo6"], "%(Section1.foo3)")
    self.assertEqual(conf.GetRaw("Section1.foo6"), r"\%(Section1.foo3\)")

    # OTOH when we write it raw, reading it back will interpolate:
    conf.SetRaw("Section1.foo6", "%(Section1.foo3)")
    self.assertEqual(conf["Section1.foo6"], "foo)")

    # A complex regex which gets literally expanded.
    self.assertEqual(
        conf["Section1.literal"], r"aff4:/C\.(?P<path>.{1,16}?)($|/.*)")

  def testDataTypes(self):
    conf = config_lib.GrrConfigManager()
    conf.DEFINE_float("Section1.float", 0, "A float")
    conf.Initialize(parser=config_lib.YamlParser, data="Section1.float: abc")
    errors = conf.Validate("Section1")
    self.assertTrue(
        "Invalid value abc for Float" in str(errors["Section1.float"]))

    self.assertRaises(config_lib.ConfigFormatError, conf.Get, "Section1.float")
    conf.Initialize(parser=config_lib.YamlParser, data="Section1.float: 2")

    # Should have no errors now. Validate should normalize the value to a float.
    self.assertEqual(conf.Validate("Section1"), {})

    self.assertEqual(type(conf.Get("Section1.float")), float)

    conf = config_lib.GrrConfigManager()
    conf.DEFINE_integer("Section1.int", 0, "An integer")
    conf.DEFINE_list("Section1.list", default=[], help="A list")
    conf.DEFINE_list("Section1.list2", default=["a", "2"], help="A list")
    conf.Initialize(parser=config_lib.YamlParser, data="Section1.int: 2.0")

    errors = conf.Validate("Section1")

    # Floats can not be coerced to an int because that will lose data.
    self.assertTrue(
        "Invalid value 2.0 for Integer" in str(errors["Section1.int"]))

    # A string can be coerced to an int if it makes sense:
    conf.Initialize(parser=config_lib.YamlParser, data="Section1.int: '2'")

    errors = conf.Validate("Section1")
    self.assertEqual(type(conf.Get("Section1.int")), long)

    self.assertEqual(type(conf.Get("Section1.list")), list)
    self.assertEqual(conf.Get("Section1.list"), [])

    self.assertEqual(type(conf.Get("Section1.list2")), list)
    self.assertEqual(conf.Get("Section1.list2"), ["a", "2"])

  def _GetNewConf(self):
    conf = config_lib.GrrConfigManager()
    conf.DEFINE_bool("SecondaryFileIncluded", False, "A string")
    conf.DEFINE_bool("TertiaryFileIncluded", False, "A string")
    conf.DEFINE_integer("Section1.int", 0, "An integer")
    return conf

  def _CheckConf(self, conf):
    self.assertTrue(conf.Get("SecondaryFileIncluded"))
    self.assertTrue(conf.Get("TertiaryFileIncluded"))
    self.assertEqual(conf.Get("Section1.int"), 3)

  def testConfigFileInclusion(self):
    one = r"""
ConfigIncludes:
  - 2.yaml

Section1.int: 1
"""
    two = r"""
SecondaryFileIncluded: true
Section1.int: 2
ConfigIncludes:
  - subdir/3.yaml
"""
    three = r"""
TertiaryFileIncluded: true
Section1.int: 3
"""

    with utils.TempDirectory() as temp_dir:
      configone = os.path.join(temp_dir, "1.yaml")
      configtwo = os.path.join(temp_dir, "2.yaml")
      subdir = os.path.join(temp_dir, "subdir")
      os.makedirs(subdir)
      configthree = os.path.join(subdir, "3.yaml")
      with open(configone, "w") as fd:
        fd.write(one)

      with open(configtwo, "w") as fd:
        fd.write(two)

      with open(configthree, "w") as fd:
        fd.write(three)

      # Using filename
      conf = self._GetNewConf()
      conf.Initialize(parser=config_lib.YamlParser, filename=configone)
      self._CheckConf(conf)

      # If we don't get a filename or a handle with a .name we look in the cwd
      # for the specified path, check this works.
      olddir = os.getcwd()
      os.chdir(temp_dir)

      # Using fd with no fd.name
      conf = self._GetNewConf()
      fd = StringIO.StringIO(one)
      conf.Initialize(parser=config_lib.YamlParser, fd=fd)
      self._CheckConf(conf)

      # Using data
      conf = self._GetNewConf()
      conf.Initialize(parser=config_lib.YamlParser, data=one)
      self._CheckConf(conf)
      os.chdir(olddir)

  def testMatchBuildContext(self):
    context = """
Test1 Context:
  Client.labels: [Test1]
  ClientBuilder.target_platforms:
    - linux_amd64_deb
    - linux_i386_deb
    - windows_amd64_exe

Test2 Context:
  Client.labels: [Test2]

Test3 Context:
  Client.labels: [Test3]
  ClientBuilder.target_platforms:
    - linux_amd64_deb
    - windows_i386_exe
"""
    conf = config_lib.CONFIG.MakeNewConfig()
    conf.DEFINE_context("Test1 Context")
    conf.DEFINE_context("Test2 Context")
    conf.DEFINE_context("Test3 Context")
    conf.Initialize(parser=config_lib.YamlParser, data=context)
    orig_context = copy.deepcopy(conf.context)
    config_orig = conf.ExportState()
    conf.AddContext("Test1 Context")
    result_map = [(("linux", "amd64", "deb"), True),
                  (("linux", "i386", "deb"), True),
                  (("windows", "amd64", "exe"), True),
                  (("windows", "i386", "exe"), False)]
    for result in result_map:
      self.assertEqual(conf.MatchBuildContext(*result[0]), result[1])

    conf = config_lib.ImportConfigManger(config_orig)
    self.assertItemsEqual(conf.context, orig_context)
    self.assertFalse("Test1 Context" in conf.context)
    conf.AddContext("Test3 Context")
    result_map = [(("linux", "amd64", "deb"), True),
                  (("linux", "i386", "deb"), False),
                  (("windows", "amd64", "exe"), False),
                  (("windows", "i386", "exe"), True)]
    for result in result_map:
      self.assertEqual(conf.MatchBuildContext(*result[0]), result[1])

    conf = config_lib.ImportConfigManger(config_orig)
    self.assertItemsEqual(conf.context, orig_context)
    self.assertFalse("Test1 Context" in conf.context)
    self.assertFalse("Test3 Context" in conf.context)

  def testMatchBuildContextError(self):
    """Raise because the same target was listed twice."""
    context = """
Test1 Context:
  Client.labels: [Test1]
  ClientBuilder.target_platforms:
    - linux_amd64_deb
    - linux_i386_deb
    - linux_amd64_deb
    - windows_amd64_exe
"""
    conf = config_lib.CONFIG.MakeNewConfig()
    conf.DEFINE_context("Test1 Context")
    conf.Initialize(parser=config_lib.YamlParser, data=context)
    conf.AddContext("Test1 Context")
    with self.assertRaises(type_info.TypeValueError):
      conf.MatchBuildContext("linux", "amd64", "deb")


def main(argv):
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
