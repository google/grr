#!/usr/bin/env python
"""UI report plugins server-side interface."""

from grr_response_server.gui.api_plugins.report_plugins import report_plugin_base
from grr_response_server.gui.api_plugins.report_plugins import server_report_plugins


def GetAvailableReportPlugins() -> list[report_plugin_base.ReportPluginBase]:
  """Lists the registered report plugins."""
  return sorted(
      REGISTRY.GetRegisteredPlugins().values(), key=lambda cls: cls.__name__
  )


def GetReportByName(name) -> report_plugin_base.ReportPluginBase:
  """Maps report plugin names to report objects.

  Args:
    name: The name of a plugin class. Also the name field of ApiGetReportArgs
      and ApiReportDescriptor.

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
    self.plugins: dict[str, report_plugin_base.ReportPluginBase] = {}

  def GetRegisteredPlugins(
      self,
  ) -> dict[str, report_plugin_base.ReportPluginBase]:
    return self.plugins

  def RegisterPlugin(
      self, report_plugin_cls: report_plugin_base.ReportPluginBase
  ) -> None:
    """Registers a report plugin for use in the GRR UI."""

    name = report_plugin_cls.__name__
    if name in self.plugins:
      raise RuntimeError(
          "Can't register two report plugins with the same "
          "name. In particular, can't register the same "
          "report plugin twice: %r" % name
      )

    self.plugins[name] = report_plugin_cls


REGISTRY = _Registry()


# Server report plugins.

REGISTRY.RegisterPlugin(server_report_plugins.ClientApprovalsReportPlugin)
REGISTRY.RegisterPlugin(server_report_plugins.CronApprovalsReportPlugin)
REGISTRY.RegisterPlugin(server_report_plugins.HuntActionsReportPlugin)
REGISTRY.RegisterPlugin(server_report_plugins.HuntApprovalsReportPlugin)
