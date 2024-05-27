#!/usr/bin/env python
"""Flow to recover history files."""

# DISABLED for now until it gets converted to artifacts.

import collections
import os
from typing import Iterator, cast

from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server.databases import db
from grr_response_server.flows.general import collectors
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects


class CollectBrowserHistoryArgs(rdf_structs.RDFProtoStruct):
  """Arguments for CollectBrowserHistory."""
  protobuf = flows_pb2.CollectBrowserHistoryArgs


# Working around the RDFStructs limitation: the only way to use a top-level
# enum is to reference it through the class that has a field of that enum's
# type.
Browser = CollectBrowserHistoryArgs.Browser


class CollectBrowserHistoryResult(rdf_structs.RDFProtoStruct):
  """Result item to be returned by CollectBrowserHistory."""
  protobuf = flows_pb2.CollectBrowserHistoryResult
  rdf_deps = [
      rdf_client_fs.StatEntry,
  ]


class BrowserProgress(rdf_structs.RDFProtoStruct):
  """Single browser progress for CollectBrowserHistoryProgress."""
  protobuf = flows_pb2.BrowserProgress


class CollectBrowserHistoryProgress(rdf_structs.RDFProtoStruct):
  """Progress for CollectBrowserHistory."""
  protobuf = flows_pb2.CollectBrowserHistoryProgress
  rdf_deps = [BrowserProgress]

  @property
  def has_errors(self) -> bool:
    return any(i.status == BrowserProgress.Status.ERROR for i in self.browsers)

  @property
  def errors_summary(self) -> str:
    summary = []
    for item in self.browsers:
      if item.status == BrowserProgress.Status.ERROR:
        summary.append(f"{item.browser.name}: {item.description}")

    return "\n".join(summary)


class CollectBrowserHistory(flow_base.FlowBase):
  """Convenience Flow to collect browser history artifacts."""

  friendly_name = "Browser History"
  category = "/Browser/"
  args_type = CollectBrowserHistoryArgs
  progress_type = CollectBrowserHistoryProgress
  result_types = (CollectBrowserHistoryResult,)
  behaviours = flow_base.BEHAVIOUR_BASIC

  BROWSER_TO_ARTIFACTS_MAP = {
      Browser.CHROME: ["ChromiumBasedBrowsersHistory"],
      Browser.FIREFOX: ["FirefoxHistory"],
      Browser.INTERNET_EXPLORER: ["InternetExplorerHistory"],
      Browser.OPERA: ["OperaHistoryFile"],
      Browser.SAFARI: ["SafariHistory"],
  }

  def GetProgress(self) -> CollectBrowserHistoryProgress:
    if hasattr(self.state, "progress"):
      return self.state.progress
    return CollectBrowserHistoryProgress()

  def GetFilesArchiveMappings(
      self, flow_results: Iterator[rdf_flow_objects.FlowResult]
  ) -> Iterator[flow_base.ClientPathArchiveMapping]:
    path_counters = collections.Counter()
    for r in flow_results:
      p = cast(CollectBrowserHistoryResult, r.payload)
      client_path = db.ClientPath.FromPathSpec(self.client_id,
                                               p.stat_entry.pathspec)
      target_path = os.path.join(p.browser.name.lower(),
                                 _ArchiveFilename(client_path.components))
      if path_counters[target_path] > 0:
        fname, ext = os.path.splitext(target_path)
        target_path = f"{fname}_{path_counters[target_path]}{ext}"

      path_counters[target_path] += 1

      yield flow_base.ClientPathArchiveMapping(client_path, target_path)

  def Start(self):
    super().Start()

    if not self.args.browsers:
      raise flow_base.FlowError("Need to collect at least one type of history.")

    if Browser.UNDEFINED in self.args.browsers:
      raise flow_base.FlowError("UNDEFINED is not a valid browser type to use.")

    if len(self.args.browsers) != len(set(self.args.browsers)):
      raise flow_base.FlowError(
          "Duplicate browser entries are not allowed in the arguments.")

    self.state.progress = CollectBrowserHistoryProgress()

    # Start a sub-flow for every browser to split results and progress in
    # the user interface more cleanly.
    for browser in self.args.browsers:
      flow_id = self.CallFlow(
          collectors.ArtifactCollectorFlow.__name__,
          artifact_list=self.BROWSER_TO_ARTIFACTS_MAP[browser],
          apply_parsers=False,
          request_data={"browser": browser},
          next_state=self.ProcessArtifactResponses.__name__)
      self.state.progress.browsers.append(
          BrowserProgress(
              browser=browser,
              status=BrowserProgress.Status.IN_PROGRESS,
              flow_id=flow_id))

  def ProcessArtifactResponses(
      self,
      responses: flow_responses.Responses[rdf_client_fs.StatEntry]) -> None:

    browser = Browser.FromInt(responses.request_data["browser"])
    for bp in self.state.progress.browsers:
      if bp.browser != browser:
        continue

      if not responses.success:
        bp.status = BrowserProgress.Status.ERROR
        bp.description = responses.status.error_message
      else:
        bp.status = BrowserProgress.Status.SUCCESS
        bp.num_collected_files = len(responses)

      break

    for response in responses:
      self.SendReply(
          CollectBrowserHistoryResult(browser=browser, stat_entry=response),
          tag=browser.name)

  def End(self, responses):
    del responses  # Unused.

    p = self.GetProgress()
    if p.has_errors:
      raise flow_base.FlowError(
          f"Errors were encountered during collection: {p.errors_summary}")

  @classmethod
  def GetDefaultArgs(cls, username=None):
    return CollectBrowserHistoryArgs(browsers=[
        Browser.CHROME,
        Browser.FIREFOX,
        Browser.INTERNET_EXPLORER,
        Browser.OPERA,
        Browser.SAFARI,
    ])


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
