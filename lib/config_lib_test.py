#!/usr/bin/env python
"""Tests for config_lib classes."""

import ConfigParser
import os
import StringIO
import unittest


from grr.client import conf
from grr.client import conf as flags
from grr.lib import config_lib
from grr.lib import test_lib


FLAGS = flags.FLAGS


class ConfigLibTest(test_lib.GRRBaseTest):
  """Tests for config functionality."""

  def setUp(self):
    super(ConfigLibTest, self).setUp()
    self.conf_file = os.path.join(FLAGS.test_srcdir, FLAGS.test_config)

  def testInit(self):
    """Testing initialization of a ConfigManager."""
    conf = config_lib.ConfigManager()
    opened = conf.Initialize(self.conf_file)
    self.assertEquals(len(opened), 1)

    self.assertTrue(conf.has_section("ServerFlags"))
    self.assertFalse(conf.has_section("serverflags"))

  def testSet(self):
    """Test setting options."""
    # Test access methods.
    conf = config_lib.ConfigManager()
    conf.Initialize(self.conf_file)
    conf.add_section("NewSection1")
    conf.set("NewSection1", "new_option1", "New Value1")

    self.assertEquals(conf["NewSection1.new_option1"], "New Value1")
    self.assertEquals(conf.get("NewSection1", "new_option1"), "New Value1")

    # Test case sensitivity. Sections are sensitive, options not.
    self.assertRaises(ConfigParser.NoSectionError,
                      conf.__getitem__, "newSection1.new_option1")
    self.assertEquals(conf.get("NewSection1", "NEW_option1"), "New Value1")

  def testSave(self):
    """Save the config and ensure it still works."""
    conf = config_lib.ConfigManager()
    conf.Initialize(self.conf_file)
    conf.add_section("NewSection1")
    conf.set("NewSection1", "new_option1", "New Value1")

    output_fd = StringIO.StringIO()
    conf.write(output_fd)
    output_fd.seek(0)

    new_conf = config_lib.ConfigManager()
    new_conf.readfp(output_fd)

    self.assertEquals(new_conf["NewSection1.New_Option1"], "New Value1")

  def testFallThroughSections(self):
    """Test OS specific fallthrough sections."""

    test_conf = StringIO.StringIO("""
[TestSection]
test_val = val1

[InheritedSection]
@inherit_from_section = TestSection
""")
    conf = config_lib.ConfigManager()
    conf.InitializeFromFileObject(test_conf)

    self.assertEquals(conf["TestSection.test_val"], "val1")
    self.assertEquals(conf["InheritedSection.test_val"], "val1")

    conf["InheritedSection.test_val"] = "val2"
    self.assertEquals(conf["InheritedSection.test_val"], "val2")

  def testFormating(self):
    test_conf = StringIO.StringIO("""
[ClientSigningKeysWindows_]
Test = val2""")
    conf = config_lib.ConfigManager()
    self.assertRaises(config_lib.ConfigFormatError,
                      conf.InitializeFromFileObject, test_conf)

    conf.add_section("clientsigningkeys")
    self.assertRaises(config_lib.ConfigFormatError, conf.Validate)


def main(_):
  unittest.main()

if __name__ == "__main__":
  conf.StartMain(main)
