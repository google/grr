#!/usr/bin/env python
# Lint as: python3
"""These are filesystem related flows."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os
import re
import stat

from grr_response_core.lib.rdfvalues import artifacts as rdf_artifacts
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import compatibility
from grr_response_core.lib.util.compat import fnmatch
from grr_response_proto import flows_pb2
from grr_response_server import data_store
from grr_response_server import flow_base
from grr_response_server import notification
from grr_response_server import server_stubs
from grr_response_server.rdfvalues import objects as rdf_objects

# This is all bits that define the type of the file in the stat mode. Equal to
# 0b1111000000000000.
stat_type_mask = (
    stat.S_IFREG | stat.S_IFDIR | stat.S_IFLNK | stat.S_IFBLK
    | stat.S_IFCHR | stat.S_IFIFO | stat.S_IFSOCK)


def _FilterOutPathInfoDuplicates(path_infos):
  """Filters out duplicates from passed PathInfo objects.

  Args:
    path_infos: An iterable with PathInfo objects.

  Returns:
    A list of PathInfo objects with duplicates removed. Duplicates are
    removed following this logic: they're sorted by (ctime, mtime, atime,
    inode number) in the descending order and then the first one is taken
    and the others are dropped.
  """
  pi_dict = {}

  for pi in path_infos:
    path_key = (pi.path_type, pi.GetPathID())
    pi_dict.setdefault(path_key, []).append(pi)

  def _SortKey(pi):
    return (
        pi.stat_entry.st_ctime,
        pi.stat_entry.st_mtime,
        pi.stat_entry.st_atime,
        pi.stat_entry.st_ino,
    )

  for pi_values in pi_dict.values():
    if len(pi_values) > 1:
      pi_values.sort(key=_SortKey, reverse=True)

  return [v[0] for v in pi_dict.values()]


def WriteStatEntries(stat_entries, client_id):
  """Persists information about stat entries.

  Args:
    stat_entries: A list of `StatEntry` instances.
    client_id: An id of a client the stat entries come from.
  """

  for stat_response in stat_entries:
    if stat_response.pathspec.last.stream_name:
      # This is an ads. In that case we always need to create a file or
      # we won't be able to access the data. New clients send the correct mode
      # already but to make sure, we set this to a regular file anyways.
      # Clear all file type bits:
      stat_response.st_mode &= ~stat_type_mask
      stat_response.st_mode |= stat.S_IFREG

  path_infos = [rdf_objects.PathInfo.FromStatEntry(s) for s in stat_entries]
  # NOTE: TSK may return duplicate entries. This is may be either due to
  # a bug in TSK implementation, or due to the fact that TSK is capable
  # of returning deleted files information. Our VFS data model only supports
  # storing multiple versions of the files when we collect the versions
  # ourselves. At the moment we can't store multiple versions of the files
  # "as returned by TSK".
  #
  # Current behaviour is to simply drop excessive version before the
  # WritePathInfo call. This way files returned by TSK will still make it
  # into the flow's results, but not into the VFS data.
  data_store.REL_DB.WritePathInfos(client_id,
                                   _FilterOutPathInfoDuplicates(path_infos))


class ListDirectoryArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.ListDirectoryArgs
  rdf_deps = [
      rdf_paths.PathSpec,
  ]


class ListDirectory(flow_base.FlowBase):
  """List files in a directory."""

  category = "/Filesystem/"
  args_type = ListDirectoryArgs
  behaviours = flow_base.BEHAVIOUR_ADVANCED

  def Start(self):
    """Issue a request to list the directory."""
    self.state.urn = None

    # TODO(hanuszczak): Support for old clients ends on 2021-01-01.
    # This conditional should be removed after that date.
    if not self.client_version or self.client_version >= 3221:
      stub = server_stubs.GetFileStat
      request = rdf_client_action.GetFileStatRequest(
          pathspec=self.args.pathspec, follow_symlink=True)
    else:
      stub = server_stubs.StatFile
      request = rdf_client_action.ListDirRequest(pathspec=self.args.pathspec)

    self.CallClient(stub, request, next_state=compatibility.GetName(self.Stat))

    # We use data to pass the path to the callback:
    self.CallClient(
        server_stubs.ListDirectory,
        pathspec=self.args.pathspec,
        next_state=compatibility.GetName(self.List))

  def Stat(self, responses):
    """Save stat information on the directory."""
    # Did it work?
    if not responses.success:
      raise flow_base.FlowError("Could not stat directory: %s" %
                                responses.status)

    # Keep the stat response for later.
    stat_entry = rdf_client_fs.StatEntry(responses.First())
    self.state.stat = stat_entry

    # The full path of the object is the combination of the client_id and the
    # path.
    self.state.urn = stat_entry.pathspec.AFF4Path(self.client_urn)

  def List(self, responses):
    """Collect the directory listing and store in the datastore."""
    if not responses.success:
      raise flow_base.FlowError(str(responses.status))

    self.Log("Listed %s", self.state.urn)

    path_info = rdf_objects.PathInfo.FromStatEntry(self.state.stat)
    data_store.REL_DB.WritePathInfos(self.client_id, [path_info])

    stat_entries = list(map(rdf_client_fs.StatEntry, responses))
    WriteStatEntries(stat_entries, client_id=self.client_id)

    for stat_entry in stat_entries:
      self.SendReply(stat_entry)  # Send Stats to parent flows.

  def NotifyAboutEnd(self):
    """Sends a notification that this flow is done."""
    if not self.state.urn:
      super(ListDirectory, self).NotifyAboutEnd()
      return

    st = self.state.stat

    ps_path_type = st.pathspec.last.pathtype
    path_type = rdf_objects.PathInfo.PathTypeFromPathspecPathType(ps_path_type)

    full_path = st.pathspec.CollapsePath()
    path_components = full_path.strip("/").split("/")

    file_ref = rdf_objects.VfsFileReference(
        client_id=self.client_id,
        path_type=path_type,
        path_components=path_components)

    notification.Notify(
        self.token.username,
        rdf_objects.UserNotification.Type.TYPE_VFS_LIST_DIRECTORY_COMPLETED,
        "Listed {0}".format(full_path),
        rdf_objects.ObjectReference(
            reference_type=rdf_objects.ObjectReference.Type.VFS_FILE,
            vfs_file=file_ref))


class RecursiveListDirectoryArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.RecursiveListDirectoryArgs
  rdf_deps = [
      rdf_paths.PathSpec,
  ]


class RecursiveListDirectory(flow_base.FlowBase):
  """Recursively list directory on the client."""

  category = "/Filesystem/"

  args_type = RecursiveListDirectoryArgs

  def Start(self):
    """List the initial directory."""
    # The first directory we listed.
    self.state.first_directory = None

    self.state.dir_count = 0
    self.state.file_count = 0

    self.CallClient(
        server_stubs.ListDirectory,
        pathspec=self.args.pathspec,
        next_state=compatibility.GetName(self.ProcessDirectory))

  def ProcessDirectory(self, responses):
    """Recursively list the directory, and add to the timeline."""
    if responses.success:
      response = responses.First()

      if response is None:
        return

      directory_pathspec = response.pathspec.Dirname()

      urn = directory_pathspec.AFF4Path(self.client_urn)

      self.StoreDirectory(responses)

      if self.state.first_directory is None:
        self.state.first_directory = urn

      # If the urn is too deep we quit to prevent recursion errors.
      relative_name = urn.RelativeName(self.state.first_directory) or ""
      if _Depth(relative_name) >= self.args.max_depth - 1:
        self.Log("Exceeded maximum path depth at %s.",
                 urn.RelativeName(self.state.first_directory))
        return

      for stat_response in responses:
        # Queue a list directory for each directory here, but do not follow
        # symlinks.
        is_dir = stat.S_ISDIR(int(stat_response.st_mode))
        if not stat_response.symlink and is_dir:
          self.CallClient(
              server_stubs.ListDirectory,
              pathspec=stat_response.pathspec,
              next_state=compatibility.GetName(self.ProcessDirectory))
          self.state.dir_count += 1
          if self.state.dir_count % 100 == 0:  # Log every 100 directories
            self.Log("Reading %s. (%d nodes, %d directories done)",
                     urn.RelativeName(self.state.first_directory),
                     self.state.file_count, self.state.dir_count)

      self.state.file_count += len(responses)

  def StoreDirectory(self, responses):
    """Stores all stat responses."""
    stat_entries = list(map(rdf_client_fs.StatEntry, responses))
    WriteStatEntries(stat_entries, client_id=self.client_id)

    for stat_entry in stat_entries:
      self.SendReply(stat_entry)  # Send Stats to parent flows.

  def NotifyAboutEnd(self):
    status_text = "Recursive Directory Listing complete %d nodes, %d dirs"

    urn = self.state.first_directory
    if not urn:
      try:
        urn = self.args.pathspec.AFF4Path(self.client_urn)
      except ValueError:
        pass

    if urn:
      components = urn.Split()
      file_ref = None
      if len(components) > 3:
        file_ref = rdf_objects.VfsFileReference(
            client_id=components[0],
            path_type=components[2].upper(),
            path_components=components[3:])

    notification.Notify(
        self.token.username, rdf_objects.UserNotification.Type
        .TYPE_VFS_RECURSIVE_LIST_DIRECTORY_COMPLETED,
        status_text % (self.state.file_count, self.state.dir_count),
        rdf_objects.ObjectReference(
            reference_type=rdf_objects.ObjectReference.Type.VFS_FILE,
            vfs_file=file_ref))

  def End(self, responses):
    del responses
    status_text = "Recursive Directory Listing complete %d nodes, %d dirs"
    self.Log(status_text, self.state.file_count, self.state.dir_count)


class GlobArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.GlobArgs
  rdf_deps = [
      rdf_paths.GlobExpression,
      rdf_paths.PathSpec,
  ]

  def Validate(self):
    """Ensure that the glob paths are valid."""
    self.paths.Validate()


class GlobLogic(object):
  """A MixIn to implement the glob functionality."""

  def GlobForPaths(self,
                   paths,
                   pathtype="OS",
                   root_path=None,
                   process_non_regular_files=False,
                   collect_ext_attrs=False):
    """Starts the Glob.

    This is the main entry point for this flow mixin.

    First we convert the pattern into regex components, and then we
    interpolate each component. Finally, we generate a cartesian product of all
    combinations.

    Args:
      paths: A list of GlobExpression instances.
      pathtype: The pathtype to use for creating pathspecs.
      root_path: A pathspec where to start searching from.
      process_non_regular_files: Work with all kinds of files - not only with
        regular ones.
      collect_ext_attrs: Whether to gather information about file extended
        attributes.
    """
    patterns = []

    if not paths:
      # Nothing to do.
      return

    self.state.pathtype = pathtype
    self.state.root_path = root_path
    self.state.process_non_regular_files = process_non_regular_files
    self.state.collect_ext_attrs = collect_ext_attrs

    # Transform the patterns by substitution of client attributes. When the
    # client has multiple values for an attribute, this generates multiple
    # copies of the pattern, one for each variation. e.g.:
    # /home/%%Usernames%%/* -> [ /home/user1/*, /home/user2/* ]
    for path in paths:
      patterns.extend(
          path.Interpolate(knowledge_base=self.client_knowledge_base))

    # Sort the patterns so that if there are files whose paths conflict with
    # directory paths, the files get handled after the conflicting directories
    # have been added to the component tree.
    patterns.sort(key=len, reverse=True)

    # Expand each glob pattern into a list of components. A component is either
    # a wildcard or a literal component.
    # e.g. /usr/lib/*.exe -> ['/usr/lib', '.*.exe']

    # We build a tree for each component such that duplicated components are
    # merged. We do not need to reissue the same client requests for the same
    # components. For example, the patterns:
    # '/home/%%Usernames%%*' -> {'/home/': {
    #      'syslog.*\\Z(?ms)': {}, 'test.*\\Z(?ms)': {}}}
    # Note: The component tree contains serialized pathspecs in dicts.
    for pattern in patterns:
      # The root node.
      curr_node = self.state.component_tree

      components = self._ConvertGlobIntoPathComponents(pattern)
      for i, curr_component in enumerate(components):
        is_last_component = i == len(components) - 1
        next_node = curr_node.get(curr_component.SerializeToBytes(), {})
        if is_last_component and next_node:
          # There is a conflicting directory already existing in the tree.
          # Replace the directory node with a node representing this file.
          curr_node[curr_component.SerializeToBytes()] = {}
        else:
          curr_node = curr_node.setdefault(curr_component.SerializeToBytes(),
                                           {})

    root_path = next(iter(self.state.component_tree.keys()))
    self.CallStateInline(
        messages=[None],
        next_state=compatibility.GetName(self._ProcessEntry),
        request_data=dict(component_path=[root_path]))

  def GlobReportMatch(self, stat_response):
    """Called when we've found a matching a StatEntry."""
    # By default write the stat_response to the AFF4 VFS.
    WriteStatEntries([stat_response], client_id=self.client_id)

  # A regex indicating if there are shell globs in this path.
  GLOB_MAGIC_CHECK = re.compile("[*?[]")

  # Maximum number of files to inspect in a single directory
  FILE_MAX_PER_DIR = 1000000

  def _ConvertGlobIntoPathComponents(self, pattern):
    r"""Converts a glob pattern into a list of pathspec components.

    Wildcards are also converted to regular expressions. The pathspec components
    do not span directories, and are marked as a regex or a literal component.

    We also support recursion into directories using the ** notation.  For
    example, /home/**2/foo.txt will find all files named foo.txt recursed 2
    directories deep. If the directory depth is omitted, it defaults to 3.

    Example:
     /home/test/* -> ['home', 'test', '.*\\Z(?ms)']

    Args:
      pattern: A glob expression with wildcards.

    Returns:
      A list of PathSpec instances for each component.

    Raises:
      ValueError: If the glob is invalid.
    """

    components = []
    for path_component in pattern.split("/"):
      # A ** in the path component means recurse into directories that match the
      # pattern.
      m = rdf_paths.GlobExpression.RECURSION_REGEX.search(path_component)
      if m:
        path_component = path_component.replace(m.group(0), "*")

        component = rdf_paths.PathSpec(
            path=fnmatch.translate(path_component),
            pathtype=self.state.pathtype,
            path_options=rdf_paths.PathSpec.Options.RECURSIVE)

        # Allow the user to override the recursion depth.
        if m.group(1):
          component.recursion_depth = int(m.group(1))

      elif self.GLOB_MAGIC_CHECK.search(path_component):
        component = rdf_paths.PathSpec(
            path=fnmatch.translate(path_component),
            pathtype=self.state.pathtype,
            path_options=rdf_paths.PathSpec.Options.REGEX)
      else:
        component = rdf_paths.PathSpec(
            path=path_component,
            pathtype=self.state.pathtype,
            path_options=rdf_paths.PathSpec.Options.CASE_INSENSITIVE)

      components.append(component)

    return components

  def Start(self, **_):
    super(GlobLogic, self).Start()
    self.state.component_tree = {}

  def _FindNode(self, component_path):
    """Find the node in the component_tree from component_path.

    Args:
      component_path: A list of components which reference a node in the
        component tree. This allows us to resume processing in the tree.

    Returns:
      A node in the component_tree.
    """
    # Find the node that the component path is referring to.
    node = self.state.component_tree
    for component in component_path:
      node = node[component]

    return node

  def _MatchPath(self, pathspec, response):
    """Check if the responses matches the pathspec (considering options)."""
    to_match = response.pathspec.Basename()
    if pathspec.path_options == rdf_paths.PathSpec.Options.CASE_INSENSITIVE:
      return to_match.lower() == pathspec.path.lower()
    elif pathspec.path_options == rdf_paths.PathSpec.Options.CASE_LITERAL:
      return to_match == pathspec.path
    elif pathspec.path_options == rdf_paths.PathSpec.Options.REGEX:
      return bool(re.match(pathspec.path, to_match, flags=re.IGNORECASE))
    elif pathspec.path_options == rdf_paths.PathSpec.Options.RECURSIVE:
      return True
    raise ValueError("Unknown Pathspec type.")

  def _ProcessEntry(self, responses):
    """Process the responses from the client."""
    if not responses.success:
      return

    # The Find client action does not return a StatEntry but a
    # FindSpec. Normalize to a StatEntry.
    stat_responses = [
        r.hit if isinstance(r, rdf_client_fs.FindSpec) else r for r in responses
    ]

    # If this was a pure path matching call without any regex / recursion, we
    # know exactly which node in the component tree we have to process next and
    # get it from the component_path. If this was a regex match though, we
    # sent the client a combined regex that matches all nodes in order to save
    # round trips and client processing time. In that case we only get the
    # base node and have to check for all subnodes if the response actually
    # matches that subnode before we continue processing.
    component_path = responses.request_data.get("component_path")
    if component_path is not None:

      for response in stat_responses:
        self._ProcessResponse(response, [component_path])

    else:
      # This is a combined match.
      base_path = responses.request_data["base_path"]
      base_node = self._FindNode(base_path)
      for response in stat_responses:
        matching_components = []
        for next_node in base_node:
          pathspec = rdf_paths.PathSpec.FromSerializedBytes(next_node)

          if self._MatchPath(pathspec, response):
            matching_path = base_path + [next_node]
            matching_components.append(matching_path)

        if matching_components:
          self._ProcessResponse(
              response, matching_components, base_wildcard=True)

  def _GetBasePathspec(self, response):
    if response:
      return response.pathspec.Copy()
    else:
      root_path = self.state.root_path
      if root_path:
        return root_path.Copy()
    return None

  def _ProcessResponse(self, response, component_paths, base_wildcard=False):
    for component_path in component_paths:
      regexes_to_get = []
      recursions_to_get = {}

      node = self._FindNode(component_path)

      if not node:
        # Node is empty representing a leaf node - we found a hit - report it.
        self.GlobReportMatch(response)
        return

      # There are further components in the tree - iterate over them.
      for component_str, next_node in node.items():
        component = rdf_paths.PathSpec.FromSerializedBytes(component_str)
        next_component = component_path + [component_str]

        # If we reach this point, we are instructed to go deeper into the
        # directory structure. We only want to actually do this if
        # - the last response was a proper directory,
        # - or it was a file (an image) that was explicitly given meaning
        #   no wildcards or groupings,
        # - or process_non_regular_files was set.
        #
        # This reduces the number of TSK opens on the client that may
        # sometimes lead to instabilities due to bugs in the library.

        if response and (not (stat.S_ISDIR(int(response.st_mode)) or
                              not base_wildcard or
                              self.state.process_non_regular_files)):
          continue

        if component.path_options == component.Options.RECURSIVE:
          recursions_to_get.setdefault(component.recursion_depth,
                                       []).append(component)
        elif component.path_options == component.Options.REGEX:
          regexes_to_get.append(component)

        elif component.path_options == component.Options.CASE_INSENSITIVE:
          # Here we need to create the next pathspec by appending the current
          # component to what we already have. If we don't have anything yet, we
          # fall back to the root path. If there is no root path either, the
          # current component becomes the new base.
          base_pathspec = self._GetBasePathspec(response)
          if base_pathspec:
            pathspec = base_pathspec.Append(component)
          else:
            pathspec = component

          if not next_node:
            # Check for the existence of the last node.
            if (response is None or
                (response and (response.st_mode == 0 or
                               not stat.S_ISREG(int(response.st_mode))))):
              # If next node is empty, this node is a leaf node, we therefore
              # must stat it to check that it is there. There is a special case
              # here where this pathspec points to a file/directory in the root
              # directory. In this case, response will be None but we still need
              # to stat it.

              # TODO(hanuszczak): Support for old clients ends on 2021-01-01.
              # This conditional should be removed after that date.
              if not self.client_version or self.client_version >= 3221:
                stub = server_stubs.GetFileStat
                request = rdf_client_action.GetFileStatRequest(
                    pathspec=pathspec,
                    collect_ext_attrs=self.state.collect_ext_attrs,
                    follow_symlink=True)
              else:
                stub = server_stubs.StatFile
                request = rdf_client_action.ListDirRequest(pathspec=pathspec)

              self.CallClient(
                  stub,
                  request,
                  next_state=compatibility.GetName(self._ProcessEntry),
                  request_data=dict(component_path=next_component))
          else:
            # There is no need to go back to the client for intermediate
            # paths in the prefix tree, just emulate this by recursively
            # calling this state inline.
            self.CallStateInline(
                [rdf_client_fs.StatEntry(pathspec=pathspec)],
                next_state=compatibility.GetName(self._ProcessEntry),
                request_data=dict(component_path=next_component))

      if recursions_to_get or regexes_to_get:
        # Recursions or regexes need a base pathspec to operate on. If we
        # have neither a response or a root path, we send a default pathspec
        # that opens the root with pathtype set to the pathtype expected by the
        # user.
        base_pathspec = self._GetBasePathspec(response)
        if not base_pathspec:
          base_pathspec = rdf_paths.PathSpec(
              path="/", pathtype=self.state.pathtype)

        for depth, recursions in recursions_to_get.items():
          path_regex = "(?i)^" + "$|^".join(set([c.path for c in recursions
                                                ])) + "$"

          findspec = rdf_client_fs.FindSpec(
              pathspec=base_pathspec,
              cross_devs=True,
              max_depth=depth,
              path_regex=path_regex)

          findspec.iterator.number = self.FILE_MAX_PER_DIR
          self.CallClient(
              server_stubs.Find,
              findspec,
              next_state=compatibility.GetName(self._ProcessEntry),
              request_data=dict(base_path=component_path))

        if regexes_to_get:
          path_regex = "(?i)^" + "$|^".join(
              set([c.path for c in regexes_to_get])) + "$"
          findspec = rdf_client_fs.FindSpec(
              pathspec=base_pathspec, max_depth=1, path_regex=path_regex)

          findspec.iterator.number = self.FILE_MAX_PER_DIR
          self.CallClient(
              server_stubs.Find,
              findspec,
              next_state=compatibility.GetName(self._ProcessEntry),
              request_data=dict(base_path=component_path))


class Glob(GlobLogic, flow_base.FlowBase):
  """Glob the filesystem for patterns.

  Returns:
    StatEntry messages, one for each matching file.
  """

  category = "/Filesystem/"
  behaviours = flow_base.BEHAVIOUR_ADVANCED
  args_type = GlobArgs
  result_types = (rdf_client_fs.StatEntry,)

  def Start(self):
    """Starts the Glob.

    First we convert the pattern into regex components, and then we
    interpolate each component. Finally, we generate a cartesian product of all
    combinations.
    """
    super(Glob, self).Start()
    self.GlobForPaths(
        self.args.paths,
        pathtype=self.args.pathtype,
        root_path=self.args.root_path,
        process_non_regular_files=self.args.process_non_regular_files)

  def GlobReportMatch(self, stat_response):
    """Called when we've found a matching StatEntry."""
    super(Glob, self).GlobReportMatch(stat_response)

    self.SendReply(stat_response)


class DiskVolumeInfoArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.DiskVolumeInfoArgs


def PathHasDriveLetter(path):
  """Check path for windows drive letter.

  Use 1:2 to avoid raising on single character paths.

  Args:
    path: path string

  Returns:
    True if this path has a drive letter.
  """
  return path[1:2] == ":"


class DiskVolumeInfo(flow_base.FlowBase):
  """Get disk volume info for a given path.

  On linux and OS X we call StatFS on each path and return the results. For
  windows we collect all the volume information and filter it using the drive
  letters in the supplied path list.
  """
  args_type = DiskVolumeInfoArgs
  category = "/Filesystem/"
  behaviours = flow_base.BEHAVIOUR_ADVANCED

  def Start(self):
    self.state.drive_letters = set()
    self.state.system_root_required = False

    if self.client_os == "Windows":
      # Handle the case where a path is specified without the drive letter by
      # collecting systemroot and making sure we report the disk usage for it.
      for path in self.args.path_list:
        if PathHasDriveLetter(path):
          self.state.drive_letters.add(path[0:2])
        else:
          self.state.system_root_required = True
      if self.state.system_root_required:
        self.CallFlow(
            # TODO(user): dependency loop between collectors.py and
            # filesystem.py.
            # collectors.ArtifactCollectorFlow.__name__,
            "ArtifactCollectorFlow",
            artifact_list=["WindowsEnvironmentVariableSystemRoot"],
            next_state=compatibility.GetName(self.StoreSystemRoot))
        return

    self.CallStateInline(
        next_state=compatibility.GetName(self.CollectVolumeInfo))

  def StoreSystemRoot(self, responses):
    if not responses.success or not responses.First():
      if self.state.drive_letters:
        # We have at least one path that already has a drive letter so we'll log
        # rather than raise.
        self.Log("Error collecting SystemRoot artifact: %s", responses.status)
      else:
        raise flow_base.FlowError("Error collecting SystemRoot artifact: %s" %
                                  responses.status)

    drive = str(responses.First())[0:2]
    if drive:
      self.state.drive_letters.add(drive)
    else:
      self.Log("Bad result for systemdrive: %s", responses.First())

    self.CallStateInline(
        next_state=compatibility.GetName(self.CollectVolumeInfo))

  def CollectVolumeInfo(self, responses):
    del responses
    if self.client_os == "Windows":
      # No dependencies for WMI
      deps = rdf_artifacts.ArtifactCollectorFlowArgs.Dependency.IGNORE_DEPS
      self.CallFlow(
          # TODO(user): dependency loop between collectors.py and
          # filesystem.py.
          # collectors.ArtifactCollectorFlow.__name__,
          "ArtifactCollectorFlow",
          artifact_list=["WMILogicalDisks"],
          next_state=compatibility.GetName(self.ProcessWindowsVolumes),
          dependencies=deps)
    else:
      self.CallClient(
          server_stubs.StatFS,
          rdf_client_action.StatFSRequest(
              path_list=self.args.path_list, pathtype=self.args.pathtype),
          next_state=compatibility.GetName(self.ProcessVolumes))

  def ProcessWindowsVolumes(self, responses):
    if not responses.success:
      self.Log("Error running WMILogicalDisks artifact: %s", responses.status)

    for response in responses:
      if response.windowsvolume.drive_letter in self.state.drive_letters:
        self.SendReply(response)

  def ProcessVolumes(self, responses):
    if not responses.success:
      self.Log("Error running StatFS: %s", responses.status)

    for response in responses:
      self.SendReply(response)


def _Depth(relative_path):
  """Calculates the depth of a given path."""
  if not relative_path:
    return 0
  return len(os.path.normpath(relative_path).split("/"))
