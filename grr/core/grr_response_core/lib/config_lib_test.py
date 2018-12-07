#!/usr/bin/env python
"""Tests for config_lib classes."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io
import ntpath
import os
import stat


from past.builtins import long

from grr_response_core import config
from grr_response_core.lib import config_lib
from grr_response_core.lib import flags
from grr_response_core.lib import package
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import type_info
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr.test_lib import test_lib


class YamlConfigTest(test_lib.GRRBaseTest):
  """Test the Yaml config file support."""

  @flags.FlagOverrider(disallow_missing_config_definitions=True)
  def testParsing(self):
    conf = config_lib.GrrConfigManager()

    conf.DEFINE_list("Section1.test_list", ["a", "b"], "A test integer.")
    conf.DEFINE_integer("Section1.test", 0, "An integer")
    conf.DEFINE_integer("Section1.test2", 0, "An integer")
    self.assertRaises(
        config_lib.MissingConfigDefinitionError,
        conf.Initialize,
        parser=config_lib.YamlParser,
        data="""
                      Section2.test: 2
                      """)

    conf.DEFINE_string("Section2.test", "", "A string")
    conf.DEFINE_context("Client Context")
    conf.DEFINE_context("Windows Context")
    conf.Initialize(
        parser=config_lib.YamlParser,
        data="""

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

    self.assertEqual(
        conf.Get(
            "Section1.test_list", context=["Client Context",
                                           "Windows Context"]), ["x", "y"])

    # Test that contexts affect option selection.
    self.assertEqual(conf.Get("Section1.test", context=["Client Context"]), 6)

    self.assertEqual(conf.Get("Section1.test", context=["Windows Context"]), 5)

    context = ["Client Context", "Windows Context"]
    self.assertEqual(conf.Get("Section1.test", context=context), 10)

    context = ["Windows Context", "Client Context"]
    # Order of the context parameters should not matter.
    self.assertEqual(conf.Get("Section1.test", context=context), 10)

  def testConflictingContexts(self):
    """Test that conflicting contexts are resolved by precedence."""
    conf = config_lib.GrrConfigManager()

    conf.DEFINE_integer("Section1.test", 0, "An integer")
    conf.DEFINE_context("Client Context")
    conf.DEFINE_context("Platform:Windows")
    conf.DEFINE_context("Extra Context")
    conf.Initialize(
        parser=config_lib.YamlParser,
        data="""

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
        conf.Get(
            "Section1.test", context=["Client Context", "Platform:Windows"]),
        10)

    self.assertEqual(
        conf.Get(
            "Section1.test", context=["Platform:Windows", "Client Context"]), 6)

  def testRemoveContext(self):
    """Test that conflicting contexts are resolved by precedence."""
    conf = config_lib.GrrConfigManager()

    conf.DEFINE_integer("Section1.test", 0, "An integer")
    conf.DEFINE_integer("Section1.test2", 9, "An integer")
    conf.DEFINE_context("Client Context")
    conf.DEFINE_context("Platform:Windows")
    conf.DEFINE_context("Extra Context")
    conf.Initialize(
        parser=config_lib.YamlParser,
        data="""

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

  def testContextApplied(self):
    conf = config_lib.GrrConfigManager()

    conf.DEFINE_integer("Section1.test", 0, "An integer")
    conf.DEFINE_context("Client Context")
    conf.DEFINE_context("Unused Context")
    conf.Initialize(
        parser=config_lib.YamlParser,
        data="""
Client Context:
  Section1.test: 6
""")

    # Should be defaults, no contexts added
    self.assertFalse(conf.ContextApplied("Client Context"))
    self.assertFalse(conf.ContextApplied("Unused Context"))

    conf.AddContext("Client Context")
    self.assertTrue(conf.ContextApplied("Client Context"))
    self.assertFalse(conf.ContextApplied("Unused Context"))

  def testBackslashes(self):
    conf = config_lib.GrrConfigManager()

    conf.DEFINE_string("Section1.parameter", "", "A test.")
    conf.DEFINE_string("Section1.parameter2", "", "A test.")
    conf.DEFINE_string("Section1.parameter3", "", "A test.")

    conf.Initialize(
        parser=config_lib.YamlParser,
        data=r"""

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

  def testSemanticValueType(self):
    conf = config_lib.GrrConfigManager()
    conf.DEFINE_semantic_value(rdfvalue.Duration, "Section1.foobar", None,
                               "Sample help.")
    conf.Initialize(
        parser=config_lib.YamlParser, data="""
Section1.foobar: 6d
""")

    value = conf.Get("Section1.foobar")
    self.assertIsInstance(value, rdfvalue.Duration)
    self.assertEqual(value, rdfvalue.Duration("6d"))

  def testSemanticStructType(self):
    conf = config_lib.GrrConfigManager()

    conf.DEFINE_semantic_struct(rdf_file_finder.FileFinderArgs,
                                "Section1.foobar", [], "Sample help.")
    conf.Initialize(
        parser=config_lib.YamlParser,
        data="""
Section1.foobar:
  paths:
    - "a/b"
    - "b/c"
  pathtype: "TSK"
""")

    values = conf.Get("Section1.foobar")
    self.assertIsInstance(values, rdf_file_finder.FileFinderArgs)
    self.assertEqual(values.paths, ["a/b", "b/c"])
    self.assertEqual(values.pathtype, "TSK")


class ConfigLibTest(test_lib.GRRBaseTest):
  """Tests for config functionality."""

  def testInit(self):
    """Testing initialization of a ConfigManager."""
    conf = config_lib.GrrConfigManager()
    conf.DEFINE_string("MemoryDriver.device_path", "Default Value", "Help")
    conf.DEFINE_context("Platform:Windows")
    conf.DEFINE_context("Client Context")
    conf.DEFINE_context("Platform:Linux")

    data = r"""
Platform:Linux:
    MemoryDriver.device_path: /dev/pmem

Platform:Windows:
    MemoryDriver.device_path: \\\\.\\pmem
"""

    conf.Initialize(parser=config_lib.YamlParser, data=data)

    # Check that the linux client have a different value from the windows
    # client.
    self.assertEqual(
        conf.Get(
            "MemoryDriver.device_path",
            context=("Client Context", "Platform:Linux")), "/dev/pmem")

    self.assertEqual(
        conf.Get(
            "MemoryDriver.device_path",
            context=("Client Context", "Platform:Windows")), r"\\.\pmem")

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

    new_conf.Initialize(filename=config_file)

    self.assertEqual(new_conf["NewSection1.new_option1"], "New Value1")

  def _SetupConfig(self, value):
    conf = config_lib.GrrConfigManager()
    config_file = os.path.join(self.temp_dir, "config.yaml")
    with open(config_file, "wb") as fd:
      fd.write("Section1.option1: %s" % value)
    conf.DEFINE_string("Section1.option1", "Default Value", "Help")
    conf.Initialize(filename=config_file)
    return conf

  def testPersist(self):
    writeback_file = os.path.join(self.temp_dir, "writeback.yaml")

    conf = self._SetupConfig("Value1")
    conf.SetWriteBack(writeback_file)

    self.assertEqual(conf["Section1.option1"], "Value1")

    conf.Persist("Section1.option1")

    conf = self._SetupConfig("Value2")
    # This should give the persisted value back.
    conf.SetWriteBack(writeback_file)

    self.assertEqual(conf["Section1.option1"], "Value1")

    # Now overwrite the writeback from the config ("Value2").
    conf.Persist("Section1.option1")

    conf = self._SetupConfig("Value3")
    conf.SetWriteBack(writeback_file)

    self.assertEqual(conf["Section1.option1"], "Value2")

    # This new config has the same value as the current writeback file.
    conf = self._SetupConfig("Value2")
    conf.SetWriteBack(writeback_file)

    self.assertEqual(conf["Section1.option1"], "Value2")

    def DontCall():
      raise NotImplementedError("Write was called!")

    # If the value in config and writeback are the same, nothing is written.
    with utils.Stubber(conf, "Write", DontCall):
      conf.Persist("Section1.option1")

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

  def testCopyConfig(self):
    """Check we can copy a config and use it without affecting the old one."""
    conf = config.CONFIG.CopyConfig()
    conf.initialized = False
    conf.DEFINE_string("NewSection1.new_option1", "Default Value", "Help")
    conf.Set("NewSection1.new_option1", "New Value1")
    conf.initialized = True
    conf.Write()
    self.assertEqual(conf.Get("NewSection1.new_option1"), "New Value1")
    self.assertEqual(config.CONFIG.Get("NewSection1.new_option1", None), None)

  def testKeyConfigOptions(self):
    """Check that keys get read correctly from the config."""
    # Clone a test config object from the global config so it knows about Client
    # options.
    conf = config.CONFIG.MakeNewConfig()
    conf.Initialize(data="""
[Client]
private_key = -----BEGIN RSA PRIVATE KEY-----
    MIIBOwIBAAJBAJTrcBYtenHgT23ZVwYTiMPF+XQi+b9f7idy2eD+ELAUOoBK9A+n
    W+WSavIg3cje+yDqd1VjvSo+LGKC+OQkKcsCAwEAAQJALGVsSxBP2rc2ttb+nK8i
    LMtOrRLoReeBhn00+2CC9Rr+Ui8GJxvmgJ16+DObU9xIPPG73bqDdsOOrmTV8Jo4
    8QIhAMQC2siJr+uuKpGODCM1ItJfG2Uaa9eplYj1pBVuztVPAiEAwn8Lluk7ULX6
    SkLzKnsbahInoni6t7SBd/o6hjNsvMUCIQCcUpZ/9udZdAa5HOtrLNZ/pqAniuHV
    FoeOujFJcpz8GwIgSRVYE4LcSP24aQMzQDk2GetsfT6EWtc29xBNwXO9XkkCIQCl
    7o5SVqKx1wHOj8gV3/8WHJ61MvAQCAX4o/M8cGkTQQ==
    -----END RSA PRIVATE KEY-----
executable_signing_public_key = -----BEGIN PUBLIC KEY-----
    MFwwDQYJKoZIhvcNAQEBBQADSwAwSAJBALnfFW1FffeKPs5PLUhFOSkNrr9TDCOD
    QAI3WluLh0sW7/ro93eoIZ0FbipnTpzGkPpriONbSOXmxWNTo0b9ma8CAwEAAQ==
    -----END PUBLIC KEY-----
""")
    errors = conf.Validate(["Client"])
    self.assertEqual(errors, {})
    self.assertIsInstance(conf["Client.executable_signing_public_key"],
                          rdf_crypto.RSAPublicKey)
    self.assertIsInstance(conf["Client.private_key"], rdf_crypto.RSAPrivateKey)

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
    """Test that we can not modify constant values during runtime."""
    conf = config_lib.GrrConfigManager()

    conf.DEFINE_constant_string("Section1.const", "test", "A test string.")

    # We should be able to read this while the config is not initialized.
    self.assertEqual(conf["Section1.const"], "test")

    data = """
[Section1]
const = New string
"""

    # Modifying a constant value in the config file is OK.
    conf.Initialize(data=data)

    # Once the config file is loaded and initialized, modification of constant
    # values is an error.
    self.assertRaises(config_lib.ConstModificationError, conf.Set,
                      "Section1.const", "New string")
    self.assertRaises(config_lib.ConstModificationError, conf.SetRaw,
                      "Section1.const", "New string")

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

  def testBadFilterRaises(self):
    """Checks that bad filter directive raise."""
    conf = config_lib.GrrConfigManager()
    conf.DEFINE_string("Section1.foo6", "%(somefile@somepackage|resource)",
                       "test")
    conf.DEFINE_string("Section1.foo1", "%(Section1.foo6)/bar", "test")
    conf.Initialize(data="")

    with self.assertRaises(config_lib.InterpolationError) as context:
      _ = conf["Section1.foo1"]

    # Make sure the stringified exception explains the full interpolation chain.
    self.assertIn("%(Section1.foo6)/bar", str(context.exception))

  @flags.FlagOverrider(disallow_missing_config_definitions=True)
  def testConfigOptionsDefined(self):
    """Test that all config options in use are defined."""
    # We need to use the actual config.CONFIG variable since that is where
    # all the variables are already defined.
    conf = config.CONFIG.MakeNewConfig()

    # Check our actual config validates
    configpath = package.ResourcePath("grr-response-core",
                                      "install_data/etc/grr-server.yaml")
    conf.Initialize(filename=configpath)

  def _DefineStringName(self, conf, name):
    conf.DEFINE_string(name, "", "A test.")

  def testUnbalancedParenthesis(self):
    conf = config_lib.GrrConfigManager()
    name_list = [
        "Section1.foobar", "Section1.foo", "Section1.foo1", "Section1.foo2",
        "Section1.foo3", "Section1.foo4", "Section1.foo5", "Section1.foo6",
        "Section1.interpolation1", "Section1.interpolation2", "Section1.literal"
    ]
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
    self.assertRaises(config_lib.ConfigFormatError, conf.__getitem__,
                      "Section1.foo1")

    self.assertRaises(config_lib.ConfigFormatError, conf.__getitem__,
                      "Section1.foo2")

    self.assertEqual(conf["Section1.foo3"], "foo)")

    # Test literal expansion.
    self.assertEqual(conf["Section1.foo4"], "%(hello)")

    self.assertRaises(config_lib.ConfigFormatError, conf.__getitem__,
                      "Section1.foo5")

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
    self.assertEqual(conf["Section1.literal"],
                     r"aff4:/C\.(?P<path>.{1,16}?)($|/.*)")

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
    conf.DEFINE_context("Client Context")
    return conf

  def _CheckConf(self, conf):
    self.assertTrue(conf.Get("SecondaryFileIncluded"))
    self.assertTrue(conf.Get("TertiaryFileIncluded"))
    self.assertEqual(conf.Get("Section1.int"), 3)

  def testConfigFileInclusion(self):
    one = r"""
Config.includes:
  - 2.yaml

Section1.int: 1
"""
    two = r"""
SecondaryFileIncluded: true
Section1.int: 2
Config.includes:
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
      with open(configone, "wb") as fd:
        fd.write(one)

      with open(configtwo, "wb") as fd:
        fd.write(two)

      with open(configthree, "wb") as fd:
        fd.write(three)

      # Using filename
      conf = self._GetNewConf()
      conf.Initialize(parser=config_lib.YamlParser, filename=configone)
      self._CheckConf(conf)

      # Using fd with no fd.name should raise because there is no way to resolve
      # the relative path.
      conf = self._GetNewConf()
      fd = io.StringIO(one)
      self.assertRaises(
          config_lib.ConfigFileNotFound,
          conf.Initialize,
          parser=config_lib.YamlParser,
          fd=fd)

      # Using data
      conf = self._GetNewConf()
      self.assertRaises(
          config_lib.ConfigFileNotFound,
          conf.Initialize,
          parser=config_lib.YamlParser,
          data=one)

  def testConfigFileIncludeAbsolutePaths(self):
    one = r"""
Section1.int: 1
"""
    with utils.TempDirectory() as temp_dir:
      configone = os.path.join(temp_dir, "1.yaml")
      with open(configone, "wb") as fd:
        fd.write(one)

      absolute_include = r"""
Config.includes:
  - %s

Section1.int: 2
""" % configone

      conf = self._GetNewConf()
      conf.Initialize(parser=config_lib.YamlParser, data=absolute_include)
      self.assertEqual(conf["Section1.int"], 1)

      relative_include = r"""
Config.includes:
  - 1.yaml

Section1.int: 2
"""
      conf = self._GetNewConf()
      # Can not include a relative path from config without a filename.
      self.assertRaises(
          config_lib.ConfigFileNotFound,
          conf.Initialize,
          parser=config_lib.YamlParser,
          data=relative_include)

      # If we write it to a file it should work though.
      configtwo = os.path.join(temp_dir, "2.yaml")
      with open(configtwo, "wb") as fd:
        fd.write(relative_include)

      conf.Initialize(parser=config_lib.YamlParser, filename=configtwo)
      self.assertEqual(conf["Section1.int"], 1)

  def testConfigFileInclusionWindowsPaths(self):
    one = r"""
Config.includes:
  - 2.yaml

Section1.int: 1
"""
    two = r"""
Section1.int: 2
SecondaryFileIncluded: true
"""
    config_path = "C:\\Windows\\System32\\GRR"

    def MockedWindowsOpen(filename, _=None):
      basename = ntpath.basename(filename)
      dirname = ntpath.dirname(filename)

      # Make sure we only try to open files from this directory.
      if dirname != config_path:
        raise IOError("Tried to open wrong file %s" % filename)

      if basename == "1.yaml":
        return io.StringIO(one)

      if basename == "2.yaml":
        return io.StringIO(two)

      raise IOError("File not found %s" % filename)

    # We need to also use the nt path manipulation modules.
    with utils.MultiStubber((io, "open", MockedWindowsOpen),
                            (os, "path", ntpath)):
      conf = self._GetNewConf()
      conf.Initialize(filename=ntpath.join(config_path, "1.yaml"))
      self.assertEqual(conf["Section1.int"], 2)
      self.assertEqual(conf["SecondaryFileIncluded"], True)

  def testConfigFileInclusionWithContext(self):
    one = r"""
Client Context:
  Config.includes:
    - 2.yaml

Section1.int: 1
"""
    two = r"""
Section1.int: 2
SecondaryFileIncluded: true
"""
    with utils.TempDirectory() as temp_dir:
      configone = os.path.join(temp_dir, "1.yaml")
      configtwo = os.path.join(temp_dir, "2.yaml")
      with open(configone, "wb") as fd:
        fd.write(one)

      with open(configtwo, "wb") as fd:
        fd.write(two)

      # Without specifying the context the includes are not processed.
      conf = self._GetNewConf()
      conf.Initialize(parser=config_lib.YamlParser, filename=configone)
      self.assertEqual(conf["Section1.int"], 1)

      # Only one config is loaded.
      self.assertEqual(conf.files, [configone])

      # Now we specify the context.
      conf = self._GetNewConf()
      conf.AddContext("Client Context")
      conf.Initialize(parser=config_lib.YamlParser, filename=configone)

      # Both config files were loaded. Note that load order is important and
      # well defined.
      self.assertEqual(conf.files, [configone, configtwo])
      self.assertEqual(conf["Section1.int"], 2)

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
    conf = config.CONFIG.MakeNewConfig()
    conf.DEFINE_context("Test1 Context")
    conf.DEFINE_context("Test2 Context")
    conf.DEFINE_context("Test3 Context")
    conf.Initialize(parser=config_lib.YamlParser, data=context)
    conf.AddContext("Test1 Context")
    result_map = [(("linux", "amd64", "deb"), True), (("linux", "i386", "deb"),
                                                      True),
                  (("windows", "amd64", "exe"), True), (("windows", "i386",
                                                         "exe"), False)]
    for result in result_map:
      self.assertEqual(conf.MatchBuildContext(*result[0]), result[1])

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
    conf = config.CONFIG.MakeNewConfig()
    conf.DEFINE_context("Test1 Context")
    conf.Initialize(parser=config_lib.YamlParser, data=context)
    conf.AddContext("Test1 Context")
    with self.assertRaises(type_info.TypeValueError):
      conf.MatchBuildContext("linux", "amd64", "deb")

  def testNoUnicodeWriting(self):
    conf = config.CONFIG.MakeNewConfig()
    config_file = os.path.join(self.temp_dir, "writeback.yaml")
    conf.SetWriteBack(config_file)
    conf.DEFINE_string("NewSection1.new_option1", u"Default Value", "Help")
    conf.Set(unicode("NewSection1.new_option1"), u"New Value1")
    conf.Write()

    data = open(config_file).read()
    self.assertNotIn("!!python/unicode", data)

  def testNoUnicodeReading(self):
    """Check that we can parse yaml files with unicode tags."""
    data = """
Client.labels: [Test1]
!!python/unicode ClientBuilder.target_platforms:
  - linux_amd64_deb
"""
    conf = config.CONFIG.MakeNewConfig()
    conf.Initialize(parser=config_lib.YamlParser, data=data)

  def testRenameOnWritebackFailure(self):
    conf = config.CONFIG.MakeNewConfig()
    writeback_file = os.path.join(self.temp_dir, "writeback.yaml")
    with open(writeback_file, "w") as f:
      f.write("This is a bad line of yaml{[(\n")
      f.close()

    self.assertRaises(AttributeError, conf.SetWriteBack, writeback_file)
    self.assertTrue(os.path.isfile(writeback_file + ".bak"))

  def testNoRenameOfReadProtectedFile(self):
    """Don't rename config files we don't have permission to read."""
    conf = config.CONFIG.MakeNewConfig()
    writeback_file = os.path.join(self.temp_dir, "writeback.yaml")
    with open(writeback_file, "w") as f:
      f.write("...")
      f.close()

    # Remove all permissions except user write.
    os.chmod(writeback_file, stat.S_IWUSR)
    conf.SetWriteBack(writeback_file)

    # File is still in the same place
    self.assertTrue(os.path.isfile(writeback_file))


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
