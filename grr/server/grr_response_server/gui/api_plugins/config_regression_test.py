#!/usr/bin/env python
"""This modules contains regression tests for config API handler."""

from absl import app

from grr_response_core.lib.rdfvalues import config as rdf_config
from grr_response_proto.api import config_pb2 as api_config_pb2
from grr_response_server.gui import api_regression_test_lib
from grr_response_server.gui.api_plugins import config as config_plugin
from grr_response_server.gui.api_plugins import config_test as config_plugin_test
from grr.test_lib import test_lib


class ApiListGrrBinariesHandlerRegressionTest(
    config_plugin_test.ApiGrrBinaryTestMixin,
    api_regression_test_lib.ApiRegressionTest,
):

  api_method = "ListGrrBinaries"
  handler = config_plugin.ApiListGrrBinariesHandler

  def Run(self):
    self.SetUpBinaries()

    self.Check("ListGrrBinaries")


class ApiGetGrrBinaryHandlerRegressionTest(
    config_plugin_test.ApiGrrBinaryTestMixin,
    api_regression_test_lib.ApiRegressionTest,
):

  api_method = "GetGrrBinary"
  handler = config_plugin.ApiGetGrrBinaryHandler

  def Run(self):
    self.SetUpBinaries()

    self.Check(
        "GetGrrBinary",
        args=api_config_pb2.ApiGetGrrBinaryArgs(
            type=api_config_pb2.ApiGrrBinary.Type.PYTHON_HACK, path="test"
        ),
    )
    self.Check(
        "GetGrrBinary",
        args=api_config_pb2.ApiGetGrrBinaryArgs(
            type=api_config_pb2.ApiGrrBinary.Type.EXECUTABLE,
            path="windows/test.exe",
        ),
    )


class ApiGetGrrBinaryBlobHandlerRegressionTest(
    config_plugin_test.ApiGrrBinaryTestMixin,
    api_regression_test_lib.ApiRegressionTest,
):

  api_method = "GetGrrBinaryBlob"
  handler = config_plugin.ApiGetGrrBinaryBlobHandler

  def Run(self):
    self.SetUpBinaries()

    self.Check(
        "GetGrrBinaryBlob",
        args=api_config_pb2.ApiGetGrrBinaryBlobArgs(
            type="PYTHON_HACK", path="test"
        ),
    )
    self.Check(
        "GetGrrBinaryBlob",
        args=api_config_pb2.ApiGetGrrBinaryBlobArgs(
            type="EXECUTABLE", path="windows/test.exe"
        ),
    )


class ApiGetConfigOptionHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
):
  api_method = "GetConfigOption"
  handler = config_plugin.ApiGetConfigOptionHandler

  def Run(self):
    # Test config values of different types. Not all of them are supported in
    # the UI.
    with test_lib.ConfigOverrider({
        "Client.company_name": "Monstros S.A.",
        "AdminUI.hunt_config": rdf_config.AdminUIHuntConfig(
            default_exclude_labels=["oh-oh"],
        ),
        "Source.version_major": 42,
        "Hunt.default_client_rate": 42.0,
        "Email.enable_custom_email_address": True,
        "Cron.disabled_cron_jobs": ["Job1", "Job2"],
        "Server.fleetspeak_last_ping_threshold": "1h",
        "Server.raw_filesystem_access_pathtype": "TSK",
        "ClientBuilder.build_type": "Debug",
        "ClientBuilder.target_platforms": [
            "darwin_amd64_dmg",
            "linux_amd64_deb",
        ],
        "ClientRepacker.output_filename": (
            "%(ClientRepacker.output_basename)%(ClientBuilder.output_extension)"
        ),
        "Mysql.password": "top-secret",
    }):
      self.Check(
          "GetConfigOption",
          args=api_config_pb2.ApiGetConfigOptionArgs(
              name="Client.company_name"
          ),
      )
      self.Check(
          "GetConfigOption",
          args=api_config_pb2.ApiGetConfigOptionArgs(
              name="AdminUI.hunt_config"
          ),
      )
      self.Check(
          "GetConfigOption",
          args=api_config_pb2.ApiGetConfigOptionArgs(
              name="Source.version_major"
          ),
      )
      self.Check(
          "GetConfigOption",
          args=api_config_pb2.ApiGetConfigOptionArgs(
              name="Source.version_major"
          ),
      )
      self.Check(
          "GetConfigOption",
          args=api_config_pb2.ApiGetConfigOptionArgs(
              name="Source.version_major"
          ),
      )
      self.Check(
          "GetConfigOption",
          args=api_config_pb2.ApiGetConfigOptionArgs(
              name="Source.version_major"
          ),
      )
      self.Check(
          "GetConfigOption",
          args=api_config_pb2.ApiGetConfigOptionArgs(
              name="Hunt.default_client_rate"
          ),
      )
      self.Check(
          "GetConfigOption",
          args=api_config_pb2.ApiGetConfigOptionArgs(
              name="Email.enable_custom_email_address"
          ),
      )
      self.Check(
          "GetConfigOption",
          args=api_config_pb2.ApiGetConfigOptionArgs(
              name="Cron.disabled_cron_jobs"
          ),
      )
      self.Check(
          "GetConfigOption",
          args=api_config_pb2.ApiGetConfigOptionArgs(
              name="Server.fleetspeak_last_ping_threshold"
          ),
      )
      self.Check(
          "GetConfigOption",
          args=api_config_pb2.ApiGetConfigOptionArgs(
              name="Server.raw_filesystem_access_pathtype"
          ),
      )
      self.Check(
          "GetConfigOption",
          args=api_config_pb2.ApiGetConfigOptionArgs(
              name="ClientBuilder.build_type"
          ),
      )
      self.Check(
          "GetConfigOption",
          args=api_config_pb2.ApiGetConfigOptionArgs(
              name="ClientBuilder.target_platforms"
          ),
      )
      self.Check(
          "GetConfigOption",
          args=api_config_pb2.ApiGetConfigOptionArgs(
              name="ClientRepacker.output_filename"
          ),
      )
      self.Check(
          "GetConfigOption",
          args=api_config_pb2.ApiGetConfigOptionArgs(name="Mysql.password"),
      )


class ApiGetUiConfigHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
):
  api_method = "GetUiConfig"
  handler = config_plugin.ApiGetUiConfigHandler

  def Run(self):
    self.Check(
        "GetUiConfig",
        args=None,
    )

    with test_lib.ConfigOverrider({
        "AdminUI.hunt_config": rdf_config.AdminUIHuntConfig(
            default_exclude_labels=["oh-oh"],
        ),
        "AdminUI.heading": "test heading",
        "AdminUI.report_url": "test report url",
        "AdminUI.help_url": "test help url",
        "AdminUI.profile_image_url": "test profile image url",
        "Source.version_string": "1.2.3.4",
    }):
      self.Check(
          "GetUiConfig",
          args=None,
      )


def main(argv):
  api_regression_test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
