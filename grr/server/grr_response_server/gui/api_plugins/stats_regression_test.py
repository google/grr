#!/usr/bin/env python
"""This module contains regression tests for stats API handlers."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl import app

from grr_response_core.lib import rdfvalue
from grr_response_server.gui import api_regression_test_lib
from grr_response_server.gui.api_plugins import stats as stats_plugin
from grr_response_server.gui.api_plugins.report_plugins import report_plugins_test_mocks


from grr.test_lib import test_lib


class ApiListReportsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest):

  api_method = "ListReports"
  handler = stats_plugin.ApiListReportsHandler

  def Run(self):
    with report_plugins_test_mocks.MockedReportPlugins():
      self.Check("ListReports")


class ApiGetReportRegressionTest(api_regression_test_lib.ApiRegressionTest):

  api_method = "GetReport"
  handler = stats_plugin.ApiGetReportHandler

  def Run(self):
    with report_plugins_test_mocks.MockedReportPlugins():
      self.Check(
          "GetReport",
          args=stats_plugin.ApiGetReportArgs(
              name="BarReportPlugin",
              start_time=rdfvalue.RDFDatetime.FromHumanReadable("2012/12/14")
              .AsMicrosecondsSinceEpoch(),
              duration="4d"))


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
