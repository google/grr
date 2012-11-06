#!/usr/bin/env python
# Copyright 2011 Google Inc.
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


"""Flows for collecting all files in a user specific Java Cache directory."""



from grr.lib import aff4
from grr.lib import constants
from grr.lib import flow
from grr.lib import flow_utils
from grr.lib import type_info
from grr.lib import utils
from grr.proto import jobs_pb2


class JavaCacheCollector(flow.GRRFlow):
  """Collect all files in a user specific Java Cache directory.

  Returns to parent flow:
    A URN to a GRRCollection object.
  """

  category = "/Collectors/"
  flow_typeinfo = {"pathtype": type_info.ProtoEnum(jobs_pb2.Path, "PathType"),
                   "username": type_info.String()}
  MAJOR_VERSION_WINDOWS_VISTA = 6

  def __init__(self,
               pathtype=jobs_pb2.Path.OS,
               username="", domain=None, cachedir="",
               output="analysis/java-cache/{u}-{t}", **kwargs):
    """Constructor.

    Args:
      pathtype: Identifies requested path type. Enum from Path protobuf.
      username: A string containing the username.
      domain: Optional string containing the domain of the username.
      cachedir: Path to the Java cache. If provided, this overrides the guessing
                of the cache directory using username/domain.
      output: If set, a URN to an AFF4Collection to add each result to.
          This will create the collection if it does not exist.

    Raises:
      RuntimeError: If parameters are invalid.
    """
    super(JavaCacheCollector, self).__init__(**kwargs)
    self.pathtype = pathtype
    self.cache_dir = cachedir
    if not username:
      raise RuntimeError("Username not set")

    self.username = username
    self.domain = domain
    self.output = output
    self.findspecs = list(self.GetFindSpecs())

  @flow.StateHandler(next_state="End")
  def Start(self):
    self.CallFlow("FileCollector", output=self.output,
                  findspecs=self.findspecs, next_state="End")

  @flow.StateHandler()
  def End(self, responses):
    """Notify the user if we were successful."""
    response = responses.First()
    if response:
      fd = aff4.FACTORY.Open(response.aff4path, mode="r", token=self.token)
      collection_list = fd.Get(fd.Schema.COLLECTION)
      if collection_list:
        self.Notify("ViewObject", response.aff4path,
                    "Retrieved %s Java cache files." % len(collection_list))
        return

    raise flow.FlowError("No Java cache files were downloaded.")

  def GetJavaCachePath(self):
    """Determines the platform specific Java Cache sub path.

    Returns:
      A Unicode string containing the client specific Java cache sub path.

    Raises:
      OSError: If the client operating system is not supported.
    """
    client = aff4.FACTORY.Open(aff4.ROOT_URN.Add(self.client_id),
                               token=self.token)
    system = client.Get(client.Schema.SYSTEM)
    version = client.Get(client.Schema.OS_VERSION)

    user_pb = flow_utils.GetUserInfo(client, self.username)

    if user_pb is None:
      raise flow.FlowError("User %s not found." % self.username)

    if not user_pb.homedir:
      raise flow.FlowError("No valid homedir for {0}".format(self.username))

    if system == "Darwin":
      return utils.JoinPath([user_pb.homedir,
                             u"/Library/Caches/Java/cache"])

    elif system == "Linux":
      return utils.JoinPath([user_pb.homedir,
                             u"/.java/deployment/cache"])

    elif system == "Windows":
      appdata_dir = user_pb.special_folders.local_app_data
      if appdata_dir:
        appdata_dir = appdata_dir.replace("Roaming", "LocalLow")
        return appdata_dir + u"\\Sun\\Java\\Deployment\\cache"

      if version:
        major_version = version.versions[0]
        if major_version < constants.MAJOR_VERSION_WINDOWS_VISTA:
          return (user_pb.homedir +
                  u"\\Application Data\\Sun\\Java\\Deployment\\cache")

      return (user_pb.homedir +
              u"\\AppData\\LocalLow\\Sun\\Java\\Deployment\\cache")

    else:
      raise OSError("Unsupported operating system: {0}".format(self.system))

  def GetFindSpecs(self):
    """Determine the Find specifications.

    Yields:
      A path specification to search

    Raises:
      OSError: If the client operating system is not supported.
    """
    cache_directory = self.cache_dir or self.GetJavaCachePath()

    path_spec = utils.Pathspec(jobs_pb2.Path(path=cache_directory,
                                             pathtype=self.pathtype))

    yield jobs_pb2.Find(
        pathspec=path_spec.ToProto(),
        path_regex=".*",
        max_depth=2)
