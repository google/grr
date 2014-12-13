#!/usr/bin/env python
"""This modules contains tests for config API renderer."""



# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.gui.api_plugins import config as config_plugin

from grr.lib import config_lib
from grr.lib import flags
from grr.lib import test_lib
from grr.lib import utils


def GetConfigMockClass(sections=None):
  """Mocks a configuration file for use by the API renderer.

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

  class ConfigMock(object):
    type_infos = []
    option_values = {}
    raw_values = {}
    default_values = {}

    def __init__(self):
      for section_name, section in sections.iteritems():
        for parameter_name, parameter_data in section.iteritems():
          name = "%s.%s" % (section_name, parameter_name)
          descriptor = utils.DataObject(section=section_name, name=name)
          self.type_infos.append(descriptor)

          if "option_value" in parameter_data:
            self.option_values[name] = parameter_data["option_value"]

          if "raw_value" in parameter_data:
            self.raw_values[name] = parameter_data["raw_value"]

          if "default_value" in parameter_data:
            self.default_values[name] = parameter_data["default_value"]

    def Get(self, parameter, default=missing):
      try:
        return self.option_values[parameter]
      except KeyError:
        if default is missing:
          return self.default_values[parameter]
        return default

    def GetRaw(self, parameter, default=missing):
      try:
        return self.raw_values[parameter]
      except KeyError:
        if default is missing:
          return self.default_values[parameter]
        return default

  return ConfigMock()


class ApiConfigRendererTest(test_lib.GRRBaseTest):
  """Test for ApiConfigRendererTest."""

  def setUp(self):
    super(ApiConfigRendererTest, self).setUp()
    self.renderer = config_plugin.ApiConfigRenderer()

  def _ConfigStub(self, sections=None):
    return utils.Stubber(config_lib,
                         "CONFIG",
                         GetConfigMockClass(sections))

  def _RenderConfig(self, sections):
    with self._ConfigStub(sections):
      mock_request = utils.DataObject()
      rendering = self.renderer.Render(mock_request)

    return rendering

  def _assertRendersConfig(self, sections, expected_rendering):
    actual_rendering = self._RenderConfig(sections)
    self.assertEquals(actual_rendering, expected_rendering)

  def testRendersEmptyConfig(self):
    self._assertRendersConfig(None, {})

  def testRendersEmptySection(self):
    self._assertRendersConfig({"section": {}}, {})

  def testRendersSetting(self):
    input_dict = {"section": {"parameter": {"option_value": "value",
                                            "raw_value": "value"}}}
    output_dict = {"section": {"section.parameter": {"option_value": "value",
                                                     "is_default": False,
                                                     "raw_value": "value",
                                                     "type": "plain"}}}
    self._assertRendersConfig(input_dict, output_dict)

  def testRendersDefault(self):
    input_dict = {"section": {"parameter": {"default_value": "value"}}}
    rendering = self._RenderConfig(input_dict)
    self.assertTrue(rendering["section"]["section.parameter"]["is_default"])

  def testRendersBinary(self):
    input_dict = {"section": {"parameter": {"option_value": "value\xff",
                                            "raw_value": "value\xff"}}}
    rendering = self._RenderConfig(input_dict)
    self.assertEquals(rendering["section"]["section.parameter"]["type"],
                      "binary")

  def testRendersRedacted(self):
    input_dict = {"Mysql": {"database_password": {"option_value": "secret",
                                                  "raw_value": "secret"}}}
    rendering = self._RenderConfig(input_dict)
    self.assertEquals(rendering["Mysql"]["Mysql.database_password"]["type"],
                      "redacted")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
