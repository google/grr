#!/usr/bin/env python
"""This modules contains regression tests for config API handler."""



from grr.gui import api_regression_test_lib
from grr.gui.api_plugins import config as config_plugin
from grr.gui.api_plugins import config_test as config_plugin_test

from grr.lib import flags
from grr.lib import utils


class ApiListGrrBinariesHandlerRegressionTest(
    config_plugin_test.ApiGrrBinaryTestMixin,
    api_regression_test_lib.ApiRegressionTest):

  api_method = "ListGrrBinaries"
  handler = config_plugin.ApiListGrrBinariesHandler

  def Run(self):
    summary = self.SetUpBinaries()
    blob_fd = self.GetBinaryBlob(summary)

    self.Check(
        "ListGrrBinaries",
        # Size of the ciphered blob depends on a number of factors,
        # including the random number generator. To avoid test flakiness,
        # it's better to substitute it with a predefined number.
        replace={summary.seed: "abcdef",
                 utils.SmartStr(blob_fd.size): "42"})


class ApiGetGrrBinaryHandlerRegressionTest(
    config_plugin_test.ApiGrrBinaryTestMixin,
    api_regression_test_lib.ApiRegressionTest):

  api_method = "GetGrrBinary"
  handler = config_plugin.ApiGetGrrBinaryHandler

  def Run(self):
    summary = self.SetUpBinaries()

    self.Check(
        "GetGrrBinary",
        args=config_plugin.ApiGetGrrBinaryArgs(type="PYTHON_HACK", path="test"))
    self.Check(
        "GetGrrBinary",
        args=config_plugin.ApiGetGrrBinaryArgs(
            type="EXECUTABLE", path="windows/test.exe"))

    blob_fd = self.GetBinaryBlob(summary)
    blob_contents = summary.cipher.Decrypt(blob_fd.Read(blob_fd.size))

    self.Check(
        "GetGrrBinary",
        args=config_plugin.ApiGetGrrBinaryArgs(
            type="COMPONENT",
            path="grr-awesome-component_1.2.3.4/%s/Linux_debian_64bit" %
            summary.seed),
        # Serialized component contains a random seed, so we need to
        # replace it with a predefined string.
        replace={
            summary.seed: "abcdef",
            utils.SmartUnicode(blob_contents): "<binary data>"
        })


def main(argv):
  api_regression_test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
