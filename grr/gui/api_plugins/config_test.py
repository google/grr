#!/usr/bin/env python
"""This modules contains tests for config API handler."""



import StringIO

from grr.gui import api_test_lib
from grr.gui.api_plugins import config as config_plugin

from grr.lib import config_lib
from grr.lib import flags
from grr.lib import test_lib
from grr.lib import utils


def GetConfigMockClass(sections=None):
  """Mocks a configuration file for use by the API handler.

  Args:
    sections: A dict containing one key per config section
    with a value of a dict containing one key per config parameter name
    and a value of config parameter value. (default {})

  Returns:
    A class to be used as a config mock.
  """

  if sections is None:
    sections = {}

  missing = object()

  type_infos = []
  values = {}
  raw_values = {}
  default_values = {}

  for section_name, section in sections.iteritems():
    for parameter_name, parameter_data in section.iteritems():
      name = "%s.%s" % (section_name, parameter_name)
      descriptor = utils.DataObject(section=section_name, name=name)
      type_infos.append(descriptor)

      if "value" in parameter_data:
        values[name] = parameter_data["value"]

      if "raw_value" in parameter_data:
        raw_values[name] = parameter_data["raw_value"]

      if "default_value" in parameter_data:
        default_values[name] = parameter_data["default_value"]

  def Get(parameter, default=missing):
    try:
      return values[parameter]
    except KeyError:
      if default is missing:
        return default_values[parameter]
      return default

  def GetRaw(parameter, default=missing):
    try:
      return raw_values[parameter]
    except KeyError:
      if default is missing:
        return default_values[parameter]
      return default

  return {"Get": Get, "GetRaw": GetRaw, "type_infos": type_infos}


class ApiGetConfigHandlerTest(test_lib.GRRBaseTest):
  """Test for ApiGetConfigHandlerTest."""

  def setUp(self):
    super(ApiGetConfigHandlerTest, self).setUp()
    self.handler = config_plugin.ApiGetConfigHandler()

  def _ConfigStub(self, sections=None):
    mock = GetConfigMockClass(sections)
    config = config_lib.CONFIG
    return utils.MultiStubber((config, "GetRaw", mock["GetRaw"]),
                              (config, "Get", mock["Get"]),
                              (config, "type_infos", mock["type_infos"]))

  def _RenderConfig(self, sections):
    with self._ConfigStub(sections):
      mock_request = utils.DataObject()
      rendering = self.handler.Render(mock_request)

    return rendering

  def _assertRendersConfig(self, sections, expected_rendering):
    actual_rendering = self._RenderConfig(sections)
    self.assertEquals(actual_rendering, expected_rendering)

  def testRendersEmptyConfig(self):
    self._assertRendersConfig(None, {})

  def testRendersEmptySection(self):
    self._assertRendersConfig({"section": {}}, {})

  def testRendersSetting(self):
    input_dict = {"section": {"parameter": {"value": u"value",
                                            "raw_value": u"value"}}}
    output_dict = {
        "section": {
            "section.parameter": {
                "value": {
                    "age": 0,
                    "type": "unicode",
                    "value": u"value"
                    },
                "is_default": False,
                "is_expanded": False,
                "raw_value": u"value",
                "type": "plain"
                }
            }
        }
    self._assertRendersConfig(input_dict, output_dict)

  def testAlwaysReportsIsDefaultAsFalse(self):
    input_dict = {"section": {"parameter": {"default_value": u"value"}}}
    rendering = self._RenderConfig(input_dict)
    self.assertFalse(rendering["section"]["section.parameter"]["is_default"])

  def testRendersBinary(self):
    input_dict = {"section": {"parameter": {"value": "value\xff",
                                            "raw_value": "value\xff"}}}
    rendering = self._RenderConfig(input_dict)
    self.assertEquals(rendering["section"]["section.parameter"]["type"],
                      "binary")

  def testRendersRedacted(self):
    input_dict = {"Mysql": {"database_password": {"value": u"secret",
                                                  "raw_value": u"secret"}}}
    rendering = self._RenderConfig(input_dict)
    self.assertEquals(rendering["Mysql"]["Mysql.database_password"]["type"],
                      "redacted")

  def testAlwaysReportsIsExpandedAsFalse(self):
    input_dict = {"section": {"parameter": {"value": u"%(answer)",
                                            "raw_value": u"fourty-two"}}}
    rendering = self._RenderConfig(input_dict)
    self.assertFalse(rendering["section"]["section.parameter"]["is_expanded"])

    input_dict = {"section": {"parameter": {"value": u"fourty-two",
                                            "raw_value": u"fourty-two"}}}
    rendering = self._RenderConfig(input_dict)
    self.assertFalse(rendering["section"]["section.parameter"]["is_expanded"])


class ApiGetConfigHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):

  handler = "ApiGetConfigHandler"

  def Run(self):
    config_obj = config_lib.GrrConfigManager()
    config_obj.DEFINE_bool("SectionFoo.sample_boolean_option", True,
                           "Regression test sample boolean option.")
    config_obj.DEFINE_integer("SectionFoo.sample_integer_option", 42,
                              "Sample integer option.")
    config_obj.DEFINE_string("SectionBar.sample_string_option", "",
                             "Sample string option.")
    config_obj.DEFINE_list("SectionBar.sample_list_option", [],
                           "Sample list option.")

    config = """
SectionFoo.sample_boolean_option: True
SectionBar.sample_string_option: "%(sAmPlE|lower)"
"""

    config_lib.LoadConfig(config_obj, StringIO.StringIO(config),
                          parser=config_lib.YamlParser)

    with utils.Stubber(config_lib, "CONFIG", config_obj):
      self.Check("GET", "/api/config")


class ApiGetConfigOptionHandlerTest(test_lib.GRRBaseTest):
  """Test for ApiGetConfigOptionHandler."""

  def setUp(self):
    super(ApiGetConfigOptionHandlerTest, self).setUp()
    self.handler = config_plugin.ApiGetConfigOptionHandler()

  def _ConfigStub(self, sections=None):
    mock = GetConfigMockClass(sections)
    config = config_lib.CONFIG
    return utils.MultiStubber((config, "GetRaw", mock["GetRaw"]),
                              (config, "Get", mock["Get"]),
                              (config, "type_infos", mock["type_infos"]))

  def _RenderConfigOption(self, stub_sections, name):
    with self._ConfigStub(stub_sections):
      rendering = self.handler.Render(
          config_plugin.ApiGetConfigOptionArgs(name=name))

    return rendering

  def testRendersRedacted(self):
    input_dict = {"Mysql": {"database_password": {"value": u"secret",
                                                  "raw_value": u"secret"}}}
    rendering = self._RenderConfigOption(input_dict, "Mysql.database_password")
    self.assertEquals(rendering, dict(status="OK", type="redacted"))


class ApiGetConfigOptionHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):

  handler = "ApiGetConfigOptionHandler"

  def Run(self):
    config_obj = config_lib.GrrConfigManager()
    config_obj.DEFINE_string("SectionFoo.sample_string_option", "",
                             "Sample string option.")
    config_obj.DEFINE_string("Mysql.database_password", "",
                             "Secret password.")

    config = """
SectionBar.sample_string_option: "%(sAmPlE|lower)"
Mysql.database_password: "THIS IS SECRET AND SHOULD NOT BE SEEN"
"""

    config_lib.LoadConfig(config_obj, StringIO.StringIO(config),
                          parser=config_lib.YamlParser)

    with utils.Stubber(config_lib, "CONFIG", config_obj):
      self.Check("GET", "/api/config/SectionFoo.sample_string_option")
      self.Check("GET", "/api/config/Mysql.database_password")
      self.Check("GET", "/api/config/NonExistingOption")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
