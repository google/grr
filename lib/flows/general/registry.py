#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.
"""Gather information from the registry on windows."""

import re
import stat

from grr.lib import aff4
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import utils


class CollectRunKeys(flow.GRRFlow):
  """Collect Run and RunOnce keys on the system for all users and System."""

  category = "/Registry/"

  @flow.StateHandler(next_state="StoreRunKeys")
  def Start(self):
    """Issue the find request for each user and the system."""
    fd = aff4.FACTORY.Open(self.client_id, mode="r", token=self.token)
    self.numrunkeys = 0
    users = fd.Get(fd.Schema.USER, [])
    # Iterate through all the users and trigger flows for Run and RunOnce keys.
    for user in users:
      for key in ["Run", "RunOnce"]:
        run_path = ("HKEY_USERS/%s/Software/Microsoft/Windows/CurrentVersion"
                    "/%s" % (user.sid, key))

        findspec_run = rdfvalue.RDFFindSpec(max_depth=2)
        findspec_run.iterator.number = 1000
        findspec_run.pathspec.path = run_path
        findspec_run.pathspec.pathtype = rdfvalue.PathSpec.PathType.REGISTRY

        self.CallFlow("FindFiles", findspec=findspec_run,
                      next_state="StoreRunKeys",
                      request_data=dict(username=user.username, keytype=key))

    # Set off the LocalMachine Run and RunOnce Flows.
    for key in ["Run", "RunOnce"]:
      run_path = ("HKEY_LOCAL_MACHINE/Software/Microsoft/Windows/CurrentVersion"
                  "/%s" % key)

      findspec_run = rdfvalue.RDFFindSpec(max_depth=2)
      findspec_run.iterator.number = 1000
      findspec_run.pathspec.path = run_path
      findspec_run.pathspec.pathtype = rdfvalue.PathSpec.PathType.REGISTRY

      self.CallFlow("FindFiles", findspec=findspec_run,
                    next_state="StoreRunKeys",
                    request_data=dict(username="System", keytype=key))

  @flow.StateHandler()
  def StoreRunKeys(self, responses):
    """Store the Run Keys in RunKey Collections."""

    # Get Username and keytype from the responses object.
    username = responses.request_data["username"]
    keytype = responses.request_data["keytype"]

    # Log that the requested key does not exist.
    if not responses.success:
      self.Log("%s for %s does not exist" % (keytype, username))

    # Creates a RunKeyCollection for everyone, even if the key does not exist.
    runkey_collection = aff4.FACTORY.Create(
        rdfvalue.RDFURN(self.client_id).Add("analysis/RunKeys")
        .Add(username).Add(keytype),
        "RDFValueCollection", token=self.token, mode="rw")

    for response in responses:
      runkey_collection.Add(rdfvalue.RunKey(
          keyname=utils.SmartUnicode(response.pathspec.path),
          filepath=utils.SmartUnicode(response.registry_data.string),
          lastwritten=int(response.st_mtime)))

    runkey_collection.Close()
    self.numrunkeys = len(runkey_collection)

  @flow.StateHandler()
  def End(self):
    self.Log("Successfully wrote %d RunKeys.", self.numrunkeys)
    urn = self.client_id.Add("analysis/RunKeys")
    self.Notify("ViewObject", urn, "Collected the User and System Run Keys")


class FindMRU(flow.GRRFlow):
  """Collect a list of the Most Recently Used files for all users."""

  category = "/Registry/"

  @flow.StateHandler(next_state="StoreMRUs")
  def Start(self):
    """Call the find flow to get the MRU data for each user."""
    fd = aff4.FACTORY.Open(self.client_id, mode="r", token=self.token)
    for user in fd.Get(fd.Schema.USER):
      mru_path = ("HKEY_USERS/%s/Software/Microsoft/Windows"
                  "/CurrentVersion/Explorer/ComDlg32"
                  "/OpenSavePidlMRU" % user.sid)

      findspec = rdfvalue.RDFFindSpec(max_depth=2)
      findspec.iterator.number = 1000
      findspec.pathspec.path = mru_path
      findspec.pathspec.pathtype = rdfvalue.PathSpec.PathType.REGISTRY

      self.CallFlow("FindFiles", findspec=findspec, output=None,
                    next_state="StoreMRUs",
                    request_data=dict(username=user.username))

  @flow.StateHandler()
  def StoreMRUs(self, responses):
    """Store the MRU data for each user in a special structure."""
    for response in responses:
      urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(
          response.pathspec, self.client_id)

      if stat.S_ISDIR(response.st_mode):
        obj_type = "VFSDirectory"
      else:
        obj_type = "VFSFile"

      fd = aff4.FACTORY.Create(urn, obj_type, mode="w", token=self.token)
      fd.Set(fd.Schema.STAT(response))
      fd.Close(sync=False)

      username = responses.request_data["username"]

      m = re.search("/([^/]+)/\\d+$", unicode(urn))
      if m:
        extension = m.group(1)
        fd = aff4.FACTORY.Create(
            rdfvalue.RDFURN(self.client_id)
            .Add("analysis/MRU/Explorer")
            .Add(extension)
            .Add(username),
            "MRUCollection", token=self.token,
            mode="rw")

        # TODO(user): Implement the actual parsing of the MRU.
        mrus = fd.Get(fd.Schema.LAST_USED_FOLDER)
        mrus.Append(filename="Foo")

        fd.Set(mrus)
        fd.Close()
