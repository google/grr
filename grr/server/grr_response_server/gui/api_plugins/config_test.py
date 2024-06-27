#!/usr/bin/env python
"""This modules contains tests for config API handler."""

from unittest import mock

from absl import app

from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import config as rdf_config
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server import maintenance_utils
from grr_response_server import signed_binary_utils
from grr_response_server.gui import api_test_lib
from grr_response_server.gui.api_plugins import config as config_plugin
from grr.test_lib import test_lib


def GetConfigMockClass(sections=None):
  """Mocks a configuration file for use by the API handler.

  Args:
    sections: A dict containing one key per config section with a value of a
      dict containing one key per config parameter name and a value of config
      parameter value. (default {})

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

  for section_name, section in sections.items():
    for parameter_name, parameter_data in section.items():
      name = "%s.%s" % (section_name, parameter_name)

      descriptor = mock.MagicMock()
      descriptor.section = section_name
      descriptor.name = name
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


class ApiGetConfigHandlerTest(api_test_lib.ApiCallHandlerTest):
  """Test for ApiGetConfigHandlerTest."""

  def setUp(self):
    super().setUp()
    self.handler = config_plugin.ApiGetConfigHandler()

  def _ConfigStub(self, sections=None):
    mock_config = GetConfigMockClass(sections)
    return utils.MultiStubber(
        (config.CONFIG, "GetRaw", mock_config["GetRaw"]),
        (config.CONFIG, "Get", mock_config["Get"]),
        (config.CONFIG, "type_infos", mock_config["type_infos"]),
    )

  def _HandleConfig(self, sections):
    with self._ConfigStub(sections):
      request = mock.MagicMock()
      result = self.handler.Handle(request)

    return result

  def _assertHandlesConfig(self, sections, expected_result):
    actual_result = self._HandleConfig(sections)
    self.assertEqual(actual_result, expected_result)

  def testHandlesEmptyConfig(self):
    self._assertHandlesConfig(None, config_plugin.ApiGetConfigResult())

  def testHandlesEmptySection(self):
    self._assertHandlesConfig(
        {"section": {}}, config_plugin.ApiGetConfigResult()
    )

  def testHandlesConfigOption(self):
    input_dict = {
        "section": {"parameter": {"value": "value", "raw_value": "value"}}
    }
    result = self._HandleConfig(input_dict)
    self.assertLen(result.sections, 1)
    self.assertLen(result.sections[0].options, 1)
    self.assertEqual(result.sections[0].options[0].name, "section.parameter")
    self.assertEqual(result.sections[0].options[0].value, "value")

  def testRendersRedacted(self):
    input_dict = {
        "Mysql": {
            "database_password": {"value": "secret", "raw_value": "secret"}
        }
    }
    result = self._HandleConfig(input_dict)
    self.assertTrue(result.sections[0].options[0].is_redacted)


class ApiGetConfigOptionHandlerTest(api_test_lib.ApiCallHandlerTest):
  """Test for ApiGetConfigOptionHandler."""

  def setUp(self):
    super().setUp()
    self.handler = config_plugin.ApiGetConfigOptionHandler()

  def _ConfigStub(self, sections=None):
    mock_config = GetConfigMockClass(sections)
    return utils.MultiStubber(
        (config.CONFIG, "GetRaw", mock_config["GetRaw"]),
        (config.CONFIG, "Get", mock_config["Get"]),
        (config.CONFIG, "type_infos", mock_config["type_infos"]),
    )

  def _HandleConfigOption(self, stub_sections, name):
    with self._ConfigStub(stub_sections):
      result = self.handler.Handle(
          config_plugin.ApiGetConfigOptionArgs(name=name)
      )

    return result

  def testRendersRedacted(self):
    input_dict = {
        "Mysql": {"password": {"value": "secret", "raw_value": "secret"}}
    }
    result = self._HandleConfigOption(input_dict, "Mysql.password")
    self.assertEqual(result.name, "Mysql.password")
    self.assertTrue(result.is_redacted)

  def testRendersRDFStruct(self):
    hunt_cfg = rdf_config.AdminUIHuntConfig(
        default_include_labels=["include"],
        make_default_exclude_labels_a_presubmit_check=True,
    )
    with test_lib.ConfigOverrider({"AdminUI.hunt_config": hunt_cfg}):
      result = self.handler.Handle(
          config_plugin.ApiGetConfigOptionArgs(name="AdminUI.hunt_config")
      )
    self.assertEqual(result.name, "AdminUI.hunt_config")
    self.assertEqual(result.type, "AdminUIHuntConfig")
    self.assertEqual(result.value.default_include_labels, ["include"])
    self.assertTrue(result.value.make_default_exclude_labels_a_presubmit_check)

  def testRendersRDFString(self):
    with test_lib.ConfigOverrider({"Logging.domain": "localhost"}):
      result = self.handler.Handle(
          config_plugin.ApiGetConfigOptionArgs(name="Logging.domain")
      )
    self.assertEqual(result.name, "Logging.domain")
    self.assertEqual(result.type, "RDFString")
    self.assertEqual(result.value, "localhost")

  def testRendersRDFStringFakeList(self):
    with test_lib.ConfigOverrider(
        {"AdminUI.new_flow_form.default_output_plugins": "Dummy1,Dummy2"}
    ):
      result = self.handler.Handle(
          config_plugin.ApiGetConfigOptionArgs(
              name="AdminUI.new_flow_form.default_output_plugins"
          )
      )
    self.assertEqual(
        result.name, "AdminUI.new_flow_form.default_output_plugins"
    )
    self.assertEqual(result.type, "RDFString")
    self.assertEqual(result.value, "Dummy1,Dummy2")

  def testRendersInt(self):
    with test_lib.ConfigOverrider({"Source.version_major": 42}):
      result = self.handler.Handle(
          config_plugin.ApiGetConfigOptionArgs(name="Source.version_major")
      )
    self.assertEqual(result.name, "Source.version_major")
    self.assertEqual(result.type, "RDFInteger")
    self.assertEqual(result.value, 42)

  def testRendersFakeFloat(self):
    with test_lib.ConfigOverrider({"Hunt.default_client_rate": 42.0}):
      result = self.handler.Handle(
          config_plugin.ApiGetConfigOptionArgs(name="Hunt.default_client_rate")
      )
    self.assertEqual(result.name, "Hunt.default_client_rate")
    self.assertEqual(result.type, "RDFInteger")
    self.assertEqual(result.value, 42)

  def testRendersBool(self):
    with test_lib.ConfigOverrider({"Email.enable_custom_email_address": True}):
      result = self.handler.Handle(
          config_plugin.ApiGetConfigOptionArgs(
              name="Email.enable_custom_email_address"
          )
      )
    self.assertEqual(result.name, "Email.enable_custom_email_address")
    # This is a bug, the type should be "bool".
    self.assertEqual(result.type, "RDFInteger")
    self.assertTrue(result.value)

  def testRendersList(self):
    with test_lib.ConfigOverrider(
        {"Cron.disabled_cron_jobs": ["Job1", "Job2"]}
    ):
      result = self.handler.Handle(
          config_plugin.ApiGetConfigOptionArgs(name="Cron.disabled_cron_jobs")
      )
    self.assertEqual(result.name, "Cron.disabled_cron_jobs")
    # We don't support lists in the API.
    self.assertTrue(result.is_invalid)

  def testRendersRDFDuration(self):
    with test_lib.ConfigOverrider(
        {"Server.fleetspeak_last_ping_threshold": "1h"}
    ):
      result = self.handler.Handle(
          config_plugin.ApiGetConfigOptionArgs(
              name="Server.fleetspeak_last_ping_threshold"
          )
      )
    self.assertEqual(result.name, "Server.fleetspeak_last_ping_threshold")
    self.assertEqual(result.type, "Duration")
    self.assertEqual(result.value, rdfvalue.Duration("1h"))

  def testRendersRDFEnum(self):
    with test_lib.ConfigOverrider(
        {"Server.raw_filesystem_access_pathtype": "TSK"}
    ):
      result = self.handler.Handle(
          config_plugin.ApiGetConfigOptionArgs(
              name="Server.raw_filesystem_access_pathtype"
          )
      )
    self.assertEqual(result.name, "Server.raw_filesystem_access_pathtype")
    self.assertEqual(result.type, "EnumNamedValue")
    self.assertEqual(result.value, rdf_paths.PathSpec.PathType.TSK)

  def testRendersChoice(self):
    with test_lib.ConfigOverrider({"ClientBuilder.build_type": "Debug"}):
      result = self.handler.Handle(
          config_plugin.ApiGetConfigOptionArgs(name="ClientBuilder.build_type")
      )
    self.assertEqual(result.name, "ClientBuilder.build_type")
    self.assertEqual(result.type, "RDFString")
    self.assertEqual(result.value, "Debug")

  def testRendersMultiChoice(self):
    with test_lib.ConfigOverrider({
        "ClientBuilder.target_platforms": [
            "darwin_amd64_dmg",
            "linux_amd64_deb",
        ]
    }):
      result = self.handler.Handle(
          config_plugin.ApiGetConfigOptionArgs(
              name="ClientBuilder.target_platforms"
          )
      )
    self.assertEqual(result.name, "ClientBuilder.target_platforms")
    # We don't support lists in the API.
    self.assertTrue(result.is_invalid)

  def testRendersOption(self):
    with test_lib.ConfigOverrider({
        "ClientRepacker.output_filename": (
            "%(ClientRepacker.output_basename)%(ClientBuilder.output_extension)"
        )
    }):
      result = self.handler.Handle(
          config_plugin.ApiGetConfigOptionArgs(
              name="ClientRepacker.output_filename"
          )
      )
    self.assertEqual(result.name, "ClientRepacker.output_filename")
    self.assertEqual(result.type, "RDFString")
    self.assertEqual(result.value, "GRR_0.0.0.0_")


class ApiGrrBinaryTestMixin(object):
  """Mixing providing GRR binaries test setup routine."""

  def SetUpBinaries(self):
    with test_lib.FakeTime(42):
      code = "I am a binary file"
      upload_path = signed_binary_utils.GetAFF4ExecutablesRoot().Add(
          "windows/test.exe"
      )
      maintenance_utils.UploadSignedConfigBlob(
          code.encode("utf-8"), aff4_path=upload_path
      )

    with test_lib.FakeTime(43):
      code = "I'm a python hack"
      upload_path = signed_binary_utils.GetAFF4PythonHackRoot().Add("test")
      maintenance_utils.UploadSignedConfigBlob(
          code.encode("utf-8"), aff4_path=upload_path
      )


class ApiGetUiConfigHandlerTest(api_test_lib.ApiCallHandlerTest):
  """Test for ApiGetUiConfigHandler."""

  def testHandlesConfigOption(self):
    input_dict = {
        "AdminUI.heading": "test heading",
        "AdminUI.report_url": "test report url",
        "AdminUI.help_url": "test help url",
        "AdminUI.profile_image_url": "test profile image url",
        "Source.version_string": "1.2.3.4",
        "Hunt.default_client_rate": 123,
    }

    with test_lib.ConfigOverrider(input_dict):
      request = mock.MagicMock()
      result = config_plugin.ApiGetUiConfigHandler().Handle(request)

    self.assertEqual(result.heading, "test heading")
    self.assertEqual(result.report_url, "test report url")
    self.assertEqual(result.help_url, "test help url")
    self.assertEqual(result.grr_version, "1.2.3.4")
    self.assertEqual(result.profile_image_url, "test profile image url")
    self.assertEqual(result.default_hunt_runner_args.client_rate, 123)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
