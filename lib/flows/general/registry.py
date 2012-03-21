#!/usr/bin/env python

# Copyright 2012 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Gather information from the registry on windows."""

import re
import stat

from grr.lib import aff4
from grr.lib import flow
from grr.proto import jobs_pb2
from grr.proto import sysinfo_pb2


class MRUFolder(aff4.RDFProtoArray):
  """Store the MRU files."""
  _proto = sysinfo_pb2.MRUFile


class MRUCollection(aff4.AFF4Object):
  """Show the result of MRU analysis."""

  class SchemaCls(aff4.AFF4Object.SchemaCls):
    LAST_USED_FOLDER = aff4.Attribute(
        "aff4:mru", MRUFolder, "The Most Recently Used files.",
        default="")


class FindMRU(flow.GRRFlow):
  """Find interesting MRUs on the system."""

  category = "/Registry/"

  @flow.StateHandler(next_state="StoreMRUs")
  def Start(self):
    """Issue the find request for each user."""
    fd = aff4.FACTORY.Open(self.client_id, mode="r", token=self.token)
    for user in fd.Get(fd.Schema.USER):
      mru_path = ("HKEY_USERS/%s/Software/Microsoft/Windows"
                  "/CurrentVersion/Explorer/ComDlg32"
                  "/OpenSavePidlMRU" % user.sid)

      pathspec = jobs_pb2.Path(pathtype=jobs_pb2.Path.REGISTRY,
                               path=mru_path)

      findspec = jobs_pb2.Find(pathspec=pathspec,
                               max_depth=2)
      findspec.iterator.number = 1000

      self.CallFlow("FindFiles", findspec=findspec, output=None,
                    next_state="StoreMRUs",
                    request_data=dict(username=user.username))

  @flow.StateHandler(in_protobuf=jobs_pb2.StatResponse)
  def StoreMRUs(self, responses):
    """Actually store the data."""

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
            aff4.RDFURN(self.client_id)
            .Add("analysis/MRU/Explorer")
            .Add(extension)
            .Add(username),
            "MRUCollection", token=self.token,
            mode="rw")

        # TODO(user): Implement the actual parsing of the MRU.
        mrus = fd.Get(fd.Schema.LAST_USED_FOLDER)
        mrus.Append(sysinfo_pb2.MRUFile(filename="Foo"))

        fd.Set(fd.Schema.LAST_USED_FOLDER, mrus)
        fd.Close()
