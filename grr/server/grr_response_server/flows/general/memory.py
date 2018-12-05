#!/usr/bin/env python
"""Flows for controlling access to memory.

These flows allow for distributing memory access modules to clients and
performing basic analysis.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import json
import logging


from future.utils import iteritems

from grr_response_core import config
from grr_response_core.lib import registry
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import rekall_types as rdf_rekall_types
from grr_response_core.lib.rdfvalues import standard as rdf_standard
from grr_response_core.lib.rdfvalues import structs as rdf_structs

from grr_response_proto import flows_pb2
from grr_response_proto import rekall_pb2
from grr_response_server import aff4
from grr_response_server import aff4_flows
from grr_response_server import flow
from grr_response_server import flow_base
from grr_response_server import rekall_profile_server
from grr_response_server import server_stubs
from grr_response_server.flows.general import file_finder
from grr_response_server.flows.general import transfer


class MemoryCollectorArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.MemoryCollectorArgs


class MemoryCollector(flow.GRRFlow):
  """Flow for scanning and imaging memory.

  MemoryCollector applies "action" (e.g. Download) to memory if memory contents
  match all given "conditions". Matches are then written to the results
  collection. If there are no "conditions", "action" is applied immediately.
  """
  friendly_name = "Memory Collector"
  category = "/Memory/"
  behaviours = flow.FlowBehaviour("DEBUG")
  args_type = MemoryCollectorArgs

  def Start(self):
    if not config.CONFIG["Rekall.enabled"]:
      raise RuntimeError("Rekall flows are disabled. "
                         "Add 'Rekall.enabled: True' to the config to enable "
                         "them.")

    self.state.output_urn = None

    # Use Rekall to grab memory. We no longer manually check for kcore's
    # existence since Rekall does it for us and runs additionally checks (like
    # the actual usability of kcore).
    client = aff4.FACTORY.Open(self.client_id, token=self.token)
    memory_size = client.Get(client.Schema.MEMORY_SIZE)
    self.state.memory_size = memory_size

    # Should we check if there is enough free space?
    if self.args.check_disk_free_space:
      self.CallClient(
          server_stubs.CheckFreeGRRTempSpace, next_state="CheckFreeSpace")
    else:
      self.RunRekallPlugin()

  def CheckFreeSpace(self, responses):
    if responses.success and responses.First():
      disk_usage = responses.First()
      if disk_usage.free < self.state.memory_size:
        raise flow.FlowError(
            "Free space may be too low for local copy. Free "
            "space for path %s is %s bytes. Mem size is: %s "
            "bytes. Override with check_disk_free_space=False." %
            (disk_usage.path, disk_usage.free, self.state.memory_size))
    else:
      logging.error("Couldn't determine free disk space for temporary files.")

    self.RunRekallPlugin()

  def RunRekallPlugin(self):
    plugin = rdf_rekall_types.PluginRequest(plugin="aff4acquire")
    plugin.args["destination"] = "GRR"
    request = rdf_rekall_types.RekallRequest(plugins=[plugin])

    # Note that this will actually also retrieve the memory image.
    self.CallFlow(
        aff4_flows.AnalyzeClientMemory.__name__,
        request=request,
        max_file_size_download=self.args.max_file_size,
        next_state="CheckAnalyzeClientMemory")

  def CheckAnalyzeClientMemory(self, responses):
    if not responses.success:
      raise flow.FlowError("Unable to image memory: %s." % responses.status)

    for response in responses:
      for download in response.downloaded_files:
        self.state.output_urn = download
        self.SendReply(download)
        self.Log("Memory imaged successfully")
        return

    raise flow.FlowError("Rekall flow did not return any files.")


class AnalyzeClientMemoryArgs(rdf_structs.RDFProtoStruct):
  protobuf = rekall_pb2.AnalyzeClientMemoryArgs
  rdf_deps = [
      rdf_rekall_types.RekallRequest,
  ]


@flow_base.DualDBFlow
class AnalyzeClientMemoryMixin(object):
  """Runs client side analysis using Rekall.

  This flow takes a list of Rekall plugins to run. It then sends the list of
  Rekall commands to the client. The client will run those plugins using the
  client's copy of Rekall.
  """

  category = "/Memory/"
  behaviours = flow.FlowBehaviour("DEBUG")
  args_type = AnalyzeClientMemoryArgs

  def Start(self):
    if not config.CONFIG["Rekall.enabled"]:
      raise RuntimeError("Rekall flows are disabled. "
                         "Add 'Rekall.enabled: True' to the config to enable "
                         "them.")

    self.CallStateInline(next_state="StartAnalysis")

  def StartAnalysis(self, responses):
    del responses
    self.state.rekall_context_messages = {}
    self.state.output_files = []
    self.state.plugin_errors = []

    request = self.args.request.Copy()

    # We always push the inventory to the request. This saves a round trip
    # because the client always needs it (so it can figure out if its cache is
    # still valid).
    request.profiles.append(
        self.GetProfileByName("inventory",
                              server_stubs.REKALL_PROFILE_REPOSITORY_VERSION))

    if self.args.debug_logging:
      request.session[u"logging_level"] = u"DEBUG"

    # We want to disable local profile building on the client machines.
    request.session[u"autodetect_build_local"] = u"none"

    # The client will use rekall in live mode.
    if "live" not in request.session:
      request.session["live"] = "Memory"

    self.state.rekall_request = request

    self.CallClient(
        server_stubs.RekallAction,
        self.state.rekall_request,
        next_state="StoreResults")

  def UpdateProfile(self, responses):
    """The target of the WriteRekallProfile client action."""
    if not responses.success:
      self.Log(responses.status)

  def StoreResults(self, responses):
    """Stores the results."""
    if not responses.success:
      self.state.plugin_errors.append(unicode(responses.status.error_message))
      # Keep processing to read out the debug messages from the json.

    self.Log("Rekall returned %s responses." % len(responses))
    for response in responses:
      if response.missing_profile:
        profile = self.GetProfileByName(response.missing_profile,
                                        response.repository_version)
        if profile:
          self.CallClient(
              server_stubs.WriteRekallProfile,
              profile,
              next_state="UpdateProfile")
        else:
          self.Log(
              "Needed profile %s not found! See "
              "https://github.com/google/grr-doc/blob/master/"
              "troubleshooting.adoc#missing-rekall-profiles",
              response.missing_profile)

      if response.json_messages:
        response.client_urn = self.client_id
        if self.state.rekall_context_messages:
          response.json_context_messages = json.dumps(
              list(iteritems(self.state.rekall_context_messages)),
              separators=(",", ":"))

        json_data = json.loads(response.json_messages)
        for message in json_data:
          if len(message) >= 1:
            if message[0] in ["t", "s"]:
              self.state.rekall_context_messages[message[0]] = message[1]

            if message[0] == "file":
              pathspec = rdf_paths.PathSpec(**message[1])
              self.state.output_files.append(pathspec)

            if message[0] == "L":
              if len(message) > 1:
                log_record = message[1]
                self.Log("%s:%s:%s", log_record["level"], log_record["name"],
                         log_record["msg"])

        self.SendReply(response)

    if self.state.output_files:
      self.Log("Getting %i files.", len(self.state.output_files))
      self.CallFlow(
          transfer.MultiGetFile.__name__,
          pathspecs=self.state.output_files,
          file_size=self.args.max_file_size_download,
          next_state="DeleteFiles")

  def DeleteFiles(self, responses):
    # Check that the MultiGetFile flow worked.
    if not responses.success:
      raise flow.FlowError("Could not get files: %s" % responses.status)

    for output_file in self.state.output_files:
      self.CallClient(
          server_stubs.DeleteGRRTempFiles,
          output_file,
          next_state="LogDeleteFiles")

    # Let calling flows know where files ended up in AFF4 space.
    self.SendReply(
        rdf_rekall_types.RekallResponse(
            downloaded_files=[x.AFF4Path(self.client_urn) for x in responses]))

  def LogDeleteFiles(self, responses):
    # Check that the DeleteFiles flow worked.
    if not responses.success:
      raise flow.FlowError("Could not delete file: %s" % responses.status)

  def End(self, responses):
    del responses
    if self.state.plugin_errors:
      all_errors = u"\n".join([unicode(e) for e in self.state.plugin_errors])
      raise flow.FlowError("Error running plugins: %s" % all_errors)

  def GetProfileByName(self, name, version):
    """Load the requested profile from the repository."""
    server_type = config.CONFIG["Rekall.profile_server"]
    logging.info("Getting missing Rekall profile '%s' from %s", name,
                 server_type)

    profile_server = rekall_profile_server.ProfileServer.classes[server_type]()

    return profile_server.GetProfileByName(name, version=version)


class ListVADBinariesArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.ListVADBinariesArgs
  rdf_deps = [
      rdf_standard.RegularExpression,
  ]


class ListVADBinaries(flow.GRRFlow):
  r"""Get list of all running binaries from Rekall, (optionally) fetch them.

    This flow executes the "vad" Rekall plugin to get the list of all
    currently running binaries (including dynamic libraries). Then if
    fetch_binaries option is set to True, it fetches all the binaries it has
    found.

    There is a caveat regarding using the "vad" plugin to detect currently
    running executable binaries. The "Filename" member of the _FILE_OBJECT
    struct is not reliable:

      * Usually it does not include volume information: i.e.
        \\Windows\\some\\path. Therefore it's impossible to detect the actual
        volume where the executable is located.

      * If the binary is executed from a shared network volume, the Filename
        attribute is not descriptive enough to easily fetch the file.

      * If the binary is executed directly from a network location (without
        mounting the volume) Filename attribute will contain yet another
        form of path.

      * Filename attribute is not actually used by the system (it's probably
        there for debugging purposes). It can be easily overwritten by a rootkit
        without any noticeable consequences for the running system, but breaking
        our functionality as a result.

    Therefore this plugin's functionality is somewhat limited. Basically, it
    won't fetch binaries that are located on non-default volumes.

    Possible workaround (future work):
    * Find a way to map given address space into the filename on the filesystem.
    * Fetch binaries directly from memory by forcing page-ins first (via
      some debug userland-process-dump API?) and then reading the memory.
  """
  category = "/Memory/"
  behaviours = flow.FlowBehaviour("DEBUG")
  args_type = ListVADBinariesArgs

  def Start(self):
    """Request VAD data."""
    if not config.CONFIG["Rekall.enabled"]:
      raise RuntimeError("Rekall flows are disabled. "
                         "Add 'Rekall.enabled: True' to the config to enable "
                         "them.")

    self.CallFlow(
        # TODO(user): dependency loop between collectors.py and memory.py.
        # collectors.ArtifactCollectorFlow.__name__,
        "ArtifactCollectorFlow",
        artifact_list=["FullVADBinaryList"],
        next_state="FetchBinaries")

  def FetchBinaries(self, responses):
    """Parses the Rekall response and initiates FileFinder flows."""
    if not responses.success:
      self.Log("Error fetching VAD data: %s", responses.status)
      return

    self.Log("Found %d binaries", len(responses))

    if self.args.filename_regex:
      binaries = []
      for response in responses:
        if self.args.filename_regex.Match(response.CollapsePath()):
          binaries.append(response)

      self.Log("Applied filename regex. Have %d files after filtering.",
               len(binaries))
    else:
      binaries = responses

    if self.args.fetch_binaries:
      self.CallFlow(
          file_finder.FileFinder.__name__,
          next_state="HandleDownloadedFiles",
          paths=[rdf_paths.GlobExpression(b.CollapsePath()) for b in binaries],
          pathtype=rdf_paths.PathSpec.PathType.OS,
          action=rdf_file_finder.FileFinderAction.Download())
    else:
      for b in binaries:
        self.SendReply(b)

  def HandleDownloadedFiles(self, responses):
    """Handle success/failure of the FileFinder flow."""
    if responses.success:
      for file_finder_result in responses:
        self.SendReply(file_finder_result.stat_entry)
        self.Log("Downloaded %s",
                 file_finder_result.stat_entry.pathspec.CollapsePath())
    else:
      self.Log("Binaries download failed: %s", responses.status)


class MemoryFlowsInit(registry.InitHook):
  """Update visibility for Rekall flows."""

  def RunOnce(self):
    if config.CONFIG["Rekall.enabled"]:
      b = flow.FlowBehaviour("BASIC")
    else:
      b = flow.FlowBehaviour("DEBUG")

    # Mark Rekall-based flows as basic, so that they appear in the UI.
    for cls in [MemoryCollector, AnalyzeClientMemoryMixin, ListVADBinaries]:
      cls.behaviours = b
