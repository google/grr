#!/usr/bin/env python
"""UI reports handling classes.

Each report is a *direct* subclass of ReportPluginBase. The list of its
direct subclasses is treated as a list of available reports.
"""

from grr.lib import registry
from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import api_pb2


class ApiReportDescriptor(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiReportDescriptor


class ApiReport(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiReport


class ApiReportData(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiReportData


class ApiStackChartReportData(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiStackChartReportData


class ApiReportDataSeries2D(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiReportDataSeries2D


class ApiReportDataPoint2D(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiReportDataPoint2D


def GetAvailableReportPlugins():
  """Lists direct subclasses of ReportPluginBase."""
  return sorted(
      ReportPluginBase.classes.itervalues(), key=lambda cls: cls.__name__)


def GetReportByName(name):
  """Maps report plugin names to report objects.

  Args:
    name: The name of a plugin class. Also the name field of
          ApiGetReportArgs and ApiReportDescriptor.

  Returns:
    Report plugin object of class corresponding to the given name.
  """
  report_class = ReportPluginBase.classes[name]
  report_object = report_class()

  return report_object


class ReportPluginBase(object):
  """Abstract base class of report plugins."""

  __metaclass__ = registry.MetaclassRegistry
  __abstract = True  # pylint: disable=g-bad-name

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
      raise ValueError("%s.TYPE is unintialized." % cls)

    if cls.TITLE is None:
      raise ValueError("%s.TITLE is unintialized." % cls)

    if cls.SUMMARY is None:
      raise ValueError("%s.SUMMARY is unintialized." % cls)

    return ApiReportDescriptor(
        type=cls.TYPE,
        name=cls.__name__,
        title=cls.TITLE,
        summary=cls.SUMMARY,
        requires_time_range=cls.REQUIRES_TIME_RANGE)

  def GetReportData(self, get_report_args, token):
    """Generates the data to be displayed in the report.

    Args:
      get_report_args: ApiGetReportArgs passed from
                       ApiListReportsHandler.
      token: The authorization token, also passed from ApiListReportsHandler.

    Raises:
      NotImplementedError: If not overriden.

    Returns:
      ApiReportData
    """
    raise NotImplementedError()
