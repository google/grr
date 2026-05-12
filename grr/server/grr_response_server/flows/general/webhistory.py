#!/usr/bin/env python
"""Flow to recover history files."""

# DISABLED for now until it gets converted to artifacts.

import collections
from collections.abc import Iterator
import os

from google.protobuf import any_pb2
from grr_response_core.lib.rdfvalues import mig_paths
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server.databases import db
from grr_response_server.flows.general import collectors


def _HasErrors(progress: flows_pb2.CollectBrowserHistoryProgress) -> bool:
  return any(
      i.status == flows_pb2.BrowserProgress.Status.ERROR
      for i in progress.browsers
  )


def _ErrorsSummary(
    progress: flows_pb2.CollectBrowserHistoryProgress,
) -> list[str]:
  summary = []
  for item in progress.browsers:
    if item.status == flows_pb2.BrowserProgress.Status.ERROR:
      summary.append(
          f"{flows_pb2.Browser.Name(item.browser)}: {item.description}"
      )
  return summary


class CollectBrowserHistory(
    flow_base.FlowBase[
        flows_pb2.CollectBrowserHistoryArgs,
        flows_pb2.DefaultFlowStore,
        flows_pb2.CollectBrowserHistoryProgress,
    ]
):
  """Convenience Flow to collect browser history artifacts."""

  friendly_name = "Browser History"
  category = "/Browser/"
  behaviours = flow_base.BEHAVIOUR_BASIC

  proto_args_type = flows_pb2.CollectBrowserHistoryArgs
  proto_progress_type = flows_pb2.CollectBrowserHistoryProgress
  proto_result_types = (flows_pb2.CollectBrowserHistoryResult,)

  BROWSER_TO_ARTIFACTS_MAP = {
      flows_pb2.Browser.CHROMIUM_BASED_BROWSERS: [
          "ChromiumBasedBrowsersHistoryDatabaseFile"
      ],
      flows_pb2.Browser.FIREFOX: ["FirefoxHistory"],
      flows_pb2.Browser.INTERNET_EXPLORER: ["InternetExplorerHistory"],
      flows_pb2.Browser.OPERA: ["OperaHistoryFile"],
      flows_pb2.Browser.SAFARI: ["SafariHistory"],
  }

  def GetProgressProto(self) -> flows_pb2.CollectBrowserHistoryProgress:
    return self.progress

  # TODO - Remove/update this method to use protos.
  # This unblocks the deletion of the `CollectBrowserHistoryResult` class above.
  def GetFilesArchiveMappings(
      self, flow_results: Iterator[flows_pb2.FlowResult]
  ) -> Iterator[flow_base.ClientPathArchiveMapping]:
    path_counters = collections.Counter()
    for r in flow_results:
      p = flows_pb2.CollectBrowserHistoryResult()
      p.ParseFromString(r.payload.value)

      client_path = db.ClientPath.FromPathSpec(
          self.client_id, mig_paths.ToRDFPathSpec(p.stat_entry.pathspec)
      )
      target_path = os.path.join(
          flows_pb2.Browser.Name(p.browser).lower(),
          _ArchiveFilename(client_path.components),
      )
      if path_counters[target_path] > 0:
        fname, ext = os.path.splitext(target_path)
        target_path = f"{fname}_{path_counters[target_path]}{ext}"

      path_counters[target_path] += 1

      yield flow_base.ClientPathArchiveMapping(client_path, target_path)

  def Start(self):
    super().Start()

    if not self.proto_args.browsers:
      raise flow_base.FlowError("Need to collect at least one type of history.")

    if flows_pb2.Browser.UNDEFINED in self.proto_args.browsers:
      raise flow_base.FlowError("UNDEFINED is not a valid browser type to use.")

    if len(self.proto_args.browsers) != len(set(self.proto_args.browsers)):
      raise flow_base.FlowError(
          "Duplicate browser entries are not allowed in the arguments."
      )

    self.progress = flows_pb2.CollectBrowserHistoryProgress()

    # Start a sub-flow for every browser to split results and progress in
    # the user interface more cleanly.
    for browser in self.proto_args.browsers:
      flow_id = self.CallFlowProto(
          collectors.ArtifactCollectorFlow.__name__,
          flow_args=flows_pb2.ArtifactCollectorFlowArgs(
              artifact_list=self.BROWSER_TO_ARTIFACTS_MAP[browser],
          ),
          request_data={"browser": browser},
          next_state=self.ProcessArtifactResponses.__name__,
      )
      self.progress.browsers.append(
          flows_pb2.BrowserProgress(
              browser=browser,
              status=flows_pb2.BrowserProgress.Status.IN_PROGRESS,
              flow_id=flow_id,
          )
      )

  @flow_base.UseProto2AnyResponses
  def ProcessArtifactResponses(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:

    browser: flows_pb2.Browser = responses.request_data["browser"]
    for bp in self.progress.browsers:
      if bp.browser != browser:
        continue

      if not responses.success:
        bp.status = flows_pb2.BrowserProgress.Status.ERROR
        if responses.status:
          bp.description = responses.status.error_message
      else:
        bp.status = flows_pb2.BrowserProgress.Status.SUCCESS
        bp.num_collected_files = len(responses)

      break

    for response_any in responses:
      stat_entry = jobs_pb2.StatEntry()
      stat_entry.ParseFromString(response_any.value)
      self.SendReplyProto(
          flows_pb2.CollectBrowserHistoryResult(
              browser=browser,
              stat_entry=stat_entry,
          ),
          tag=flows_pb2.Browser.Name(browser),
      )

  def End(self) -> None:
    p = self.GetProgressProto()
    if _HasErrors(p):
      raise flow_base.FlowError(
          f"Errors were encountered during collection: {_ErrorsSummary(p)}"
      )

  @classmethod
  def GetDefaultArgs(cls, username=None):
    """Returns default args for this flow."""
    del username  # Unused.
    return flows_pb2.CollectBrowserHistoryArgs(
        browsers=[
            flows_pb2.Browser.CHROMIUM_BASED_BROWSERS,
            flows_pb2.Browser.FIREFOX,
            flows_pb2.Browser.INTERNET_EXPLORER,
            flows_pb2.Browser.OPERA,
            flows_pb2.Browser.SAFARI,
        ]
    )


def _StripPunctuation(word: str) -> str:
  return "".join(c for c in word if c.isalnum())


def _ArchiveFilename(components: str) -> str:
  """Builds a pathname string based on components names."""
  new_components = []
  for i, component in enumerate(components):
    if i != len(components) - 1:
      new_components.append(_StripPunctuation(component))
    else:  # last component includes file extension so no stripping
      new_components.append(component)

  return "_".join(new_components)
