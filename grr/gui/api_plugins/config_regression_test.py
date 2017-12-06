#!/usr/bin/env python
"""This modules contains regression tests for config API handler."""


from grr.gui import api_regression_test_lib
from grr.gui.api_plugins import config as config_plugin
from grr.gui.api_plugins import config_test as config_plugin_test

from grr.lib import flags


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


def main(argv):
  api_regression_test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
