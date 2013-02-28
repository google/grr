#!/usr/bin/env python
# Copyright 2010 Google Inc.
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
  urn = None
  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.PathspecType(
          description="The pathspec for the directory to list."),
      )

  @flow.StateHandler(next_state=["List", "Stat"])
  def Start(self):
    """Issue a request to list the directory."""
    self.CallClient("StatFile", pathspec=self.pathspec, next_state="Stat")

    # We use data to pass the path to the callback:
    self.CallClient("ListDirectory", pathspec=self.pathspec, next_state="List")

  @flow.StateHandler()
  def Stat(self, responses):
    """Save stat information on the directory."""
    # Did it work?
    if not responses.success:
      self.Error("Could not stat directory: %s" % responses.status)

    else:
      # Keep the stat response for later.
      self.stat = rdfvalue.StatEntry(responses.First())
      self.directory_pathspec = self.stat.pathspec

      # The full path of the object is the combination of the client_id and the
      # path.
      self.urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(
          self.directory_pathspec, self.client_id)

  @flow.StateHandler()
  def List(self, responses):
    """Collect the directory listing and store in the datastore."""
    if not responses.success:
      raise flow.FlowError(str(responses.status))

    self.Status("Listed %s", self.urn)

    # The AFF4 object is opened for writing with an asyncronous close for speed.
    fd = aff4.FACTORY.Create(self.urn, "VFSDirectory", mode="w",
                             token=self.token)

    fd.Set(fd.Schema.PATHSPEC(self.directory_pathspec))
    fd.Set(fd.Schema.STAT(self.stat))

    fd.Close(sync=False)

    for st in responses:
      st = rdfvalue.StatEntry(st)
      CreateAFF4Object(st, self.client_id, self.token, False)
      self.SendReply(st)  # Send Stats to parent flows.

    aff4.FACTORY.Flush()

  @flow.StateHandler()
  def End(self):
    if self.urn:
      self.Notify("ViewObject", self.urn, u"Listed {0}".format(self.pathspec))


class IteratedListDirectory(ListDirectory):
  """A Flow to retrieve a directory listing using an iterator.

  This flow is an example for how to use the iterated client actions. Normally
  you do not need to call this flow - a ListDirectory flow is enough.
  """

  category = None

  @flow.StateHandler(next_state="List")
  def Start(self, unused_response):
    """Issue a request to list the directory."""
    # We use data to pass the path to the callback:
    self.request = rdfvalue.ListDirRequest(pathspec=self.pathspec)

    # For this example we will use a really small number to force many round
    # trips with the client. This is a performance killer.
    self.request.iterator.number = 50
    self.responses = []
    self.urn = None

    self.CallClient("IteratedListDirectory", self.request,
                    next_state="List")

  @flow.StateHandler(next_state="List")
  def List(self, responses):
    """Collect the directory listing and store in the data store."""
    if not responses.success:
      raise flow.FlowError(str(responses.status))

    if responses:
      for response in responses:
        self.responses.append(response)

      self.request.iterator = responses.iterator
      self.CallClient("IteratedListDirectory", self.request, next_state="List")
    else:
      self.StoreDirectory()

  def StoreDirectory(self):
    """Store the content of the directory listing in the AFF4 object."""
    # The full path of the object is the combination of the client_id and the
    # path.
    if not self.responses: return

    directory_pathspec = self.responses[0].pathspec.Dirname()

    urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(
        directory_pathspec, self.client_id)

    if not self.urn: self.urn = urn    # First dir we get back is the main urn.

    fd = aff4.FACTORY.Create(urn, "VFSDirectory", token=self.token)
    fd.Close(sync=False)

    for st in self.responses:
      st = rdfvalue.StatEntry(st)
      CreateAFF4Object(st, self.client_id, self.token)
      self.SendReply(st)  # Send Stats to parent flows.

  @flow.StateHandler()
  def End(self):
    self.Notify("ViewObject", self.urn, "List of {0} completed.".format(
        self.pathspec))


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
    self.first_directory = None

    self._dir_count = 0
    self._file_count = 0

    self.CallClient("ListDirectory", pathspec=self.pathspec,
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
      if self.first_directory is None:
        self.first_directory = urn

      else:
        relative_name = urn.RelativeName(self.first_directory) or ""
        if len(relative_name.split("/")) >= self.max_depth:
          self.Log("Exceeded maximum path depth at %s.",
                   urn.RelativeName(self.first_directory))
          return

      for stat_response in responses:
        # Queue a list directory for each directory here, but do not follow
        # symlinks.
        if (not stat_response.symlink and
            stat.S_ISDIR(stat_response.st_mode)):
          self.CallClient("ListDirectory", pathspec=stat_response.pathspec,
                          next_state="ProcessDirectory")
          self._dir_count += 1
          if self._dir_count % 100 == 0:   # Log every 100 directories
            self.Status("Reading %s. (%d nodes, %d directories done)",
                        urn.RelativeName(self.first_directory),
                        self._file_count, self._dir_count)

      self._file_count += len(responses)

  def StoreDirectory(self, responses):
    """Stores all stat responses."""
    for st in responses:
      st = rdfvalue.StatEntry(st)
      CreateAFF4Object(st, self.client_id, self.token)
      self.SendReply(st)  # Send Stats to parent flows.

  @flow.StateHandler()
  def End(self):
    status_text = "Recursive Directory Listing complete %d nodes, %d dirs"
    self.Notify("ViewObject", self.first_directory, status_text % (
        self._file_count, self._dir_count))
    self.Status(status_text, self._file_count, self._dir_count)


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
  _CHUNK_SIZE = 1024 * 32

  # We have a maximum of this many chunk reads outstanding (about 10mb)
  _WINDOW_SIZE = 330

  # Hold onto the aff4 file handle here.
  fd = None

  # This is the current_chunk_number we are up to.
  current_chunk_number = 0

  @flow.StateHandler(next_state=["Hash", "Stat", "ReadBuffer"])
  def Start(self):
    """Get information about the file from the client."""

    # We first obtain information about how large the file is
    self.CallClient("StatFile", pathspec=self.pathspec, next_state="Stat")

    # This flow relies on the fact that responses are always returned
    # in order:
    self.CallClient("HashFile", pathspec=self.pathspec, next_state="Hash")

    # Read the first buffer
    self.CallClient("ReadBuffer", pathspec=self.pathspec, offset=0,
                    length=self._CHUNK_SIZE, next_state="ReadBuffer")

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
    self.stat = rdfvalue.StatEntry(responses.First())

    # Update the pathspec from the client.
    self.pathspec = self.stat.pathspec

  def FetchWindow(self):
    """Read ahead a number of buffers to fill the window."""
    # Read the first lot of chunks to save on round trips
    number_of_chunks_to_readahead = min(
        self.file_size/self._CHUNK_SIZE + 1 - self.current_chunk_number,
        self._WINDOW_SIZE)

    for _ in range(number_of_chunks_to_readahead):
      bytes_needed_to_read = (
          self.file_size - self._CHUNK_SIZE * self.current_chunk_number)

      self.CallClient("ReadBuffer", pathspec=self.pathspec,
                      offset=self.current_chunk_number * self._CHUNK_SIZE,
                      length=min(self._CHUNK_SIZE, bytes_needed_to_read),
                      next_state="ReadBuffer")
      self.current_chunk_number += 1

  @flow.StateHandler()
  def Hash(self, responses):
    """Store the hash of the file."""
    # Did it work?
    if responses.success and responses:
      self.file_hash = responses.First().data
      self.Log("File hash is %s", self.file_hash)

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
      self.urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(
          self.pathspec, self.client_id)

      self.file_size = self.stat.st_size

      # Create the output file.
      self.fd = aff4.FACTORY.Create(self.urn, "VFSFile", mode="w",
                                    token=self.token)

      self.fd.Set(self.fd.Schema.CHUNKSIZE(self.aff4_chunk_size))
      self.fd.Set(self.fd.Schema.HASH(self.file_hash))
      self.fd.Set(self.fd.Schema.STAT(self.stat))

      # Now we know how large the file is we can fill the window
      self.FetchWindow()

    if not response:
      raise IOError("Missing response to ReadBuffer: %s" % responses.status)

    # We need to be synced to the file size.
    if self.fd.size != response.offset:
      raise flow.FlowError("File transfer out of sync.")

    self.fd.Write(response.data)

    # If the file is done, we dont hang around
    if self.fd.Tell() >= self.file_size:
      self.Terminate()

    offset_to_read = self.current_chunk_number * self._CHUNK_SIZE
    bytes_needed_to_read = (
        self.file_size - self._CHUNK_SIZE * self.current_chunk_number)

    # Dont read past the end of file
    if offset_to_read < self.file_size:
      self.CallClient("ReadBuffer", pathspec=self.pathspec,
                      offset=offset_to_read,
                      length=min(bytes_needed_to_read, self._CHUNK_SIZE),
                      next_state="ReadBuffer")

    self.current_chunk_number += 1

  @flow.StateHandler()
  def End(self):
    """Finalize reading the file."""
    self.Notify("ViewObject", self.urn, "File transferred successfully")

    self.Status("Finished reading %s", self.pathspec.CollapsePath())

    # Notify any parent flows.
    self.SendReply(self.stat)

  def Save(self):
    if self.fd is not None:
      # Update our status
      self.Status("Received %s/%s bytes.", self.fd.size, self.file_size)
      self.fd.Flush()


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
      type_info.List(
          description="A list of glob path descriptions.",
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

  @flow.StateHandler(next_state="ProcessDirectory")
  def Start(self):
    """Recursively list the directory, and add to the timeline."""
    # First we convert the pattern into regex components, and then we
    # interpolate each component. Finally we generate a cartesian product of all
    # combinations.
    self.patterns = set()

    # Expand the glob into a list of paths.
    # e.g. /usr/lib/*.exe -> ['/usr/lib', '.*.exe']
    client = aff4.FACTORY.Open(self.client_id, token=self.token)

    # Transform the patterns by substitution:
    for path in self.paths:
      for pattern in self.InterpolateAttributes(path, client):
        # Normalize the component path (this allows us to resolve ../
        # sequences).
        pattern = utils.NormalizePath(pattern.replace("\\", "/"))

        for pattern in self.InterpolateGrouping(pattern):
          self.patterns.add(pattern)

    # Now prepare a pathspec for each pattern.
    self.pathspecs = []

    for pattern in self.patterns:
      pathspec_components = []
      self.pathspecs.append(pathspec_components)

      for component in self.GlobPath(pattern):
        component = rdfvalue.RDFPathSpec(
            path=component, pathtype=int(self.pathtype))

        pathspec_components.append(component)

    # At this point self.pathspecs is a list of pathspec components we need to
    # search - issue a Stat on each to see if it exists.
    for i, pathspec in enumerate(self.pathspecs):
      if pathspec:
        self.CallClient("StatFile",
                        # Only look for the first component.
                        pathspec=pathspec[0],
                        next_state="ProcessDirectory",
                        request_data=dict(component_index=0,
                                          pathspec_index=i))

  @flow.StateHandler(next_state="ProcessDirectory")
  def ProcessDirectory(self, responses):
    """Receive the directory contents and match against the regex."""
    if not responses.success:
      return

    pathspec_index = responses.request_data["pathspec_index"]
    component_index = responses.request_data["component_index"]

    # This is the current component we are working on.
    pathspec = self.pathspecs[pathspec_index]

    component = pathspec[component_index]

    # Any files matching this glob will be reported. We also recurse into any
    # directories matching this pattern.
    regex = re.compile(os.path.basename(component.path), re.I | re.S | re.M)

    for response in responses:
      response = rdfvalue.StatEntry(response)

      basename = response.pathspec.Basename()

      if component_index and not regex.match(basename):
        continue

      # We are at the final component - report the hit.
      if len(pathspec) <= component_index + 1:
        urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(
            response.pathspec, self.client_id)

        self.Notify("ViewObject", urn, u"Glob matched")
        self.Status("Glob Matched %s", urn)
        self.SendReply(response)
        CreateAFF4Object(response, self.client_id, self.token)

      else:
        # Queue a list directory for each directory here, but do not follow
        # symlinks.
        if not response.symlink and stat.S_ISDIR(response.st_mode):
          self.CallClient("ListDirectory", pathspec=response.pathspec,
                          next_state="ProcessDirectory",
                          request_data=dict(component_index=component_index+1,
                                            pathspec_index=pathspec_index))


class Flow(type_info.String):
  """A flow name type."""

  def Validate(self, value):
    super(Flow, self).Validate(value)
    flow_cls = flow.GRRFlow.classes.get(value, None)
    if not flow_cls:
      raise type_info.TypeValueError("%s is not a valid flow name." % value)
    return flow_cls


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
      glob_args[parameter.name] = getattr(self, parameter.name)

    self.CallFlow("Glob", next_state="StartSubFlow", **glob_args)

  @flow.StateHandler(next_state=["Done"])
  def StartSubFlow(self, responses):
    if not responses.success:
      self.Log("Error while running Glob.")
    elif not responses:
      self.Log("Glob did not return any results.")
    else:
      self.Log("Glob returned %d results." % len(responses))

      for response in responses:

        args = {}
        for parameter in self.flow_class.flow_typeinfo:
          args[parameter.name] = getattr(self, parameter.name)

        self.InjectPathspec(args, response.pathspec)

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
                   transfer.GetFile.flow_typeinfo)


class GlobAndGrep(GlobAndRunFlow):
  """A flow that runs a glob first and then issues a grep on the results."""
  category = "/Filesystem/Glob/"

  flow_class = grep.Grep
  flow_typeinfo = (GlobAndRunFlow.flow_typeinfo +
                   grep.Grep.flow_typeinfo.Remove("request") +
                   type_info.TypeDescriptorSet(
                       type_info.EmptyTargetGrepspecType(name="request")))

  def InjectPathspec(self, args=None, new_pathspec=None):
    """Injects the pathspec returned into the subflow parameter dict."""
    grep_request = args.setdefault("request", rdfvalue.GrepSpec())
    grep_request.target = new_pathspec


class GlobAndDownloadDirectory(GlobAndRunFlow):
  category = "/Filesystem/Glob/"

  flow_class = utilities.DownloadDirectory
  flow_typeinfo = (GlobAndRunFlow.flow_typeinfo +
                   utilities.DownloadDirectory.flow_typeinfo)


class GlobAndListDirectory(GlobAndRunFlow):
  category = "/Filesystem/Glob/"

  flow_class = ListDirectory
  flow_typeinfo = (GlobAndRunFlow.flow_typeinfo +
                   ListDirectory.flow_typeinfo)


class GlobAndListDirectoryRecursive(GlobAndRunFlow):
  category = "/Filesystem/Glob/"

  flow_class = RecursiveListDirectory
  flow_typeinfo = (GlobAndRunFlow.flow_typeinfo +
                   RecursiveListDirectory.flow_typeinfo)
