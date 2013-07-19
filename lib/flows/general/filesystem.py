#!/usr/bin/env python
# Copyright 2010 Google Inc. All Rights Reserved.
"""These are filesystem related flows."""


import fnmatch
import os
import re
import stat

from grr.lib import aff4
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import type_info
from grr.lib import utils
from grr.lib.flows.general import grep
from grr.lib.flows.general import transfer
from grr.lib.flows.general import utilities


def CreateAFF4Object(stat_response, client_id, token, sync=False):
  """This creates a File or a Directory from a stat response."""

  urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(stat_response.pathspec,
                                                   client_id)
  if stat.S_ISDIR(stat_response.st_mode):
    fd = aff4.FACTORY.Create(urn, "VFSDirectory", mode="w", token=token)
  else:
    fd = aff4.FACTORY.Create(urn, "VFSFile", mode="w", token=token)

  fd.Set(fd.Schema.STAT(stat_response))
  fd.Set(fd.Schema.PATHSPEC(stat_response.pathspec))
  fd.Close(sync=sync)


class ListDirectory(flow.GRRFlow):
  """List files in a directory."""

  category = "/Filesystem/"

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.PathspecType(
          description="The pathspec for the directory to list."),
      )

  @flow.StateHandler(next_state=["List", "Stat"])
  def Start(self):
    """Issue a request to list the directory."""
    self.CallClient("StatFile", pathspec=self.state.pathspec, next_state="Stat")

    # We use data to pass the path to the callback:
    self.CallClient("ListDirectory", pathspec=self.state.pathspec,
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
                  u"Listed {0}".format(self.state.pathspec))


class IteratedListDirectory(ListDirectory):
  """A Flow to retrieve a directory listing using an iterator.

  This flow is an example for how to use the iterated client actions. Normally
  you do not need to call this flow - a ListDirectory flow is enough.
  """

  category = None

  @flow.StateHandler(next_state="List")
  def Start(self, unused_response):
    """Issue a request to list the directory."""
    self.state.Register("responses", [])
    self.state.Register("urn", None)

    # We use data to pass the path to the callback:
    self.state.Register("request", rdfvalue.ListDirRequest(
        pathspec=self.state.pathspec))

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
        self.state.pathspec))


class RecursiveListDirectory(flow.GRRFlow):
  """Recursively list directory on the client."""

  category = "/Filesystem/"

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.PathspecType(
          description="The pathspec for the directory to list."),
      type_info.Integer(
          name="max_depth",
          description="Maximum depth to recurse",
          default=5),
      )

  @flow.StateHandler(next_state="ProcessDirectory")
  def Start(self):
    """List the initial directory."""
    # The first directory we listed.
    self.state.Register("first_directory", None)

    self.state.Register("dir_count", 0)
    self.state.Register("file_count", 0)

    self.CallClient("ListDirectory", pathspec=self.state.pathspec,
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
        if len(relative_name.split("/")) >= self.state.max_depth:
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
    self.Notify("ViewObject", self.state.first_directory, status_text % (
        self.state.file_count, self.state.dir_count))
    self.Status(status_text, self.state.file_count, self.state.dir_count)


class SlowGetFile(flow.GRRFlow):
  """Simple file retrieval."""

  category = "/Filesystem/"

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.PathspecType(
          description="The pathspec for the directory to list."),

      type_info.Integer(
          description=("Specifies how much data is saved in each AFF4Stream "
                       "chunk"),
          name="aff4_chunk_size",
          default=2**20,
          )
      )

  # Read in 32kb chunks
  CHUNK_SIZE = 1024 * 32

  # We have a maximum of this many chunk reads outstanding (about 10mb)
  _WINDOW_SIZE = 330

  @flow.StateHandler(next_state=["Hash", "Stat", "ReadBuffer"])
  def Start(self):
    """Get information about the file from the client."""

    self.state.Register("current_chunk_number", 0)

    # We first obtain information about how large the file is
    self.CallClient("StatFile", pathspec=self.state.pathspec,
                    next_state="Stat")

    # This flow relies on the fact that responses are always returned
    # in order:
    self.CallClient("HashFile", pathspec=self.state.pathspec,
                    next_state="Hash")

    # Read the first buffer
    self.CallClient("ReadBuffer", pathspec=self.state.pathspec, offset=0,
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
    self.state.pathspec = self.state.stat.pathspec

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

      self.CallClient("ReadBuffer", pathspec=self.state.pathspec,
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
          self.state.pathspec, self.client_id)

      self.state.Register("file_size", self.state.stat.st_size)

      # Create the output file.
      fd = aff4.FACTORY.Create(self.state.urn, "VFSFile", mode="w",
                               token=self.token)

      fd.SetChunksize(self.state.aff4_chunk_size)
      fd.Set(fd.Schema.HASH(self.state.file_hash))
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
      self.CallClient("ReadBuffer", pathspec=self.state.pathspec,
                      offset=offset_to_read,
                      length=min(bytes_needed_to_read, self.CHUNK_SIZE),
                      next_state="ReadBuffer")

    self.state.current_chunk_number += 1

  @flow.StateHandler()
  def End(self):
    """Finalize reading the file."""
    self.Notify("ViewObject", self.state.urn, "File transferred successfully")

    self.Status("Finished reading %s", self.state.pathspec.CollapsePath())

    # Notify any parent flows.
    self.SendReply(self.state.stat)

  def Save(self):
    if self.state.get("fd") is not None:
      # Update our status
      self.Status("Received %s/%s bytes.", self.state.fd.size,
                  self.state.file_size)
      self.state.fd.Flush()


class Glob(flow.GRRFlow):
  """Glob the filesystem for patterns.

  Returns:
    StatResponse messages, one for each matching file.
  """

  interpolated_regex = re.compile(r"%%([^%]+?)%%")

  # Grouping pattern: e.g. {test.exe,foo.doc,bar.txt}
  grouping_pattern = re.compile("{([^}]+)}")

  # A regex indicating if there are shell globs in this path.
  glob_magic_check = re.compile("[*?[]")

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.InterpolatedList(
          description=("A list of paths to glob that can contain %% "
                       "expansions"),
          name="paths",
          validator=type_info.String()
          ),
      type_info.PathTypeEnum(
          description="Type of access to glob in."),
      )

  def Cartesian(self, components):
    """Generates all cartesian products of the list of components.

    This essentially produces all possible combinations obtained by the
    components list. For example consider the components list:

    c = [("a", "b"), ("c",), ("d", "e")]

    cartesian(c) => ['acd', 'ace', 'bcd', 'bce']

    Args:
      components: A list of lists of strings.

    Yields:
      Strings build by concatenating every possibility in the components set.
    """
    if not components:
      yield []

    else:
      for comb in components[0]:
        for suffix in self.Cartesian(components[1:]):
          yield [comb] + suffix

  def InterpolateGrouping(self, pattern):
    """Interpolate inline globbing groups."""
    components = []
    offset = 0
    for match in self.grouping_pattern.finditer(pattern):
      components.append([pattern[offset:match.start()]])

      # Expand the attribute into the set of possibilities:
      alternatives = match.group(1).split(",")
      components.append(set(alternatives))
      offset = match.end()

    components.append([pattern[offset:]])
    # Now calculate the cartesian products of all these sets to form all
    # strings.
    for vector in self.Cartesian(components):
      yield "".join(vector)

  def InterpolateAttributes(self, pattern, client):
    """Interpolate all client attributes in pattern.

    Args:
      pattern: A string with potential interpolation markers. For example:
        "/home/[%Usernames%]/Downloads/"
      client: The client VFSGRRClient object we interpolate parameters from.

    Yields:
      All unique strings generated by expanding the pattern.
    """
    components = []
    offset = 0
    for match in self.interpolated_regex.finditer(pattern):
      components.append([pattern[offset:match.start()]])
      # Expand the attribute into the set of possibilities:
      alternatives = []

      # Only get the newest attribute that matches the pattern.
      for rdf_value in client.GetValuesForAttribute(
          match.group(1), only_one=True):

        # Treat string as special because its an iterable :-(
        if isinstance(rdf_value, basestring):
          alternatives.append(rdf_value)
        else:
          for value in rdf_value:
            value = utils.SmartUnicode(value)
            if value:
              alternatives.append(value)

      components.append(set(alternatives))
      offset = match.end()

    components.append([pattern[offset:]])

    # Now calculate the cartesian products of all these sets to form all
    # strings.
    for vector in self.Cartesian(components):
      yield "".join(vector)

  def GlobPath(self, path):
    """Takes a path with possible globs and returns split components.

    For example:
    path = "/home/lib/*/foo/*.exe"

    returns: ['home/lib', '*', 'foo', '*.exe']

    Args:
      path: A string with shell globs.
    Returns:
      a list of path components.
    """
    components = []
    tmp = ""

    for path_component in path.split("/"):
      if self.glob_magic_check.search(path_component):
        if tmp:
          components.append(tmp)

        tmp = ""
        components.append(fnmatch.translate(path_component))
      else:
        tmp = os.path.join(tmp, path_component)

    if tmp:
      components.append(tmp)

    return components

  def ReportMatch(self, stat_response):
    """Called when we've found a matching a pathspec."""
    urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(stat_response.pathspec,
                                                     self.client_id)
    self.Notify("ViewObject", urn, u"Glob matched")
    self.Status("Glob Matched %s", urn)
    self.SendReply(stat_response)
    CreateAFF4Object(stat_response, self.client_id, self.token)

  def ProceedIntoDirectory(self, stat_response, component_index,
                           pathspec_index):
    """Called when we want to apply next pathspec component to a directory."""
    self.CallClient("ListDirectory", pathspec=stat_response.pathspec,
                    next_state="ProcessDirectory",
                    request_data=dict(
                        component_index=component_index,
                        pathspec_index=pathspec_index))

  @flow.StateHandler(next_state="ProcessStatFile")
  def Start(self):
    """Starts the Glob.

    First we convert the pattern into regex components, and then we
    interpolate each component. Finally, we generate a cartesian product of all
    combinations.
    """
    self.state.Register("patterns", set())

    # Expand the glob into a list of paths.
    # e.g. /usr/lib/*.exe -> ['/usr/lib', '.*.exe']
    client = aff4.FACTORY.Open(self.client_id, token=self.token)

    # Transform the patterns by substitution:
    for path in self.state.paths:
      for pattern in self.InterpolateAttributes(path, client):
        # Normalize the component path (this allows us to resolve ../
        # sequences).
        norm_pattern = utils.NormalizePath(pattern.replace("\\", "/"))

        for p in self.InterpolateGrouping(norm_pattern):
          self.state.patterns.add(p)

    # Now prepare a pathspec for each pattern.
    self.state.Register("pathspecs", [])

    for pattern in self.state.patterns:
      pathspec_components = []
      self.state.pathspecs.append(pathspec_components)

      for component in self.GlobPath(pattern):
        component = rdfvalue.PathSpec(
            path=component, pathtype=int(self.state.pathtype))

        pathspec_components.append(component)

    # At this point self.pathspecs is a list of pathspec components we need to
    # search - issue a Stat on each to see if it exists.
    for i, pathspec in enumerate(self.state.pathspecs):
      if pathspec:
        self.CallClient("StatFile",
                        # Only look for the first component.
                        pathspec=pathspec[0],
                        next_state="ProcessStatFile",
                        request_data=dict(component_index=0,
                                          pathspec_index=i))

  @flow.StateHandler(next_state="ProcessDirectory")
  def ProcessStatFile(self, responses):
    """ProcessStatFile is used for glob pathspec components without stars."""
    # If response is successful, we may safely proceed to the next component
    # in glob pathspec, or report a match if we're at the last component.
    if not responses.success:
      return

    component_index = responses.request_data["component_index"]

    pathspec_index = responses.request_data["pathspec_index"]
    pathspec = self.state.pathspecs[pathspec_index]

    for response in responses:
      response = rdfvalue.StatEntry(response)

      # We are at the final component - report the hit.
      if len(pathspec) <= component_index + 1:
        self.ReportMatch(response)
      else:
        self.ProceedIntoDirectory(response, component_index + 1, pathspec_index)

  @flow.StateHandler(next_state=["ProcessDirectory", "ProcessStatFile"])
  def ProcessDirectory(self, responses):
    """Receive the directory contents and match against the regex."""
    if not responses.success:
      return

    pathspec_index = responses.request_data["pathspec_index"]
    component_index = responses.request_data["component_index"]

    # This is the current component we are working on.
    pathspec = self.state.pathspecs[pathspec_index]
    component = pathspec[component_index]
    subcomponents = component.path.split("/")

    # Any files matching this glob will be reported. We also recurse into any
    # directories matching this pattern.
    regex = re.compile(subcomponents[0], flags=re.I | re.S | re.M)

    for response in responses:
      response = rdfvalue.StatEntry(response)
      basename = response.pathspec.Basename()

      if not regex.match(basename):
        continue

      # If component is something like a/b/c, proceed with a StatFile instead
      # of ListDirectory.
      if len(subcomponents) > 1:
        pathspec = response.pathspec.Dirname().Append(component)
        self.CallClient("StatFile",
                        pathspec=pathspec,
                        next_state="ProcessStatFile",
                        request_data=dict(component_index=component_index,
                                          pathspec_index=pathspec_index))
      else:
        # We are at the final component - report the hit.
        if len(pathspec) <= component_index + 1:
          self.ReportMatch(response)
        else:
          self.ProceedIntoDirectory(response, component_index + 1,
                                    pathspec_index)


class GlobAndRunFlow(flow.GRRFlow):
  """Baseclass for flows that run a glob and use the results in another flow."""

  flow_class = None  # The flow to run.
  flow_typeinfo = Glob.flow_typeinfo

  def InjectPathspec(self, args=None, new_pathspec=None):
    """Injects the pathspec returned into the subflow parameter dict."""

    args["pathspec"] = new_pathspec

  @flow.StateHandler(next_state=["StartSubFlow"])
  def Start(self):
    """Run the glob first."""

    glob_args = {}
    for parameter in Glob.flow_typeinfo:
      glob_args[parameter.name] = self.state.get(parameter.name)

    self.CallFlow("Glob", next_state="StartSubFlow", **glob_args)

  @flow.StateHandler(next_state=["Done"])
  def StartSubFlow(self, responses):
    if not responses.success:
      raise flow.FlowError("Error while running the Glob subflow.")
    elif not responses:
      self.Log("Glob did not return any results.")
    else:
      self.Log("Glob returned %d results." % len(responses))

      for response in responses:

        args = {}
        for parameter in self.flow_class.flow_typeinfo:
          args[parameter.name] = self.state.get(parameter.name)

        self.InjectPathspec(args=args, new_pathspec=response.pathspec)

        self.CallFlow(self.flow_class.__name__, next_state="Done", **args)

  @flow.StateHandler()
  def Done(self, responses):
    # Just send the results to the parent.
    if responses.success:
      for response in responses:
        self.SendReply(response)


class GlobAndDownload(GlobAndRunFlow):
  category = "/Filesystem/Glob/"

  flow_class = transfer.GetFile

  flow_typeinfo = (GlobAndRunFlow.flow_typeinfo +
                   transfer.GetFile.flow_typeinfo.Remove("pathspec"))


class GlobAndGrep(GlobAndRunFlow):
  """A flow that runs a glob first and then issues a grep on the results."""
  category = "/Filesystem/Glob/"

  flow_class = grep.Grep
  flow_typeinfo = (GlobAndRunFlow.flow_typeinfo +
                   grep.Grep.flow_typeinfo.Remove("request") +
                   type_info.TypeDescriptorSet(
                       type_info.NoTargetGrepspecType(name="request")))

  def InjectPathspec(self, args=None, new_pathspec=None):
    """Injects the pathspec returned into the subflow parameter dict."""
    grep_request = args.setdefault("request", rdfvalue.GrepSpec())
    grep_request.target = new_pathspec


class GlobAndDownloadDirectory(GlobAndRunFlow):
  category = "/Filesystem/Glob/"

  flow_class = utilities.DownloadDirectory
  flow_typeinfo = (GlobAndRunFlow.flow_typeinfo +
                   utilities.DownloadDirectory.flow_typeinfo.Remove("pathspec"))


class GlobAndListDirectory(GlobAndRunFlow):
  category = "/Filesystem/Glob/"

  flow_class = ListDirectory
  flow_typeinfo = (GlobAndRunFlow.flow_typeinfo +
                   ListDirectory.flow_typeinfo.Remove("pathspec"))


class GlobAndListDirectoryRecursive(GlobAndRunFlow):
  category = "/Filesystem/Glob/"

  flow_class = RecursiveListDirectory
  flow_typeinfo = (GlobAndRunFlow.flow_typeinfo +
                   RecursiveListDirectory.flow_typeinfo.Remove("pathspec"))
