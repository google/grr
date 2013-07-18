#!/usr/bin/env python
"""Flows for collecting all files in a user specific Java Cache directory."""



from grr.lib import aff4
from grr.lib import constants
from grr.lib import flow
from grr.lib import flow_utils
from grr.lib import rdfvalue
from grr.lib import type_info
from grr.lib import utils


class JavaCacheCollector(flow.GRRFlow):
  """Collect all files in a user specific Java Cache directory.

  Returns to parent flow:
    A URN to a GRRCollection object.
  """

  category = "/Collectors/"
  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.PathTypeEnum(
          description="The requested path type.",
          name="pathtype",
          default=rdfvalue.PathSpec.PathType.OS),
      type_info.String(
          name="username",
          description="A string containing the username."),
      type_info.String(
          name="domain",
          default="",
          description="Optional string containing the domain of the username."),
      type_info.String(
          name="cache_dir",
          default="",
          description=("Path to the Java cache. If provided, this overrides "
                       "the guessing of the cache directory using "
                       "username/domain.")),
      type_info.String(
          name="output",
          default="analysis/java-cache/{u}-{t}",
          description=("If set, a URN to an AFF4Collection to add each result "
                       "to. This will create the collection if it does not "
                       "exist.")),
      )

  MAJOR_VERSION_WINDOWS_VISTA = 6

  @flow.StateHandler(next_state="End")
  def Start(self):
    self.findspecs = list(self.GetFindSpecs())
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

    pathspec = rdfvalue.PathSpec(path=cache_directory,
                                 pathtype=self.pathtype)

    yield rdfvalue.RDFFindSpec(
        pathspec=pathspec,
        path_regex=".*",
        max_depth=2)
