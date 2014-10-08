#!/usr/bin/env python
"""Tests for config_lib classes."""
import os

from grr.lib import config_lib
from grr.lib import flags
from grr.lib import test_lib


class YamlConfigTest(test_lib.GRRBaseTest):
  """Test the Yaml config file support."""

  def testParsing(self):
    conf = config_lib.GrrConfigManager()

    conf.DEFINE_list("Section1.test_list", ["a", "b"], "A test integer.")
    conf.DEFINE_integer("Section1.test", 0, "An integer")
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
                              context=("Client", "Platform:Linux")),
                     "/dev/pmem")

    self.assertEqual(conf.Get("MemoryDriver.device_path",
                              context=("Client", "Platform:Windows")),
                     r"\\.\pmem")

  def testSet(self):
    """Test setting options."""
    # Test access methods.
    conf = config_lib.GrrConfigManager()
    conf.DEFINE_string("NewSection1.new_option1", "Default Value", "Help")

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
certificate =
""")
    errors = conf.Validate(["Client"])
    self.assertItemsEqual(errors.keys(),
                          ["Client.driver_signing_public_key",
                           "Client.executable_signing_public_key"])

  def testAddOption(self):
    """Test that we can add options."""
    conf = config_lib.GrrConfigManager()

    conf.DEFINE_string("Section1.foobar", "test", "A test string.")
    conf.DEFINE_string("Section1.test", "test", "A test string.")

    conf.DEFINE_string("Section1.interpolated", "", "An interpolated string.")

    # This entry is not correct - the default is invalid.
    conf.DEFINE_integer("Section1.test_int", "string", "A test integer.")

    # The default value is invalid.
    errors = conf.Validate("Section1")
    self.assertTrue(
        "Invalid value string for Integer" in str(errors["Section1.test_int"]))

    conf.DEFINE_string("Section1.system", None, "The basic operating system.")
    conf.DEFINE_integer("Section1.test_int", 54, "A test integer.")
    conf.DEFINE_list("Section1.test_list", ["a", "b"], "A test integer.")
    conf.DEFINE_list("Section1.test_list2", ["a", "b"], "A test integer.")

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

  def testUnbalancedParenthesis(self):
    conf = config_lib.GrrConfigManager()
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

    conf.DEFINE_integer("Section1.int", 0, "An integer")
    conf.Initialize(parser=config_lib.YamlParser, data="Section1.int: 2.0")

    errors = conf.Validate("Section1")

    # Floats can not be coerced to an int because that will lose data.
    self.assertTrue(
        "Invalid value 2.0 for Integer" in str(errors["Section1.int"]))

    # A string can be coerced to an int if it makes sense:
    conf.Initialize(parser=config_lib.YamlParser, data="Section1.int: '2'")

    errors = conf.Validate("Section1")
    self.assertEqual(type(conf.Get("Section1.int")), long)

    conf.DEFINE_list("Section1.list", default=[], help="A list")
    self.assertEqual(type(conf.Get("Section1.list")), list)
    self.assertEqual(conf.Get("Section1.list"), [])

    conf.DEFINE_list("Section1.list2", default=["a", "2"], help="A list")
    self.assertEqual(type(conf.Get("Section1.list2")), list)
    self.assertEqual(conf.Get("Section1.list2"), ["a", "2"])


def main(argv):
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
