#!/usr/bin/env python
"""Client actions related to searching files and directories."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import functools
import logging
import stat

from grr_response_client import actions
from grr_response_client import vfs
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import flows as rdf_flows


class Find(actions.IteratedAction):
  """Recurses through a directory returning files which match conditions."""
  in_rdfvalue = rdf_client_fs.FindSpec
  out_rdfvalues = [rdf_client_fs.FindSpec]

  # The filesystem we are limiting ourselves to, if cross_devs is false.
  filesystem_id = None

  def ListDirectory(self, pathspec, state, depth=0):
    """A recursive generator of files."""
    # Limit recursion depth
    if depth >= self.request.max_depth:
      return

    try:
      fd = vfs.VFSOpen(pathspec, progress_callback=self.Progress)
      files = fd.ListFiles(ext_attrs=self.request.collect_ext_attrs)
    except (IOError, OSError) as e:
      if depth == 0:
        # We failed to open the directory the server asked for because dir
        # doesn't exist or some other reason. So we set status and return
        # back to the caller ending the Iterator.
        self.SetStatus(rdf_flows.GrrStatus.ReturnedStatus.IOERROR, e)
      else:
        # Can't open the directory we're searching, ignore the directory.
        logging.info("Find failed to ListDirectory for %s. Err: %s", pathspec,
                     e)
      return

    # If we are not supposed to cross devices, and don't know yet
    # which device we are on, we need to find out.
    if not self.request.cross_devs and self.filesystem_id is None:
      dir_stat = fd.Stat()
      self.filesystem_id = dir_stat.st_dev

    # Recover the start point for this directory from the state dict so we can
    # resume.
    start = state.get(pathspec.CollapsePath(), 0)

    for i, file_stat in enumerate(files):
      # Skip the files we already did before
      if i < start:
        continue

      if stat.S_ISDIR(file_stat.st_mode):
        # Do not traverse directories in a different filesystem.
        if self.request.cross_devs or self.filesystem_id == file_stat.st_dev:
          for child_stat in self.ListDirectory(file_stat.pathspec, state,
                                               depth + 1):
            yield child_stat

      state[pathspec.CollapsePath()] = i + 1
      yield file_stat

    # Now remove this from the state dict to prevent it from getting too large
    try:
      del state[pathspec.CollapsePath()]
    except KeyError:
      pass

  def TestFileContent(self, file_stat):
    """Checks the file for the presence of the regular expression."""
    # Content regex check
    try:

      data = ""
      with vfs.VFSOpen(
          file_stat.pathspec, progress_callback=self.Progress) as fd:
        # Only read this much data from the file.
        while fd.Tell() < self.request.max_data:
          data_read = fd.read(1024000)
          if not data_read:
            break
          data += data_read

          # Got it.
          if self.request.data_regex.Search(data):
            return True

          # Keep a bit of context from the last buffer to ensure we dont miss a
          # match broken by buffer. We do not expect regex's to match something
          # larger than about 100 chars.
          data = data[-100:]

    except (IOError, KeyError):
      pass

    return False

  def BuildChecks(self, request):
    """Parses request and returns a list of filter callables.

    Each callable will be called with the StatEntry and returns True if the
    entry should be suppressed.

    Args:
      request: A FindSpec that describes the search.

    Returns:
      a list of callables which return True if the file is to be suppressed.
    """
    result = []
    if request.HasField("start_time") or request.HasField("end_time"):

      def FilterTimestamp(file_stat, request=request):
        return file_stat.HasField("st_mtime") and (
            file_stat.st_mtime < request.start_time or
            file_stat.st_mtime > request.end_time)

      result.append(FilterTimestamp)

    if request.HasField("min_file_size") or request.HasField("max_file_size"):

      def FilterSize(file_stat, request=request):
        return file_stat.HasField("st_size") and (
            file_stat.st_size < request.min_file_size or
            file_stat.st_size > request.max_file_size)

      result.append(FilterSize)

    if request.HasField("perm_mode"):

      def FilterPerms(file_stat, request=request):
        return (file_stat.st_mode & request.perm_mask) != request.perm_mode

      result.append(FilterPerms)

    if request.HasField("uid"):

      def FilterUID(file_stat, request=request):
        return file_stat.st_uid != request.uid

      result.append(FilterUID)

    if request.HasField("gid"):

      def FilterGID(file_stat, request=request):
        return file_stat.st_gid != request.gid

      result.append(FilterGID)

    if request.HasField("path_regex"):
      regex = request.path_regex

      def FilterPath(file_stat, regex=regex):
        """Suppress any filename not matching the regular expression."""
        return not regex.Search(file_stat.pathspec.Basename())

      result.append(FilterPath)

    if request.HasField("data_regex"):

      def FilterData(file_stat, **_):
        """Suppress files that do not match the content."""
        return not self.TestFileContent(file_stat)

      result.append(FilterData)

    return result

  def Iterate(self, request, client_state):
    """Restores its way through the directory using an Iterator."""
    self.request = request
    filters = self.BuildChecks(request)
    limit = request.iterator.number

    # TODO(user): What is a reasonable measure of work here?
    for count, f in enumerate(
        self.ListDirectory(request.pathspec, client_state)):
      self.Progress()

      # Ignore this file if any of the checks fail.
      if not any((check(f) for check in filters)):
        self.SendReply(rdf_client_fs.FindSpec(hit=f))

      # We only check a limited number of files in each iteration. This might
      # result in returning an empty response - but the iterator is not yet
      # complete. Flows must check the state of the iterator explicitly.
      if count >= limit - 1:
        logging.debug("Processed %s entries, quitting", count)
        return

    # End this iterator
    request.iterator.state = rdf_client_action.Iterator.State.FINISHED


class Grep(actions.ActionPlugin):
  """Search a file for a pattern."""
  in_rdfvalue = rdf_client_fs.GrepSpec
  out_rdfvalues = [rdf_client.BufferReference]

  def FindRegex(self, regex, data):
    """Search the data for a hit."""
    for match in regex.FindIter(data):
      yield (match.start(), match.end())

  def FindLiteral(self, pattern, data):
    """Search the data for a hit."""
    pattern = utils.Xor(pattern, self.xor_in_key)

    offset = 0
    while 1:
      # We assume here that data.find does not make a copy of pattern.
      offset = data.find(pattern, offset)

      if offset < 0:
        break

      yield (offset, offset + len(pattern))

      offset += 1

  BUFF_SIZE = 1024 * 1024 * 10
  ENVELOPE_SIZE = 1000
  HIT_LIMIT = 10000

  def Run(self, args):
    """Search the file for the pattern.

    This implements the grep algorithm used to scan files. It reads
    the data in chunks of BUFF_SIZE (10 MB currently) and can use
    different functions to search for matching patterns. In every
    step, a buffer that is a bit bigger than the block size is used in
    order to return all the requested results. Specifically, a
    preamble is used in order to not miss any patterns that start in
    one block of data and end in the next and also a postscript buffer
    is kept such that the algorithm can return bytes trailing the
    pattern even if the pattern is at the end of one block.

    One block:
    -----------------------------
    | Pre | Data         | Post |
    -----------------------------
    Searching the pattern is done here:
    <------------------->

    The following block is constructed like this:
    -----------------------------
    | Pre | Data         | Post |
    -----------------------------
                         |
                   -----------------------------
                   | Pre | Data         | Post |
                   -----------------------------

    The preamble is filled from Data so every hit that happens to fall
    entirely into the preamble has to be discarded since it has
    already been discovered in the step before.

    Grepping for memory

    If this action is used to grep the memory of a client machine
    using one of the GRR memory acquisition drivers, we have to be
    very careful not to have any hits in the GRR process memory space
    itself. Therefore, if the input is a literal, it is XOR encoded
    and only visible in memory when the pattern is matched. This is
    done using bytearrays which guarantees in place updates and no
    leaking patterns. Also the returned data is encoded using a
    different XOR 'key'.

    This should guarantee that there are no hits when the pattern is
    not present in memory. However, since the data will be copied to
    the preamble and the postscript, a single pattern might in some
    cases produce multiple hits.

    Args:
      args: A protobuf describing the grep request.

    Raises:
      RuntimeError: No search pattern has been given in the request.

    """
    fd = vfs.VFSOpen(args.target, progress_callback=self.Progress)
    fd.Seek(args.start_offset)
    base_offset = args.start_offset

    self.xor_in_key = args.xor_in_key
    self.xor_out_key = args.xor_out_key

    if args.regex:
      find_func = functools.partial(self.FindRegex, args.regex)
    elif args.literal:
      find_func = functools.partial(self.FindLiteral, args.literal.AsBytes())
    else:
      raise RuntimeError("Grep needs a regex or a literal.")

    preamble_size = 0
    postscript_size = 0
    hits = 0
    data = b""
    while fd.Tell() < args.start_offset + args.length:

      # Base size to read is at most the buffer size.
      to_read = min(args.length, self.BUFF_SIZE,
                    args.start_offset + args.length - fd.Tell())
      # Read some more data for the snippet.
      to_read += self.ENVELOPE_SIZE - postscript_size
      read_data = fd.Read(to_read)

      data = data[-postscript_size - self.ENVELOPE_SIZE:] + read_data

      postscript_size = max(0, self.ENVELOPE_SIZE - (to_read - len(read_data)))
      data_size = len(data) - preamble_size - postscript_size

      if data_size == 0 and postscript_size == 0:
        break

      for (start, end) in find_func(data):
        # Ignore hits in the preamble.
        if end <= preamble_size:
          continue

        # Ignore hits in the postscript.
        if end > preamble_size + data_size:
          continue

        # Offset of file in the end after length.
        if end + base_offset - preamble_size > args.start_offset + args.length:
          break

        data_start = max(0, start - args.bytes_before)
        data_end = min(len(data), end + args.bytes_after)
        out_data = utils.Xor(data[data_start:data_end], self.xor_out_key)

        hits += 1
        self.SendReply(
            rdf_client.BufferReference(
                offset=base_offset + start - preamble_size,
                data=out_data,
                length=len(out_data),
                pathspec=fd.pathspec))

        if args.mode == rdf_client_fs.GrepSpec.Mode.FIRST_HIT:
          return

        if hits >= self.HIT_LIMIT:
          msg = utils.Xor(
              b"This Grep has reached the maximum number of hits"
              b" (%d)." % self.HIT_LIMIT, self.xor_out_key)
          self.SendReply(
              rdf_client.BufferReference(offset=0, data=msg, length=len(msg)))
          return

      self.Progress()

      base_offset += data_size

      # Allow for overlap with previous matches.
      preamble_size = min(len(data), self.ENVELOPE_SIZE)
