#!/usr/bin/env python
"""This module contains report plugin mocks used for testing."""

from unittest import mock

from grr_response_core.lib import rdfvalue
from grr_response_proto import jobs_pb2
from grr_response_proto.api import stats_pb2
from grr_response_server.gui.api_plugins.report_plugins import report_plugin_base
from grr_response_server.gui.api_plugins.report_plugins import report_plugins


class FooReportPlugin(report_plugin_base.ReportPluginBase):
  """Stub report plugin."""

  TYPE = stats_pb2.ApiReportDescriptor.ReportType.CLIENT
  TITLE = "Foo"
  SUMMARY = "Reports all foos."


class BarReportPlugin(report_plugin_base.ReportPluginBase):
  """Stub report plugin."""

  TYPE = stats_pb2.ApiReportDescriptor.ReportType.SERVER
  TITLE = "Bar Activity"
  SUMMARY = "Reports bars' activity in the given time range."
  REQUIRES_TIME_RANGE = True

  def GetReportData(
      self, get_report_args: stats_pb2.ApiGetReportArgs
  ) -> stats_pb2.ApiReportData:
    return stats_pb2.ApiReportData(
        representation_type=stats_pb2.ApiReportData.RepresentationType.AUDIT_CHART,
        audit_chart=stats_pb2.ApiAuditChartReportData(
            used_fields=["action", "client", "timestamp", "user"],
            rows=[
                jobs_pb2.AuditEvent(
                    user="user",
                    action=jobs_pb2.AuditEvent.Action.USER_ADD,
                    timestamp=int(
                        rdfvalue.RDFDatetime.FromHumanReadable("2018/12/14")
                    ),
                    id=42,
                )
            ],
        ),
    )


class MockedReportPlugins(object):
  """A context manager that swaps available reports with the mocked reports."""

  def __init__(self):
    self.stubber = mock.patch.object(
        report_plugins.REGISTRY,
        "plugins",
        {
            "FooReportPlugin": FooReportPlugin,
            "BarReportPlugin": BarReportPlugin,
        },
    )

  def __enter__(self):
    self.Start()

  def __exit__(self, *_):
    self.Stop()

  def Start(self):
    self.stubber.start()

  def Stop(self):
    self.stubber.stop()
