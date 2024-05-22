#!/usr/bin/env python
"""UI server report handling classes."""

import re

from grr_response_core.lib.rdfvalues import events as rdf_events
from grr_response_server import data_store
from grr_response_server.gui.api_plugins.report_plugins import rdf_report_plugins
from grr_response_server.gui.api_plugins.report_plugins import report_plugin_base

RepresentationType = rdf_report_plugins.ApiReportData.RepresentationType


def _LoadAuditEvents(handlers, get_report_args, transformers=None):
  """Returns AuditEvents for given handlers, actions, and timerange."""
  if transformers is None:
    transformers = {}

  entries = data_store.REL_DB.ReadAPIAuditEntries(
      min_timestamp=get_report_args.start_time,
      max_timestamp=get_report_args.start_time + get_report_args.duration,
      router_method_names=list(handlers.keys()),
  )
  rows = [_EntryToEvent(entry, handlers, transformers) for entry in entries]
  rows.sort(key=lambda row: row.timestamp, reverse=True)
  return rows


def _EntryToEvent(entry, handlers, transformers):
  """Converts an APIAuditEntry to a legacy AuditEvent."""
  event = rdf_events.AuditEvent(
      timestamp=entry.timestamp,
      user=entry.username,
      action=handlers[entry.router_method_name],
  )

  for fn in transformers:
    fn(entry, event)

  return event


def _ExtractClientIdFromPath(entry, event):
  """Extracts a Client ID from an APIAuditEntry's HTTP request path."""
  match = re.match(r".*(C\.[0-9a-fA-F]{16}).*", entry.http_request_path)
  if match:
    event.client = match.group(1)


# TODO: Remove AFF4 URNs from the API data format.
def _ExtractCronJobIdFromPath(entry, event):
  """Extracts a CronJob ID from an APIAuditEntry's HTTP request path."""
  match = re.match(r".*cron-job/([^/]+).*", entry.http_request_path)
  if match:
    event.urn = "aff4:/cron/{}".format(match.group(1))


def _ExtractHuntIdFromPath(entry, event):
  """Extracts a Hunt ID from an APIAuditEntry's HTTP request path."""
  match = re.match(r".*hunt/([^/]+).*", entry.http_request_path)
  if match:
    event.urn = "aff4:/hunts/{}".format(match.group(1))


class ClientApprovalsReportPlugin(report_plugin_base.ReportPluginBase):
  """Given timerange's client approvals."""

  TYPE = rdf_report_plugins.ApiReportDescriptor.ReportType.SERVER
  TITLE = "Client Approvals"
  SUMMARY = "Client approval requests and grants for the given timerange."
  REQUIRES_TIME_RANGE = True

  USED_FIELDS = ["action", "client", "timestamp", "user"]
  # TODO: Rework API data format, to remove need for legacy
  # AuditEvent.Action.
  HANDLERS = {
      "GrantClientApproval": rdf_events.AuditEvent.Action.CLIENT_APPROVAL_GRANT,
      "CreateClientApproval": (
          rdf_events.AuditEvent.Action.CLIENT_APPROVAL_REQUEST
      ),
  }

  def GetReportData(self, get_report_args=None):
    """Filter the cron job approvals in the given timerange."""
    ret = rdf_report_plugins.ApiReportData(
        representation_type=RepresentationType.AUDIT_CHART,
        audit_chart=rdf_report_plugins.ApiAuditChartReportData(
            used_fields=self.USED_FIELDS
        ),
    )

    ret.audit_chart.rows = _LoadAuditEvents(
        self.HANDLERS, get_report_args, transformers=[_ExtractClientIdFromPath]
    )
    return ret


class CronApprovalsReportPlugin(report_plugin_base.ReportPluginBase):
  """Given timerange's cron job approvals."""

  TYPE = rdf_report_plugins.ApiReportDescriptor.ReportType.SERVER
  TITLE = "Cron Job Approvals"
  SUMMARY = "Cron job approval requests and grants for the given timerange."
  REQUIRES_TIME_RANGE = True

  USED_FIELDS = ["action", "timestamp", "user", "urn"]
  HANDLERS = {
      "GrantCronJobApproval": rdf_events.AuditEvent.Action.CRON_APPROVAL_GRANT,
      "CreateCronJobApproval": (
          rdf_events.AuditEvent.Action.CRON_APPROVAL_REQUEST
      ),
  }

  def GetReportData(self, get_report_args):
    """Filter the cron job approvals in the given timerange."""
    ret = rdf_report_plugins.ApiReportData(
        representation_type=RepresentationType.AUDIT_CHART,
        audit_chart=rdf_report_plugins.ApiAuditChartReportData(
            used_fields=self.USED_FIELDS
        ),
    )

    ret.audit_chart.rows = _LoadAuditEvents(
        self.HANDLERS, get_report_args, transformers=[_ExtractCronJobIdFromPath]
    )
    return ret


# TODO: Migrate from AuditEvent to Hunts database table as source.
class HuntActionsReportPlugin(report_plugin_base.ReportPluginBase):
  """Hunt actions in the given timerange."""

  TYPE = rdf_report_plugins.ApiReportDescriptor.ReportType.SERVER
  TITLE = "Hunts"
  SUMMARY = "Hunt management actions for the given timerange."
  REQUIRES_TIME_RANGE = True

  USED_FIELDS = ["action", "timestamp", "user"]
  TYPES = [
      rdf_events.AuditEvent.Action.HUNT_CREATED,
      rdf_events.AuditEvent.Action.HUNT_MODIFIED,
      rdf_events.AuditEvent.Action.HUNT_PAUSED,
      rdf_events.AuditEvent.Action.HUNT_STARTED,
      rdf_events.AuditEvent.Action.HUNT_STOPPED,
  ]
  HANDLERS = {
      "CreateHunt": rdf_events.AuditEvent.Action.HUNT_CREATED,
      "ModifyHunt": rdf_events.AuditEvent.Action.HUNT_MODIFIED,
  }

  def GetReportData(self, get_report_args):
    """Filter the hunt actions in the given timerange."""
    ret = rdf_report_plugins.ApiReportData(
        representation_type=RepresentationType.AUDIT_CHART,
        audit_chart=rdf_report_plugins.ApiAuditChartReportData(
            used_fields=self.USED_FIELDS
        ),
    )

    ret.audit_chart.rows = _LoadAuditEvents(self.HANDLERS, get_report_args)
    return ret


class HuntApprovalsReportPlugin(report_plugin_base.ReportPluginBase):
  """Given timerange's hunt approvals."""

  TYPE = rdf_report_plugins.ApiReportDescriptor.ReportType.SERVER
  TITLE = "Hunt Approvals"
  SUMMARY = "Hunt approval requests and grants for the given timerange."
  REQUIRES_TIME_RANGE = True

  USED_FIELDS = ["action", "timestamp", "user", "urn"]
  HANDLERS = {
      "GrantHuntApproval": rdf_events.AuditEvent.Action.HUNT_APPROVAL_GRANT,
      "CreateHuntApproval": rdf_events.AuditEvent.Action.HUNT_APPROVAL_REQUEST,
  }

  def GetReportData(self, get_report_args):
    """Filter the hunt approvals in the given timerange."""
    ret = rdf_report_plugins.ApiReportData(
        representation_type=RepresentationType.AUDIT_CHART,
        audit_chart=rdf_report_plugins.ApiAuditChartReportData(
            used_fields=self.USED_FIELDS
        ),
    )

    ret.audit_chart.rows = _LoadAuditEvents(
        self.HANDLERS, get_report_args, transformers=[_ExtractHuntIdFromPath]
    )
    return ret
