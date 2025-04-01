#!/usr/bin/env python
"""UI server report handling classes."""

from collections.abc import Callable
import re
from typing import Optional

from grr_response_core.lib import rdfvalue
from grr_response_proto import jobs_pb2
from grr_response_proto import objects_pb2
from grr_response_proto.api import stats_pb2
from grr_response_server import data_store
from grr_response_server.gui.api_plugins.report_plugins import report_plugin_base


def _LoadAuditEvents(
    handlers: dict[str, "jobs_pb2.AuditEvent.Action"],
    get_report_args: stats_pb2.ApiGetReportArgs,
    transformers: Optional[
        Callable[[objects_pb2.APIAuditEntry, jobs_pb2.AuditEvent], None]
    ] = None,
) -> list[jobs_pb2.AuditEvent]:
  """Returns AuditEvents for given handlers, actions, and timerange."""
  if transformers is None:
    transformers = {}

  entries = data_store.REL_DB.ReadAPIAuditEntries(
      min_timestamp=rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
          get_report_args.start_time
      ),
      max_timestamp=rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
          get_report_args.start_time + get_report_args.duration
      ),
      router_method_names=list(handlers.keys()),
  )
  rows = [_EntryToEvent(entry, handlers, transformers) for entry in entries]
  rows.sort(key=lambda row: row.timestamp, reverse=True)
  return rows


def _EntryToEvent(
    entry: objects_pb2.APIAuditEntry,
    handlers: dict[str, "jobs_pb2.AuditEvent.Action"],
    transformers: Optional[
        Callable[[objects_pb2.APIAuditEntry, jobs_pb2.AuditEvent], None]
    ],
) -> jobs_pb2.AuditEvent:
  """Converts an APIAuditEntry to a legacy AuditEvent."""
  event = jobs_pb2.AuditEvent(
      timestamp=entry.timestamp,
      user=entry.username,
      action=handlers[entry.router_method_name],
  )

  for fn in transformers:
    fn(entry, event)

  return event


def _ExtractClientIdFromPath(
    entry: objects_pb2.APIAuditEntry,
    event: jobs_pb2.AuditEvent,
) -> None:
  """Extracts a Client ID from an APIAuditEntry's HTTP request path."""
  match = re.match(r".*(C\.[0-9a-fA-F]{16}).*", entry.http_request_path)
  if match:
    event.client = match.group(1)


# TODO: Remove AFF4 URNs from the API data format.
def _ExtractCronJobIdFromPath(
    entry: objects_pb2.APIAuditEntry,
    event: jobs_pb2.AuditEvent,
) -> None:
  """Extracts a CronJob ID from an APIAuditEntry's HTTP request path."""
  match = re.match(r".*cron-job/([^/]+).*", entry.http_request_path)
  if match:
    event.urn = "aff4:/cron/{}".format(match.group(1))


def _ExtractHuntIdFromPath(
    entry: objects_pb2.APIAuditEntry,
    event: jobs_pb2.AuditEvent,
) -> None:
  """Extracts a Hunt ID from an APIAuditEntry's HTTP request path."""
  match = re.match(r".*hunt/([^/]+).*", entry.http_request_path)
  if match:
    event.urn = "aff4:/hunts/{}".format(match.group(1))


class ClientApprovalsReportPlugin(report_plugin_base.ReportPluginBase):
  """Given timerange's client approvals."""

  TYPE = stats_pb2.ApiReportDescriptor.ReportType.SERVER
  TITLE = "Client Approvals"
  SUMMARY = "Client approval requests and grants for the given timerange."
  REQUIRES_TIME_RANGE = True

  USED_FIELDS = ["action", "client", "timestamp", "user"]
  # TODO: Rework API data format, to remove need for legacy
  # AuditEvent.Action.
  HANDLERS = {
      "GrantClientApproval": jobs_pb2.AuditEvent.Action.CLIENT_APPROVAL_GRANT,
      "CreateClientApproval": (
          jobs_pb2.AuditEvent.Action.CLIENT_APPROVAL_REQUEST
      ),
  }

  def GetReportData(
      self, get_report_args: stats_pb2.ApiGetReportArgs
  ) -> stats_pb2.ApiReportData:
    """Filter the cron job approvals in the given timerange."""
    ret = stats_pb2.ApiReportData()
    ret.representation_type = (
        stats_pb2.ApiReportData.RepresentationType.AUDIT_CHART
    )
    ret.audit_chart.CopyFrom(
        stats_pb2.ApiAuditChartReportData(used_fields=self.USED_FIELDS),
    )
    ret.audit_chart.rows.extend(
        _LoadAuditEvents(
            self.HANDLERS,
            get_report_args,
            transformers=[_ExtractClientIdFromPath],
        )
    )
    return ret


class CronApprovalsReportPlugin(report_plugin_base.ReportPluginBase):
  """Given timerange's cron job approvals."""

  TYPE = stats_pb2.ApiReportDescriptor.ReportType.SERVER
  TITLE = "Cron Job Approvals"
  SUMMARY = "Cron job approval requests and grants for the given timerange."
  REQUIRES_TIME_RANGE = True

  USED_FIELDS = ["action", "timestamp", "user", "urn"]
  HANDLERS = {
      "GrantCronJobApproval": jobs_pb2.AuditEvent.Action.CRON_APPROVAL_GRANT,
      "CreateCronJobApproval": jobs_pb2.AuditEvent.Action.CRON_APPROVAL_REQUEST,
  }

  def GetReportData(self, get_report_args):
    """Filter the cron job approvals in the given timerange."""
    ret = stats_pb2.ApiReportData()
    ret.representation_type = (
        stats_pb2.ApiReportData.RepresentationType.AUDIT_CHART
    )
    ret.audit_chart.CopyFrom(
        stats_pb2.ApiAuditChartReportData(used_fields=self.USED_FIELDS),
    )
    ret.audit_chart.rows.extend(
        _LoadAuditEvents(
            self.HANDLERS,
            get_report_args,
            transformers=[_ExtractCronJobIdFromPath],
        )
    )
    return ret


# TODO: Migrate from AuditEvent to Hunts database table as source.
class HuntActionsReportPlugin(report_plugin_base.ReportPluginBase):
  """Hunt actions in the given timerange."""

  TYPE = stats_pb2.ApiReportDescriptor.ReportType.SERVER
  TITLE = "Hunts"
  SUMMARY = "Hunt management actions for the given timerange."
  REQUIRES_TIME_RANGE = True

  USED_FIELDS = ["action", "timestamp", "user"]
  TYPES = [
      jobs_pb2.AuditEvent.Action.HUNT_CREATED,
      jobs_pb2.AuditEvent.Action.HUNT_MODIFIED,
      jobs_pb2.AuditEvent.Action.HUNT_PAUSED,
      jobs_pb2.AuditEvent.Action.HUNT_STARTED,
      jobs_pb2.AuditEvent.Action.HUNT_STOPPED,
  ]
  HANDLERS = {
      "CreateHunt": jobs_pb2.AuditEvent.Action.HUNT_CREATED,
      "ModifyHunt": jobs_pb2.AuditEvent.Action.HUNT_MODIFIED,
  }

  def GetReportData(self, get_report_args):
    """Filter the hunt actions in the given timerange."""
    ret = stats_pb2.ApiReportData()
    ret.representation_type = (
        stats_pb2.ApiReportData.RepresentationType.AUDIT_CHART
    )
    ret.audit_chart.CopyFrom(
        stats_pb2.ApiAuditChartReportData(used_fields=self.USED_FIELDS)
    )
    ret.audit_chart.rows.extend(
        _LoadAuditEvents(self.HANDLERS, get_report_args)
    )
    return ret


class HuntApprovalsReportPlugin(report_plugin_base.ReportPluginBase):
  """Given timerange's hunt approvals."""

  TYPE = stats_pb2.ApiReportDescriptor.ReportType.SERVER
  TITLE = "Hunt Approvals"
  SUMMARY = "Hunt approval requests and grants for the given timerange."
  REQUIRES_TIME_RANGE = True

  USED_FIELDS = ["action", "timestamp", "user", "urn"]
  HANDLERS = {
      "GrantHuntApproval": jobs_pb2.AuditEvent.Action.HUNT_APPROVAL_GRANT,
      "CreateHuntApproval": jobs_pb2.AuditEvent.Action.HUNT_APPROVAL_REQUEST,
  }

  def GetReportData(
      self,
      get_report_args: stats_pb2.ApiGetReportArgs,
  ) -> stats_pb2.ApiReportData:
    """Filter the hunt approvals in the given timerange."""
    ret = stats_pb2.ApiReportData()
    ret.representation_type = (
        stats_pb2.ApiReportData.RepresentationType.AUDIT_CHART
    )
    ret.audit_chart.CopyFrom(
        stats_pb2.ApiAuditChartReportData(used_fields=self.USED_FIELDS)
    )
    ret.audit_chart.rows.extend(
        _LoadAuditEvents(
            self.HANDLERS,
            get_report_args,
            transformers=[_ExtractHuntIdFromPath],
        )
    )
    return ret
