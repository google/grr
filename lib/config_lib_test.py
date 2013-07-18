#!/usr/bin/env python
"""Tests for config_lib classes."""
import os

from grr.client import conf

from grr.lib import config_lib
from grr.lib import test_lib


class ConfigLibTest(test_lib.GRRBaseTest):
  """Tests for config functionality."""

  def setUp(self):
    super(ConfigLibTest, self).setUp()
    self.conf_file = config_lib.CONFIG["Test.config"]

  def testInit(self):
    """Testing initialization of a ConfigManager."""
    conf = config_lib.GrrConfigManager()
    conf.Initialize(self.conf_file)

    self.assertEquals(conf["MemoryDriverLinux.device_path"],
                      "/dev/pmem")

  def testSet(self):
    """Test setting options."""
    # Test access methods.
    conf = config_lib.GrrConfigManager()
    conf.Initialize(self.conf_file)

    conf.Set("NewSection1.new_option1", "New Value1")

    self.assertEquals(conf["NewSection1.new_option1"], "New Value1")

    self.assertTrue("NewSection1" in conf.GetSections())

  def testSave(self):
    """Save the config and ensure it still works."""
    conf = config_lib.GrrConfigManager()
    conf.Initialize(self.config_file)
    conf.Set("NewSection1.new_option1", "New Value1")

    conf.Write()

    new_conf = config_lib.GrrConfigManager()
    new_conf.Initialize(self.config_file)

    self.assertEquals(new_conf["NewSection1.new_option1"], "New Value1")

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
    self.assertRaises(config_lib.ConfigFormatError,
                      conf.Validate, ["Section1.test"])

  def testEmptyClientPrivateKey(self):
    """Check an empty client private_key passes."""
    conf = config_lib.GrrConfigManager()
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
    self.assertEqual(errors.keys(), ["Client.private_key"])

  def testEmptyClientKeys(self):
    """Check an empty other keys fail."""
    conf = config_lib.GrrConfigManager()
    conf.Initialize(data="""
[Client]
private_key =
driver_signing_public_key =
executable_signing_public_key =
""")
    errors = conf.Validate(["Client"])
    self.assertItemsEqual(errors.keys(),
                          ["Client.private_key",
                           "Client.driver_signing_public_key",
                           "Client.executable_signing_public_key"])

  def testAddOption(self):
    """Test that we can add options."""
    conf = config_lib.GrrConfigManager()

    # The default os is Linux which should read from SectionLinux.
    conf.DEFINE_string("Environment.os", "Linux",
                       "A parameter set by the environment.")

    conf.DEFINE_string("Environment.filename", "",
                       "Filename set by the environment.")

    conf.DEFINE_string("Section1.foobar", "test", "A test string.")
    conf.DEFINE_string("Section1.test", "test", "A test string.")

    conf.DEFINE_string("Section1.interpolated", "", "An interpolated string.")

    # This entry is not correct - the default is invalid.
    conf.DEFINE_integer("Section1.test_int", "string", "A test integer.")

    # The default value is invalid.
    self.assertRaises(config_lib.Error, conf.Validate, ["Section1"])

    conf.DEFINE_string("Section1.system", None, "The basic operating system.")
    conf.DEFINE_integer("Section1.test_int", 54, "A test integer.")
    conf.DEFINE_list("Section1.test_list", ["a", "b"], "A test integer.")
    conf.DEFINE_list("Section1.test_list2", ["a", "b"], "A test integer.")

    conf.Initialize(data="""
[Section1]
foobar = X

# This uses the environment variable to select the correct configuration section
# to use.
system = %(Section%(Environment.os).system)
test_list = x,y

[Section2]
@inherit_from_section = Section1
test_int = 34
interpolated = %(Section1.foobar)Y

[Section3]
@inherit_from_section = Section2
test_int = 1
interpolated = %(%(Section1.foobar)|lower)Y

[SectionWindows]
@inherit_from_section = Section1
system = Windows
interpolated = %(%(Environment.filename)|file)

[SectionLinux]
@inherit_from_section = Section1
system = Linux
interpolated = %(system)

""")

    # Section not specified:
    self.assertRaises(RuntimeError, conf.__getitem__, "a")

    # Test direct access.
    self.assertEquals(conf["Section1.foobar"], "X")
    self.assertEquals(conf["Section1.test_list"], ["x", "y"])
    self.assertEquals(conf["Section1.test_list2"], ["a", "b"])

    # Test default access.
    self.assertEquals(conf["Section1.test"], "test")

    # Test section inheritance access.
    self.assertEquals(conf["Section2.test"], "test")
    self.assertEquals(conf["Section2.foobar"], "X")

    # Test interpolation with full section name.
    self.assertEquals(conf["Section2.interpolated"], "XY")

    # Check that default values are typed.
    self.assertEquals(conf["Section1.test_int"], 54)

    # Check that default values are parsed from string. Note that the type of
    # this inferred by inheritance.
    self.assertEquals(conf["Section2.test_int"], 34)
    self.assertEquals(conf["Section3.test_int"], 1)

    # Test filter functions.
    self.assertEquals(conf["Section3.interpolated"], "xY")

    # If the interpolated parameter does not contain a section name, it refers
    # to the current section.
    self.assertEquals(conf["SectionLinux.interpolated"], "Linux")

    # Check that the environment influences the section selection. The default
    # Environment.os is Linux which forces the Section1.system property to be
    # read from the SectionLinux section.
    self.assertEquals(conf["Environment.os"], "Linux")
    self.assertEquals(conf["Section1.system"], "Linux")

    # If the environment is modified however, the Section1.system parameter is
    # read from the SectionWindows section.
    conf.SetEnv(Environment=dict(os="Windows", filename=__file__))
    self.assertEquals(conf["Environment.os"], "Windows")
    self.assertEquals(conf["Section1.system"], "Windows")

    # Test the file filter. This reads the current file into the interpolated
    # parameter.
    self.assertEquals(conf["Environment.filename"], __file__)
    self.assertEquals(conf["SectionWindows.interpolated"],
                      open(__file__, "rb").read())

  def testSectionOverriding(self):
    conf = config_lib.GrrConfigManager()

    conf.DEFINE_string("Section1.foobar", "test", "A test string.")

    conf.Initialize(data="""
[Section1]
foobar = X

[OverridingSection]
Section1.foobar = Y
""")

    # Test direct access.
    self.assertEquals(conf["Section1.foobar"], "X")

    # Now execute the OverridingSection:
    conf.ExecuteSection("OverridingSection")

    self.assertEquals(conf["Section1.foobar"], "Y")

  def testUnbalancedParenthesis(self):
    conf = config_lib.GrrConfigManager()
    conf.Initialize(data=r"""
[Section1]
foobar = X
foo = %(foobar)
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
interpolation1 = %(section%(foobar)|env)

# But this means literally section%(foo):
interpolation2 = %(section%{%(foo)}|env)

[Execute]
Section1.foo4! = %(Section1.foobar)
Section1.foo5 = %(Section1.foobar)
""")

    # Test direct access.
    self.assertEquals(conf["Section1.foo"], "X")
    self.assertRaises(config_lib.ConfigFormatError,
                      conf.__getitem__, "Section1.foo1")

    self.assertRaises(config_lib.ConfigFormatError,
                      conf.__getitem__, "Section1.foo2")

    self.assertEquals(conf["Section1.foo3"], "foo)")

    # Test literal expansion.
    self.assertEquals(conf["Section1.foo4"], "%(hello)")

    self.assertRaises(config_lib.ConfigFormatError,
                      conf.__getitem__, "Section1.foo5")

    self.assertEquals(conf["Section1.foo6"], "foo)")

    # The Env filter forces uppercase on args.
    os.environ["sectionX".upper()] = "1"
    os.environ["section%(foo)".upper()] = "2"

    self.assertEquals(conf["Section1.interpolation1"], "1")
    self.assertEquals(conf["Section1.interpolation2"], "2")

    # Test that Set() escapes - i.e. reading the value back will return exactly
    # the same as we wrote:
    conf.Set("Section1.foo6", "%(Section1.foo3)")
    self.assertEquals(conf["Section1.foo6"], "%(Section1.foo3)")
    self.assertEquals(conf.GetRaw("Section1.foo6"), r"\%(Section1.foo3\)")

    # OTOH when we write it raw, reading it back will interpolate:
    conf.SetRaw("Section1.foo6", "%(Section1.foo3)")
    self.assertEquals(conf["Section1.foo6"], "foo)")

    # This affects execution of sections:
    conf.ExecuteSection("Execute")
    # The raw value in Section1.foo5 has already been interpolated when the
    # Execute section was executed.
    self.assertEquals(conf.GetRaw("Section1.foo5"), "X")

    # However, parameters which end with ! are not evaluated at execution time -
    # they are written raw to their sections.
    self.assertEquals(conf.GetRaw("Section1.foo4"), "%(Section1.foobar)")


def main(argv):
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  conf.StartMain(main)
