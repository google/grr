#!/usr/bin/env python
"""UI server report handling classes."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import itertools
import math

from builtins import range  # pylint: disable=redefined-builtin

from grr_response_server import aff4
from grr_response_server.aff4_objects import stats as aff4_stats

from grr_response_server.gui.api_plugins.report_plugins import rdf_report_plugins
from grr_response_server.gui.api_plugins.report_plugins import report_plugin_base

TYPE = rdf_report_plugins.ApiReportDescriptor.ReportType.FILE_STORE


class FileSizeDistributionReportPlugin(report_plugin_base.ReportPluginBase):
  """Reports file frequency by client count."""

  TYPE = TYPE
  TITLE = "File Size Distribution"
  SUMMARY = ("Number of files in filestore by size. X: log10 (filesize), Y: "
             "Number of files.")

  def _Log(self, x):
    # Note 0 and 1 are collapsed into a single category
    return math.log10(x) if x > 0 else x

  def _BytesToHumanReadable(self, x):
    units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"]

    for u in units:
      # Our linter complains when a loop variable is used after the loop (though
      # it's valid to do so in Python). Assigning the loop variable to another
      # variable makes the linter happy.
      unit = u

      if x < 1024:
        break

      if not isinstance(x, float) and x % 1024 != 0:
        x = float(x)

      if unit != units[-1]:
        if isinstance(x, float):
          x /= 1024.0
        else:
          x //= 1024

    if not isinstance(x, float):
      return "%d %s" % (x, unit)
    return "%.1f %s" % (x, unit)

  def GetReportData(self, get_report_args, token):
    """Report file frequency by client count."""
    x_ticks = []
    for e in range(15):
      x = 32**e

      x_ticks.append(
          rdf_report_plugins.ApiReportTickSpecifier(
              x=self._Log(x), label=self._BytesToHumanReadable(x)))

    ret = rdf_report_plugins.ApiReportData(
        representation_type=rdf_report_plugins.ApiReportData.RepresentationType.
        STACK_CHART,
        stack_chart=rdf_report_plugins.ApiStackChartReportData(
            x_ticks=x_ticks, bar_width=.2))

    data = ()
    try:
      fd = aff4.FACTORY.Open("aff4:/stats/FileStoreStats", token=token)
      graph = fd.Get(
          aff4_stats.FilestoreStats.SchemaCls.FILESTORE_FILESIZE_HISTOGRAM)

      if graph:
        data = graph.data
    except (IOError, TypeError):
      pass

    xs = [point.x_value for point in data]
    ys = [point.y_value for point in data]

    labels = [
        "%s - %s" % (self._BytesToHumanReadable(int(x0)),
                     self._BytesToHumanReadable(int(x1)))
        for x0, x1 in itertools.izip(xs[:-1], xs[1:])
    ]
    last_x = data[-1].x_value
    labels.append(
        # \u221E is the infinity sign.
        u"%s - \u221E" % self._BytesToHumanReadable(int(last_x)))

    ret.stack_chart.data = (rdf_report_plugins.ApiReportDataSeries2D(
        label=label,
        points=[rdf_report_plugins.ApiReportDataPoint2D(x=self._Log(x), y=y)])
                            for label, x, y in itertools.izip(labels, xs, ys))

    return ret
