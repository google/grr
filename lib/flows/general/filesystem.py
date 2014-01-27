#!/usr/bin/env python
"""These are filesystem related flows."""

import fnmatch
import re
import stat

from grr.lib import aff4
from grr.lib import flow
from grr.lib import rdfvalue
from grr.proto import flows_pb2


def CreateAFF4Object(stat_response, client_id, token, sync=False):
  """This creates a File or a Directory from a stat response."""

  stat_response.aff4path = aff4.AFF4Object.VFSGRRClient.PathspecToURN(
      stat_response.pathspec, client_id)

  if stat.S_ISDIR(stat_response.st_mode):
    fd = aff4.FACTORY.Create(stat_response.aff4path, "VFSDirectory",
                             mode="w", token=token)
  else:
    fd = aff4.FACTORY.Create(stat_response.aff4path, "VFSFile", mode="w",
                             token=token)

  fd.Set(fd.Schema.STAT(stat_response))
  fd.Set(fd.Schema.PATHSPEC(stat_response.pathspec))
  fd.Close(sync=sync)


class ListDirectoryArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.ListDirectoryArgs


class ListDirectory(flow.GRRFlow):
  """List files in a directory."""

  category = "/Filesystem/"
  args_type = ListDirectoryArgs
  behaviours = flow.GRRFlow.behaviours + "ADVANCED"

  @flow.StateHandler(next_state=["List", "Stat"])
  def Start(self):
    """Issue a request to list the directory."""
    self.CallClient("StatFile", pathspec=self.state.args.pathspec,
                    next_state="Stat")

    # We use data to pass the path to the callback:
    self.CallClient("ListDirectory", pathspec=self.state.args.pathspec,
                    next_state="List")

  @flow.StateHandler()
  def Stat(self, responses):
    """Save stat information on the directory."""
    # Did it work?
    if not responses.success:
      self.Error("Could not stat directory: %s" % responses.status)

    else:
      # Keep the stat response for later.
      self.state.Register("stat", rdfvalue.StatEntry(responses.First()))
      self.state.Register("directory_pathspec", self.state.stat.pathspec)

      # The full path of the object is the combination of the client_id and the
      # path.
      self.state.Register("urn", aff4.AFF4Object.VFSGRRClient.PathspecToURN(
          self.state.directory_pathspec, self.client_id))

  @flow.StateHandler()
  def List(self, responses):
    """Collect the directory listing and store in the datastore."""
    if not responses.success:
      raise flow.FlowError(str(responses.status))

    self.Status("Listed %s", self.state.urn)

    # The AFF4 object is opened for writing with an asyncronous close for speed.
    fd = aff4.FACTORY.Create(self.state.urn, "VFSDirectory", mode="w",
                             token=self.token)

    fd.Set(fd.Schema.PATHSPEC(self.state.directory_pathspec))
    fd.Set(fd.Schema.STAT(self.state.stat))

    fd.Close(sync=False)

    for st in responses:
      st = rdfvalue.StatEntry(st)
      CreateAFF4Object(st, self.client_id, self.token, sync=False)
      self.SendReply(st)  # Send Stats to parent flows.

    aff4.FACTORY.Flush()

  @flow.StateHandler()
  def End(self):
    if self.state.urn:
      self.Notify("ViewObject", self.state.urn,
                  u"Listed {0}".format(self.state.args.pathspec))


class IteratedListDirectory(ListDirectory):
  """A Flow to retrieve a directory listing using an iterator.

  This flow is an example for how to use the iterated client actions. Normally
  you do not need to call this flow - a ListDirectory flow is enough.
  """

  category = None

  @flow.StateHandler(next_state="List")
  def Start(self):
    """Issue a request to list the directory."""
    self.state.Register("responses", [])
    self.state.Register("urn", None)

    # We use data to pass the path to the callback:
    self.state.Register("request", rdfvalue.ListDirRequest(
        pathspec=self.state.args.pathspec))

    # For this example we will use a really small number to force many round
    # trips with the client. This is a performance killer.
    self.state.request.iterator.number = 50

    self.CallClient("IteratedListDirectory", self.state.request,
                    next_state="List")

  @flow.StateHandler(next_state="List")
  def List(self, responses):
    """Collect the directory listing and store in the data store."""
    if not responses.success:
      raise flow.FlowError(str(responses.status))

    if responses:
      for response in responses:
        self.state.responses.append(response)

      self.state.request.iterator = responses.iterator
      self.CallClient("IteratedListDirectory", self.state.request,
                      next_state="List")
    else:
      self.StoreDirectory()

  def StoreDirectory(self):
    """Store the content of the directory listing in the AFF4 object."""
    # The full path of the object is the combination of the client_id and the
    # path.
    if not self.state.responses: return

    directory_pathspec = self.state.responses[0].pathspec.Dirname()

    urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(
        directory_pathspec, self.client_id)

    # First dir we get back is the main urn.
    if not self.state.urn: self.state.urn = urn

    fd = aff4.FACTORY.Create(urn, "VFSDirectory", token=self.token)
    fd.Close(sync=False)

    for st in self.state.responses:
      st = rdfvalue.StatEntry(st)
      CreateAFF4Object(st, self.client_id, self.token)
      self.SendReply(st)  # Send Stats to parent flows.

  @flow.StateHandler()
  def End(self):
    self.Notify("ViewObject", self.state.urn, "List of {0} completed.".format(
        self.state.args.pathspec))


class RecursiveListDirectoryArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.RecursiveListDirectoryArgs


class RecursiveListDirectory(flow.GRRFlow):
  """Recursively list directory on the client."""

  category = "/Filesystem/"

  args_type = RecursiveListDirectoryArgs

  @flow.StateHandler(next_state="ProcessDirectory")
  def Start(self):
    """List the initial directory."""
    # The first directory we listed.
    self.state.Register("first_directory", None)

    self.state.Register("dir_count", 0)
    self.state.Register("file_count", 0)

    self.CallClient("ListDirectory", pathspec=self.state.args.pathspec,
                    next_state="ProcessDirectory")

  @flow.StateHandler(next_state="ProcessDirectory")
  def ProcessDirectory(self, responses):
    """Recursively list the directory, and add to the timeline."""
    if responses.success:
      response = responses.First()

      if response is None:
        return

      directory_pathspec = response.pathspec.Dirname()

      urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(
          directory_pathspec, self.client_id)

      self.StoreDirectory(responses)

      # If the urn is too deep we quit to prevent recursion errors.
      if self.state.first_directory is None:
        self.state.first_directory = urn

      else:
        relative_name = urn.RelativeName(self.state.first_directory) or ""
        if len(relative_name.split("/")) >= self.state.args.max_depth:
          self.Log("Exceeded maximum path depth at %s.",
                   urn.RelativeName(self.state.first_directory))
          return

      for stat_response in responses:
        # Queue a list directory for each directory here, but do not follow
        # symlinks.
        if (not stat_response.symlink and
            stat.S_ISDIR(stat_response.st_mode)):
          self.CallClient("ListDirectory", pathspec=stat_response.pathspec,
                          next_state="ProcessDirectory")
          self.state.dir_count += 1
          if self.state.dir_count % 100 == 0:   # Log every 100 directories
            self.Status("Reading %s. (%d nodes, %d directories done)",
                        urn.RelativeName(self.state.first_directory),
                        self.state.file_count, self.state.dir_count)

      self.state.file_count += len(responses)

  def StoreDirectory(self, responses):
    """Stores all stat responses."""
    for st in responses:
      st = rdfvalue.StatEntry(st)
      CreateAFF4Object(st, self.client_id, self.token)
      self.SendReply(st)  # Send Stats to parent flows.

  @flow.StateHandler()
  def End(self):
    status_text = "Recursive Directory Listing complete %d nodes, %d dirs"
    urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(self.state.args.pathspec,
                                                     self.client_id)
    self.Notify("ViewObject", self.state.first_directory or urn,
                status_text % (self.state.file_count, self.state.dir_count))
    self.Status(status_text, self.state.file_count, self.state.dir_count)


class SlowGetFileArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.SlowGetFileArgs


class SlowGetFile(flow.GRRFlow):
  """Simple file retrieval."""

  category = "/Filesystem/"
  args_type = SlowGetFileArgs

  # Read in 32kb chunks
  CHUNK_SIZE = 1024 * 32

  # We have a maximum of this many chunk reads outstanding (about 10mb)
  _WINDOW_SIZE = 330

  @flow.StateHandler(next_state=["Hash", "Stat", "ReadBuffer"])
  def Start(self):
    """Get information about the file from the client."""
    self.state.Register("urn")
    self.state.Register("current_chunk_number", 0)

    # We first obtain information about how large the file is
    self.CallClient("StatFile", pathspec=self.state.args.pathspec,
                    next_state="Stat")

    # This flow relies on the fact that responses are always returned
    # in order:
    self.CallClient("HashFile", pathspec=self.state.args.pathspec,
                    next_state="Hash")

    # Read the first buffer
    self.CallClient("ReadBuffer", pathspec=self.state.args.pathspec, offset=0,
                    length=self.CHUNK_SIZE, next_state="ReadBuffer")

  @flow.StateHandler(next_state="ReadBuffer")
  def Stat(self, responses):
    """Retrieve the file size.

    We determine how to store the file based on its size.

    Args:
     responses: Standard state Responses object.

    Raises:
     IOError: if the stat() fails on the client.
    """
    # Did it work?
    if not responses.success:
      # Its better to raise rather than merely logging since it will make it to
      # the flow's protobuf and users can inspect the reason this flow failed.
      raise IOError("Could not stat file: %s" % responses.status)

    # Keep the stat response for later.
    self.state.Register("stat", rdfvalue.StatEntry(responses.First()))

    # Update the pathspec from the client.
    self.state.args.pathspec = self.state.stat.pathspec

  def FetchWindow(self):
    """Read ahead a number of buffers to fill the window."""
    # Read the first lot of chunks to save on round trips
    number_of_chunks_to_readahead = min(
        self.state.file_size/self.CHUNK_SIZE + 1 -
        self.state.current_chunk_number,
        self._WINDOW_SIZE)

    for _ in range(number_of_chunks_to_readahead):
      bytes_needed_to_read = (self.state.file_size -
                              self.CHUNK_SIZE * self.state.current_chunk_number)

      self.CallClient("ReadBuffer", pathspec=self.state.args.pathspec,
                      offset=self.state.current_chunk_number * self.CHUNK_SIZE,
                      length=min(self.CHUNK_SIZE, bytes_needed_to_read),
                      next_state="ReadBuffer")
      self.state.current_chunk_number += 1

  @flow.StateHandler()
  def Hash(self, responses):
    """Store the hash of the file."""
    # Did it work?
    if responses.success and responses:
      self.state.Register("file_hash", responses.First().data)
      self.Log("File hash is %s", self.state.file_hash.encode("hex"))

  @flow.StateHandler(next_state="ReadBuffer")
  def ReadBuffer(self, responses):
    """Read the buffer and write to the file."""
    # Did it work?
    if not responses.success:
      raise IOError("Error running ReadBuffer: %s" % responses.status)

    # Postpone creating the AFF4 object until we get at least one successful
    # buffer back.
    response = responses.First()

    # Initial packet
    if response.offset == 0:
      # Force creation of the new AFF4 object
      self.state.urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(
          self.state.args.pathspec, self.client_id)

      self.state.Register("file_size", self.state.stat.st_size)

      # Create the output file.
      fd = aff4.FACTORY.Create(self.state.urn, "VFSFile", mode="w",
                               token=self.token)

      fd.SetChunksize(self.state.args.aff4_chunk_size)
      hash_value = fd.Schema.HASH()
      hash_value.sha256 = self.state.file_hash
      fd.Set(hash_value)
      fd.Set(fd.Schema.STAT(self.state.stat))

      self.state.Register("fd", fd)

      # Now we know how large the file is we can fill the window
      self.FetchWindow()

    if not response:
      raise IOError("Missing response to ReadBuffer: %s" % responses.status)

    # We need to be synced to the file size.
    if self.state.fd.size != response.offset:
      raise flow.FlowError("File transfer out of sync.")

    self.state.fd.Write(response.data)

    # If the file is done, we dont hang around
    if self.state.fd.Tell() >= self.state.file_size:
      self.Terminate()

    offset_to_read = self.state.current_chunk_number * self.CHUNK_SIZE
    bytes_needed_to_read = (self.state.file_size -
                            self.CHUNK_SIZE * self.state.current_chunk_number)

    # Dont read past the end of file
    if offset_to_read < self.state.file_size:
      self.CallClient("ReadBuffer", pathspec=self.state.args.pathspec,
                      offset=offset_to_read,
                      length=min(bytes_needed_to_read, self.CHUNK_SIZE),
                      next_state="ReadBuffer")

    self.state.current_chunk_number += 1

  @flow.StateHandler()
  def End(self):
    """Finalize reading the file."""
    self.Notify("ViewObject", self.state.urn, "File transferred successfully")

    self.Status("Finished reading %s", self.state.args.pathspec.CollapsePath())

    # Notify any parent flows.
    self.SendReply(self.state.stat)

  def Save(self):
    if self.state.get("fd") is not None:
      # Update our status
      self.Status("Received %s/%s bytes.", self.state.fd.size,
                  self.state.file_size)
      self.state.fd.Flush()


class GlobArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.GlobArgs

  def Validate(self):
    """Ensure that the glob paths are valid."""
    self.paths.Validate()


class Glob(flow.GRRFlow):
  """Glob the filesystem for patterns.

  Returns:
    StatResponse messages, one for each matching file.
  """

  args_type = GlobArgs

  def ReportMatch(self, stat_response):
    """Called when we've found a matching a StatEntry."""
    CreateAFF4Object(stat_response, self.client_id, self.token)
    self.SendReply(stat_response)

  # A regex indicating if there are shell globs in this path.
  GLOB_MAGIC_CHECK = re.compile("[*?[]")

  # Maximum number of files to inspect in a single directory
  FILE_MAX_PER_DIR = 100000

  def ConvertGlobIntoPathComponents(self, pattern):
    """Converts a glob pattern into a list of pathspec components.

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
      m = rdfvalue.GlobExpression.RECURSION_REGEX.search(path_component)
      if m:
        path_component = path_component.replace(m.group(0), "*")

        component = rdfvalue.PathSpec(
            path=fnmatch.translate(path_component),
            path_options=rdfvalue.PathSpec.Options.RECURSIVE)

        # Allow the user to override the recursion depth.
        if m.group(1):
          component.recursion_depth = int(m.group(1))

      elif self.GLOB_MAGIC_CHECK.search(path_component):
        component = rdfvalue.PathSpec(
            path=fnmatch.translate(path_component),
            path_options=rdfvalue.PathSpec.Options.REGEX)
      else:
        component = rdfvalue.PathSpec(
            path=path_component,
            path_options=rdfvalue.PathSpec.Options.CASE_INSENSITIVE)

      components.append(component)

    return components

  @flow.StateHandler(next_state="ProcessEntry")
  def Start(self):
    """Starts the Glob.

    First we convert the pattern into regex components, and then we
    interpolate each component. Finally, we generate a cartesian product of all
    combinations.
    """
    self.state.Register("component_tree", {})
    patterns = []

    client = aff4.FACTORY.Open(self.client_id, token=self.token)

    # Transform the patterns by substitution of client attributes. When the
    # client has multiple values for an attribute, this generates multiple
    # copies of the pattern, one for each variation. e.g.:
    # /home/%%Usernames%%/* -> [ /home/user1/*, /home/user2/* ]
    for path in self.state.args.paths:
      patterns.extend(path.Interpolate(client=client))

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
      node = self.state.component_tree

      for component in self.ConvertGlobIntoPathComponents(pattern):
        node = node.setdefault(component.SerializeToString(), {})

    # Process the component tree from the root.
    root = rdfvalue.StatEntry()
    root.pathspec = self.state.args.root_path
    if not root.pathspec:
      root.pathspec.path = "/"
    # root_path.pathtype overridden by user-settable args.pathtype
    root.pathspec.pathtype = self.state.args.pathtype
    self.CallStateInline(messages=[root], next_state="ProcessEntry",
                         request_data=dict(component_path=[]))

  def FindNode(self, component_path):
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

  @flow.StateHandler(next_state="ProcessEntry")
  def ProcessEntry(self, responses):
    """Process the responses from the client."""
    if not responses.success:
      return

    component_path = responses.request_data["component_path"]
    node = self.FindNode(component_path)

    # If we get a response with an unfinished iterator then we missed some
    # files. Call Find on the client until we're done.
    if (responses.iterator and responses.iterator.state !=
        responses.iterator.State.FINISHED):
      findspec = rdfvalue.FindSpec(responses.request.request.args)
      findspec.iterator = responses.iterator
      self.CallClient("Find", findspec,
                      next_state="ProcessEntry",
                      request_data=responses.request_data)

    regexes_to_get = []
    recursions_to_get = {}
    for response in responses:
      # The Find client action does not return a StatEntry but a
      # FindSpec. Normalize to a StatEntry.
      if isinstance(response, rdfvalue.FindSpec):
        response = response.hit

      if node:
        # There are further components in the tree - iterate over them.
        for component_str, next_node in node.items():
          component = rdfvalue.PathSpec(component_str)
          next_component = component_path + [component_str]

          # Use the pathtype from the flow args.
          component.pathtype = self.state.args.pathtype
          if component.path_options == component.Options.RECURSIVE:
            recursions_to_get.setdefault(component.recursion_depth, []).append(
                component)
          elif component.path_options == component.Options.REGEX:
            regexes_to_get.append(component)

          elif component.path_options == component.Options.CASE_INSENSITIVE:
            # Check for the existence of the last node.
            if not next_node:
              pathspec = response.pathspec.Copy().AppendPath(component.path)
              request = rdfvalue.ListDirRequest(pathspec=pathspec)

              if response.st_mode == 0 or not stat.S_ISREG(response.st_mode):
                # If next node is empty, this node is a leaf node, we therefore
                # must stat it to check that it is there.
                self.CallClient(
                    "StatFile", request, next_state="ProcessEntry",
                    request_data=dict(component_path=next_component))

            else:
              pathspec = response.pathspec.Copy().AppendPath(component.path)

              # There is no need to go back to the client for intermediate paths
              # in the prefix tree, just emulate this by recursively calling
              # this state inline.
              self.CallStateInline(
                  [rdfvalue.StatEntry(pathspec=pathspec)],
                  next_state="ProcessEntry",
                  request_data=dict(component_path=next_component))

        if recursions_to_get:
          for depth, recursions in recursions_to_get.iteritems():
            path_regex = "(?i)^" + "$|^".join(
                set([c.path for c in recursions])) + "$"

            findspec = rdfvalue.FindSpec(pathspec=response.pathspec,
                                         cross_devs=True,
                                         max_depth=depth,
                                         path_regex=path_regex)

            findspec.iterator.number = self.FILE_MAX_PER_DIR
            self.CallClient("Find", findspec,
                            next_state="ProcessEntry",
                            request_data=dict(component_path=next_component))

        if regexes_to_get:
          path_regex = "(?i)^" + "$|^".join(
              set([c.path for c in regexes_to_get])) + "$"
          findspec = rdfvalue.FindSpec(pathspec=response.pathspec,
                                       max_depth=1,
                                       path_regex=path_regex)

          findspec.iterator.number = self.FILE_MAX_PER_DIR
          self.CallClient("Find", findspec,
                          next_state="ProcessEntry",
                          request_data=dict(component_path=next_component))

      else:
        # Node is empty representing a leaf node - we found a hit - report it.
        self.ReportMatch(response)
