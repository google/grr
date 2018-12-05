#!/usr/bin/env python
"""This modules contains regression tests for config API handler."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import flags
from grr_response_server.gui import api_regression_test_lib
from grr_response_server.gui.api_plugins import config as config_plugin

from grr_response_server.gui.api_plugins import config_test as config_plugin_test


class ApiListGrrBinariesHandlerRegressionTest(
    config_plugin_test.ApiGrrBinaryTestMixin,
    api_regression_test_lib.ApiRegressionTest):

  api_method = "ListGrrBinaries"
  handler = config_plugin.ApiListGrrBinariesHandler

  def Run(self):
    self.SetUpBinaries()

    self.Check("ListGrrBinaries")


class ApiGetGrrBinaryHandlerRegressionTest(
    config_plugin_test.ApiGrrBinaryTestMixin,
    api_regression_test_lib.ApiRegressionTest):

  api_method = "GetGrrBinary"
  handler = config_plugin.ApiGetGrrBinaryHandler

  def Run(self):
    self.SetUpBinaries()

    self.Check(
        "GetGrrBinary",
        args=config_plugin.ApiGetGrrBinaryArgs(type="PYTHON_HACK", path="test"))
    self.Check(
        "GetGrrBinary",
        args=config_plugin.ApiGetGrrBinaryArgs(
            type="EXECUTABLE", path="windows/test.exe"))


class ApiGetGrrBinaryBlobHandlerRegressionTest(
    config_plugin_test.ApiGrrBinaryTestMixin,
    api_regression_test_lib.ApiRegressionTest):

  api_method = "GetGrrBinaryBlob"
  handler = config_plugin.ApiGetGrrBinaryBlobHandler

  def Run(self):
    self.SetUpBinaries()

    self.Check(
        "GetGrrBinaryBlob",
        args=config_plugin.ApiGetGrrBinaryBlobArgs(
            type="PYTHON_HACK", path="test"))
    self.Check(
        "GetGrrBinaryBlob",
        args=config_plugin.ApiGetGrrBinaryBlobArgs(
            type="EXECUTABLE", path="windows/test.exe"))


def main(argv):
  api_regression_test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
