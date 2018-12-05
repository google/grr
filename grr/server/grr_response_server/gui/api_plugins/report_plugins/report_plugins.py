#!/usr/bin/env python
"""UI report plugins server-side interface."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from future.utils import itervalues

from grr_response_server.gui.api_plugins.report_plugins import client_report_plugins
from grr_response_server.gui.api_plugins.report_plugins import filestore_report_plugins
from grr_response_server.gui.api_plugins.report_plugins import server_report_plugins


def GetAvailableReportPlugins():
  """Lists the registered report plugins."""
  return sorted(
      itervalues(REGISTRY.GetRegisteredPlugins()), key=lambda cls: cls.__name__)


def GetReportByName(name):
  """Maps report plugin names to report objects.

  Args:
    name: The name of a plugin class. Also the name field of
          ApiGetReportArgs and ApiReportDescriptor.

  Returns:
    Report plugin object of class corresponding to the given name.
  """
  report_class = REGISTRY.GetRegisteredPlugins()[name]
  report_object = report_class()

  return report_object


class _Registry(object):
  """UI report plugins registry.

  Each report plugin needs to be registered here in order to be displayed in the
  UI.
  """

  def __init__(self):
    self.plugins = {}

  def GetRegisteredPlugins(self):
    return self.plugins

  def RegisterPlugin(self, report_plugin_cls):
    """Registers a report plugin for use in the GRR UI."""

    name = report_plugin_cls.__name__
    if name in self.plugins:
      raise RuntimeError("Can't register two report plugins with the same "
                         "name. In particular, can't register the same "
                         "report plugin twice: %r" % name)

    self.plugins[name] = report_plugin_cls


REGISTRY = _Registry()

# Client report plugins.

REGISTRY.RegisterPlugin(client_report_plugins.GRRVersion1ReportPlugin)
REGISTRY.RegisterPlugin(client_report_plugins.GRRVersion7ReportPlugin)
REGISTRY.RegisterPlugin(client_report_plugins.GRRVersion30ReportPlugin)
REGISTRY.RegisterPlugin(client_report_plugins.LastActiveReportPlugin)
REGISTRY.RegisterPlugin(client_report_plugins.OSBreakdown1ReportPlugin)
REGISTRY.RegisterPlugin(client_report_plugins.OSBreakdown7ReportPlugin)
REGISTRY.RegisterPlugin(client_report_plugins.OSBreakdown14ReportPlugin)
REGISTRY.RegisterPlugin(client_report_plugins.OSBreakdown30ReportPlugin)
REGISTRY.RegisterPlugin(client_report_plugins.OSReleaseBreakdown1ReportPlugin)
REGISTRY.RegisterPlugin(client_report_plugins.OSReleaseBreakdown7ReportPlugin)
REGISTRY.RegisterPlugin(client_report_plugins.OSReleaseBreakdown14ReportPlugin)
REGISTRY.RegisterPlugin(client_report_plugins.OSReleaseBreakdown30ReportPlugin)

# FileStore report plugins.

REGISTRY.RegisterPlugin(
    filestore_report_plugins.FileSizeDistributionReportPlugin)

# Server report plugins.

REGISTRY.RegisterPlugin(server_report_plugins.ClientApprovalsReportPlugin)
REGISTRY.RegisterPlugin(server_report_plugins.CronApprovalsReportPlugin)
REGISTRY.RegisterPlugin(server_report_plugins.HuntActionsReportPlugin)
REGISTRY.RegisterPlugin(server_report_plugins.HuntApprovalsReportPlugin)
REGISTRY.RegisterPlugin(server_report_plugins.MostActiveUsersReportPlugin)
REGISTRY.RegisterPlugin(server_report_plugins.SystemFlowsReportPlugin)
REGISTRY.RegisterPlugin(server_report_plugins.UserActivityReportPlugin)
REGISTRY.RegisterPlugin(server_report_plugins.UserFlowsReportPlugin)
