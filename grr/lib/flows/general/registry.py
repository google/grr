#!/usr/bin/env python
"""Gather information from the registry on windows."""

import re
import stat

from grr.lib import aff4
from grr.lib import artifact
from grr.lib import artifact_utils
from grr.lib import flow
from grr.lib.aff4_objects import aff4_grr
from grr.lib.aff4_objects import standard
# For ArtifactCollectorFlow pylint: disable=unused-import
from grr.lib.flows.general import collectors
from grr.lib.flows.general import file_finder
# For FindFiles
from grr.lib.flows.general import find
# pylint: enable=unused-import
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import structs as rdf_structs
from grr.path_detection import windows as path_detection_windows
from grr.proto import flows_pb2


class RegistryFinderCondition(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.RegistryFinderCondition


class RegistryFinderArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.RegistryFinderArgs


class RegistryFinder(flow.GRRFlow):
  """This flow looks for registry items matching given criteria."""

  friendly_name = "Registry Finder"
  category = "/Registry/"
  args_type = RegistryFinderArgs
  behaviours = flow.GRRFlow.behaviours + "BASIC"

  def ConditionsToFileFinderConditions(self, conditions):
    ff_condition_type_cls = file_finder.FileFinderCondition.Type
    result = []
    for c in conditions:
      if c.condition_type == RegistryFinderCondition.Type.MODIFICATION_TIME:
        result.append(file_finder.FileFinderCondition(
            condition_type=ff_condition_type_cls.MODIFICATION_TIME,
            modification_time=c.modification_time))
      elif c.condition_type == RegistryFinderCondition.Type.VALUE_LITERAL_MATCH:
        result.append(file_finder.FileFinderCondition(
            condition_type=ff_condition_type_cls.CONTENTS_LITERAL_MATCH,
            contents_literal_match=c.value_literal_match))
      elif c.condition_type == RegistryFinderCondition.Type.VALUE_REGEX_MATCH:
        result.append(file_finder.FileFinderCondition(
            condition_type=ff_condition_type_cls.CONTENTS_REGEX_MATCH,
            contents_regex_match=c.value_regex_match))
      elif c.condition_type == RegistryFinderCondition.Type.SIZE:
        result.append(file_finder.FileFinderCondition(
            condition_type=ff_condition_type_cls.SIZE,
            size=c.size))
      else:
        raise ValueError("Unknown condition type: %s", c.condition_type)

    return result

  @classmethod
  def GetDefaultArgs(cls, token=None):
    _ = token
    return cls.args_type(keys_paths=["HKEY_USERS/%%users.sid%%/Software/"
                                     "Microsoft/Windows/CurrentVersion/Run/*"])

  @flow.StateHandler(next_state="Done")
  def Start(self):
    self.CallFlow(
        "FileFinder",
        paths=self.args.keys_paths,
        pathtype=rdf_paths.PathSpec.PathType.REGISTRY,
        conditions=self.ConditionsToFileFinderConditions(self.args.conditions),
        action=file_finder.FileFinderAction(
            action_type=file_finder.FileFinderAction.Action.STAT),
        next_state="Done")

  @flow.StateHandler()
  def Done(self, responses):
    if not responses.success:
      raise flow.FlowError("Registry search failed %s" % responses.status)

    for response in responses:
      self.SendReply(response)


# TODO(user): replace this flow with chained artifacts once the capability
# exists.
class CollectRunKeyBinaries(flow.GRRFlow):
  """Collect the binaries used by Run and RunOnce keys on the system.

  We use the RunKeys artifact to get RunKey command strings for all users and
  System. This flow guesses file paths from the strings, expands any
  windows system environment variables, and attempts to retrieve the files.
  """
  category = "/Registry/"
  behaviours = flow.GRRFlow.behaviours + "BASIC"

  @flow.StateHandler(next_state="ParseRunKeys")
  def Start(self):
    """Get runkeys via the ArtifactCollectorFlow."""
    self.CallFlow("ArtifactCollectorFlow",
                  artifact_list=["WindowsRunKeys"],
                  use_tsk=True,
                  store_results_in_aff4=False,
                  next_state="ParseRunKeys")

  @flow.StateHandler(next_state="Done")
  def ParseRunKeys(self, responses):
    """Get filenames from the RunKeys and download the files."""
    filenames = []
    client = aff4.FACTORY.Open(self.client_id, mode="r", token=self.token)
    kb = artifact.GetArtifactKnowledgeBase(client)

    for response in responses:
      runkey = response.registry_data.string

      environ_vars = artifact_utils.GetWindowsEnvironmentVariablesMap(kb)
      path_guesses = path_detection_windows.DetectExecutablePaths([runkey],
                                                                  environ_vars)

      if not path_guesses:
        self.Log("Couldn't guess path for %s", runkey)

      for path in path_guesses:
        filenames.append(rdf_paths.PathSpec(
            path=path, pathtype=rdf_paths.PathSpec.PathType.TSK))

    if filenames:
      self.CallFlow("MultiGetFile", pathspecs=filenames, next_state="Done")

  @flow.StateHandler()
  def Done(self, responses):
    for response in responses:
      self.SendReply(response)


class GetMRU(flow.GRRFlow):
  """Collect a list of the Most Recently Used files for all users."""

  category = "/Registry/"
  behaviours = flow.GRRFlow.behaviours + "BASIC"

  @flow.StateHandler(next_state="StoreMRUs")
  def Start(self):
    """Call the find flow to get the MRU data for each user."""
    fd = aff4.FACTORY.Open(self.client_id, mode="r", token=self.token)
    kb = fd.Get(fd.Schema.KNOWLEDGE_BASE)
    for user in kb.users:
      mru_path = ("HKEY_USERS/%s/Software/Microsoft/Windows"
                  "/CurrentVersion/Explorer/ComDlg32"
                  "/OpenSavePidlMRU" % user.sid)

      findspec = rdf_client.FindSpec(max_depth=2, path_regex=".")
      findspec.iterator.number = 1000
      findspec.pathspec.path = mru_path
      findspec.pathspec.pathtype = rdf_paths.PathSpec.PathType.REGISTRY

      self.CallFlow("FindFiles",
                    findspec=findspec,
                    output=None,
                    next_state="StoreMRUs",
                    request_data=dict(username=user.username))

  @flow.StateHandler()
  def StoreMRUs(self, responses):
    """Store the MRU data for each user in a special structure."""
    for response in responses:
      urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(response.pathspec,
                                                       self.client_id)

      if stat.S_ISDIR(response.st_mode):
        obj_type = standard.VFSDirectory
      else:
        obj_type = aff4_grr.VFSFile

      fd = aff4.FACTORY.Create(urn, obj_type, mode="w", token=self.token)
      fd.Set(fd.Schema.STAT(response))
      fd.Close(sync=False)

      username = responses.request_data["username"]

      m = re.search("/([^/]+)/\\d+$", unicode(urn))
      if m:
        extension = m.group(1)
        fd = aff4.FACTORY.Create(
            rdf_client.ClientURN(self.client_id).Add("analysis/MRU/Explorer")
            .Add(extension).Add(username),
            aff4_grr.MRUCollection,
            token=self.token,
            mode="rw")

        # TODO(user): Implement the actual parsing of the MRU.
        mrus = fd.Get(fd.Schema.LAST_USED_FOLDER)
        mrus.Append(filename="Foo")

        fd.Set(mrus)
        fd.Close()
