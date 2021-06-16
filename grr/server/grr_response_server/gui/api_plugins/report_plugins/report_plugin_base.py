#!/usr/bin/env python
"""UI report plugins base class.

Each report plugin is a subclass of ReportPluginBase.
"""

from grr_response_server.gui.api_plugins.report_plugins import rdf_report_plugins


class ReportPluginBase(object):
  """Abstract base class of report plugins."""

  # TYPE represents the category the report belongs to. Possible values are the
  # entries of ApiReportDescriptor.ReportType enum. If type is CLIENT, a client
  # label selector will be displayed in the ui. Selected label can be accessed
  # in the report handler.
  TYPE = None
  # TITLE is what the ui displays at the top of the report and in the report
  # types listing. This can be any string.
  TITLE = None
  # SUMMARY is shown in the ui with the report. It should be a string.
  SUMMARY = None
  # REQUIRES_TIME_RANGE triggers a time range selector in the ui. Selected
  # range can be accessed later in the report handler. True/False.
  REQUIRES_TIME_RANGE = False

  @classmethod
  def GetReportDescriptor(cls):
    """Returns plugins' metadata in ApiReportDescriptor."""
    if cls.TYPE is None:
      raise ValueError("%s.TYPE is uninitialized." % cls)

    if cls.TITLE is None:
      raise ValueError("%s.TITLE is uninitialized." % cls)

    if cls.SUMMARY is None:
      raise ValueError("%s.SUMMARY is uninitialized." % cls)

    return rdf_report_plugins.ApiReportDescriptor(
        type=cls.TYPE,
        name=cls.__name__,
        title=cls.TITLE,
        summary=cls.SUMMARY,
        requires_time_range=cls.REQUIRES_TIME_RANGE)

  def GetReportData(self, get_report_args):
    """Generates the data to be displayed in the report.

    Args:
      get_report_args: ApiGetReportArgs passed from
                       ApiListReportsHandler.
    Raises:
      NotImplementedError: If not overridden.

    Returns:
      ApiReportData
    """
    raise NotImplementedError()
