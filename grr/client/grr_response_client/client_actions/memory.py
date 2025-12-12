#!/usr/bin/env python
"""Client actions dealing with memory."""

import abc
import collections
from collections.abc import Callable, Iterable, Iterator, Sequence
import contextlib
import io
import logging
import os
import platform
import re
import shutil
from typing import Any, IO, Optional

import psutil
import yara

from grr_response_client import actions
from grr_response_client import client_utils
from grr_response_client import process_error
from grr_response_client import streaming
from grr_response_client.client_actions import tempfiles
from grr_response_client.unprivileged import communication
from grr_response_client.unprivileged.memory import client as memory_client
from grr_response_client.unprivileged.memory import server as memory_server
from grr_response_client.unprivileged.proto import memory_pb2
from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import memory as rdf_memory
from grr_response_core.lib.rdfvalues import paths as rdf_paths


def ProcessIterator(
    pids: Iterable[int],
    process_regex_string: Optional[str],
    cmdline_regex_string: Optional[str],
    ignore_grr_process: bool,
    ignore_parent_processes: bool,
    error_list: list[rdf_memory.ProcessMemoryError],
) -> Iterator[psutil.Process]:
  """Yields all (psutil-) processes that match certain criteria.

  Args:
    pids: A list of pids. If given, only the processes with those pids are
      returned.
    process_regex_string: If given, only processes whose name matches the regex
      are returned.
    cmdline_regex_string: If given, only processes whose cmdline matches the
      regex are returned.
    ignore_grr_process: If True, the grr process itself will not be returned.
    ignore_parent_processes: Whether to skip scanning all parent processes of
      the GRR agent.
    error_list: All errors while handling processes are appended to this list.
      Type is repeated ProcessMemoryError.

  Yields:
    psutils.Process objects matching all criteria.
  """
  pids = set(pids)

  ignore_pids: set[int] = set()
  if ignore_grr_process:
    ignore_pids.add(psutil.Process().pid)
  if ignore_parent_processes:
    ignore_pids.update(_.pid for _ in psutil.Process().parents())

  if process_regex_string:
    process_regex = re.compile(process_regex_string)
  else:
    process_regex = None

  if cmdline_regex_string:
    cmdline_regex = re.compile(cmdline_regex_string)
  else:
    cmdline_regex = None

  if pids:
    process_iterator = []
    for pid in pids:
      try:
        process_iterator.append(psutil.Process(pid=pid))
      except Exception as e:  # pylint: disable=broad-except
        error_list.append(
            rdf_memory.ProcessMemoryError(
                process=rdf_client.Process(pid=pid),
                error=str(e),
            )
        )
  else:
    process_iterator = psutil.process_iter()

  for p in process_iterator:

    if p.pid in ignore_pids:
      continue

    try:
      process_name = p.name()
    except (
        psutil.AccessDenied,
        psutil.ZombieProcess,
        psutil.NoSuchProcess,
    ) as error:
      # Catch psutil errors that might prevent it from getting a process name.
      logging.error("failed to obtain process name: %s", error)
      process_name = ""

    if process_regex and not process_regex.search(process_name):
      continue

    try:
      cmdline = p.cmdline()
    except (
        psutil.AccessDenied,
        psutil.ZombieProcess,
        psutil.NoSuchProcess,
    ) as error:
      # psutil raises AccessDenied when getting the cmdline for special
      # processes like Registry or System on Windows.
      logging.error("failed to obtain process command line: %s", error)
      cmdline = []

    if cmdline_regex and not cmdline_regex.search(" ".join(cmdline)):
      continue

    yield p


def _ShouldIncludeError(
    policy: rdf_memory.YaraProcessScanRequest.ErrorPolicy,
    error: rdf_memory.ProcessMemoryError,
) -> bool:
  """Returns whether the error should be included in the flow response."""

  if policy == rdf_memory.YaraProcessScanRequest.ErrorPolicy.NO_ERRORS:
    return False

  if policy == rdf_memory.YaraProcessScanRequest.ErrorPolicy.CRITICAL_ERRORS:
    msg = error.error.lower()
    return "failed to open process" not in msg and "access denied" not in msg

  # Fall back to including all errors.
  return True


class YaraWrapperError(Exception):
  pass


class TooManyMatchesError(YaraWrapperError):
  pass


class YaraTimeoutError(YaraWrapperError):
  pass


class YaraWrapper(abc.ABC):
  """Wraps the Yara library."""

  @abc.abstractmethod
  def Match(
      self,
      process,
      chunks: Iterable[streaming.Chunk],
      deadline: rdfvalue.RDFDatetime,
  ) -> Iterator[rdf_memory.YaraMatch]:
    """Matches the rules in this instance against a chunk of process memory.

    Args:
      process: A process opened by `client_utils.OpenProcessForMemoryAccess`.
      chunks: Chunks to match. The chunks doesn't have `data` set.
      deadline: Deadline for the match.

    Yields:
      Matches matching the rules.

    Raises:
      YaraTimeoutError: if the operation timed out.
      TooManyMatchesError: if the scan produced too many matches.
      YaraWrapperError: in case of a general error.
    """

  def Close(self) -> None:
    """Releases all resources."""

  def Open(self) -> None:
    """Acquires necessary resources."""

  def __enter__(self) -> "YaraWrapper":
    self.Open()
    return self

  def __exit__(self, exc_type, exc_value, traceback) -> None:
    self.Close()


class DirectYaraWrapper(YaraWrapper):
  """Wrapper for the YARA library."""

  def __init__(
      self, rules_str: str, progress: Callable[[], None], context_window: int
  ):
    """Constructor.

    Args:
      rules_str: The YARA rules represented as string.
      progress: A progress callback
      context_window: The amount of bytes to store before and after the match.
    """
    self._rules_str = rules_str
    self._rules: Optional[yara.Rules] = None
    self._progress = progress
    self._context_window: int = context_window

  def Match(
      self,
      process,
      chunks: Iterable[streaming.Chunk],
      deadline: rdfvalue.RDFDatetime,
  ) -> Iterator[rdf_memory.YaraMatch]:
    for chunk in chunks:
      for match in self._MatchChunk(process, chunk, deadline):
        yield match
      self._progress()

  def _MatchChunk(
      self,
      process,
      chunk: streaming.Chunk,
      deadline: rdfvalue.RDFDatetime,
  ) -> Iterator[rdf_memory.YaraMatch]:
    """Matches one chunk of memory."""
    timeout_secs = (deadline - rdfvalue.RDFDatetime.Now()).ToInt(
        rdfvalue.SECONDS
    )
    if self._rules is None:
      self._rules = yara.compile(source=self._rules_str)
    data = process.ReadBytes(chunk.offset, chunk.amount)
    try:
      for m in self._rules.match(data=data, timeout=timeout_secs):
        # Note that for regexps in general it might be possible to
        # specify characters at the end of the string that are not
        # part of the returned match. In that case, this algorithm
        # might miss results in unlikely scenarios. We doubt that the
        # Yara library even allows such constructs but it's good to be
        # aware that this can happen.
        for yara_string_match in m.strings:
          rdf_match = None
          for sm_instance in yara_string_match.instances:
            if sm_instance.offset + sm_instance.matched_length > chunk.overlap:
              # We haven't seen this match before.
              rdf_match = rdf_memory.YaraMatch.FromLibYaraMatch(
                  m, data, self._context_window
              )
              for string_match in rdf_match.string_matches:
                string_match.offset += chunk.offset
              break
          if rdf_match is not None:
            yield rdf_match
            break
    except yara.TimeoutError as e:
      raise YaraTimeoutError() from e
    except yara.Error as e:
      # Yara internal error 30 is too many hits.
      if "internal error: 30" in str(e):
        raise TooManyMatchesError() from e
      else:
        raise YaraWrapperError() from e


class UnprivilegedYaraWrapper(YaraWrapper):
  """Wrapper for the sandboxed YARA library."""

  def __init__(self, rules_str: str, psutil_processes: list[psutil.Process]):
    """Constructor.

    Args:
      rules_str: The YARA rules represented as string.
      psutil_processes: List of processes that can be scanned using `Match`.
    """
    self._pid_to_serializable_file_descriptor: dict[int, int] = {}
    self._pid_to_exception: dict[int, Exception] = {}
    self._server: Optional[communication.Server] = None
    self._client: Optional[memory_client.Client] = None
    self._rules_str = rules_str
    self._rules_uploaded = False
    self._psutil_processes = psutil_processes
    self._pids = {p.pid for p in psutil_processes}

  def Open(self) -> None:
    with contextlib.ExitStack() as stack:
      file_descriptors = []
      for psutil_process in self._psutil_processes:
        try:
          process = stack.enter_context(
              client_utils.OpenProcessForMemoryAccess(psutil_process.pid)
          )
        except Exception as e:  # pylint: disable=broad-except
          # OpenProcessForMemoryAccess can raise any exception upon error.
          self._pid_to_exception[psutil_process.pid] = e
          continue
        self._pid_to_serializable_file_descriptor[psutil_process.pid] = (
            process.serialized_file_descriptor
        )
        file_descriptors.append(
            communication.FileDescriptor.FromSerialized(
                process.serialized_file_descriptor, communication.Mode.READ
            )
        )
      self._server = memory_server.CreateMemoryServer(file_descriptors)
      self._server.Start()
      self._client = memory_client.Client(self._server.Connect())

  def Close(self) -> None:
    if self._server is not None:
      self._server.Stop()

  def ContainsPid(self, pid: int) -> bool:
    return pid in self._pids

  def Match(
      self,
      process,
      chunks: Iterable[streaming.Chunk],
      deadline: rdfvalue.RDFDatetime,
      context_window: int = 0,
  ) -> Iterator[rdf_memory.YaraMatch]:
    timeout_secs = (deadline - rdfvalue.RDFDatetime.Now()).ToInt(
        rdfvalue.SECONDS
    )
    if self._client is None:
      raise ValueError("Client not instantiated.")
    if not self._rules_uploaded:
      self._client.UploadSignature(self._rules_str)
      self._rules_uploaded = True
    if process.pid not in self._pid_to_serializable_file_descriptor:
      raise (
          process_error.ProcessError(f"Failed to open process {process.pid}.")
      ) from self._pid_to_exception.get(process.pid)
    chunks_pb = [
        memory_pb2.Chunk(offset=chunk.offset, size=chunk.amount)
        for chunk in chunks
    ]
    overlap_end_map = {
        chunk.offset: chunk.offset + chunk.overlap for chunk in chunks
    }
    response = self._client.ProcessScan(
        self._pid_to_serializable_file_descriptor[process.pid],
        chunks_pb,
        timeout_secs,
        context_window,
    )
    if response.status == memory_pb2.ProcessScanResponse.Status.NO_ERROR:
      return self._ScanResultToYaraMatches(
          response.scan_result, overlap_end_map
      )
    elif (
        response.status
        == memory_pb2.ProcessScanResponse.Status.TOO_MANY_MATCHES
    ):
      raise TooManyMatchesError()
    elif response.status == memory_pb2.ProcessScanResponse.Status.TIMEOUT_ERROR:
      raise YaraTimeoutError()
    else:
      raise YaraWrapperError()

  def _ScanResultToYaraMatches(
      self, scan_result: memory_pb2.ScanResult, overlap_end_map: dict[int, int]
  ) -> Iterator[rdf_memory.YaraMatch]:
    """Converts a scan result from protobuf to RDF."""
    for rule_match in scan_result.scan_match:
      rdf_match = self._RuleMatchToYaraMatch(rule_match)
      for string_match, rdf_string_match in zip(
          rule_match.string_matches, rdf_match.string_matches
      ):
        if (
            rdf_string_match.offset + len(rdf_string_match.data)
            > overlap_end_map[string_match.chunk_offset]
        ):
          yield rdf_match
          break

  def _RuleMatchToYaraMatch(
      self, rule_match: memory_pb2.RuleMatch
  ) -> rdf_memory.YaraMatch:
    result = rdf_memory.YaraMatch()
    if rule_match.HasField("rule_name"):
      result.rule_name = rule_match.rule_name
    for string_match in rule_match.string_matches:
      result.string_matches.append(
          self._StringMatchToYaraStringMatch(string_match)
      )
    return result

  def _StringMatchToYaraStringMatch(
      self, string_match: memory_pb2.StringMatch
  ) -> rdf_memory.YaraStringMatch:
    """Builds a YaraStringMatch from a StringMatch proto object."""
    result = rdf_memory.YaraStringMatch()
    if string_match.HasField("string_id"):
      result.string_id = string_match.string_id
    if string_match.HasField("offset"):
      result.offset = string_match.offset
    if string_match.HasField("data"):
      result.data = string_match.data
    if string_match.HasField("context"):
      result.context = string_match.context
    return result


class BatchedUnprivilegedYaraWrapper(YaraWrapper):
  """Wrapper for the sandboxed YARA library with scans processes in batches.

  This is a wrapper for `UnprivilegedYaraWrapper` which scans processes in
  batches. The purpose is to avoid exceeding the maximal number of open file
  descriptors when using `UnprivilegedYaraWrapper`.
  """

  # Linux has a file descriptor limit of 1024 per process, use half of it.
  # Windows has a limit of 10k handles per process.
  BATCH_SIZE = 512

  def __init__(
      self,
      rules_str: str,
      psutil_processes: list[psutil.Process],
      context_window: Optional[int] = None,
  ):
    """Constructor.

    Args:
      rules_str: The YARA rules represented as string.
      psutil_processes: List of processes that can be scanned using `Match`.
      context_window: Amount of bytes surrounding the match to return.
    """

    self._batches: list[UnprivilegedYaraWrapper] = []

    for i in range(0, len(psutil_processes), self.BATCH_SIZE):
      process_batch = psutil_processes[i : i + self.BATCH_SIZE]
      self._batches.append(UnprivilegedYaraWrapper(rules_str, process_batch))

    self._current_batch = self._batches.pop(0)
    self._context_window = context_window or 0

  def Match(
      self,
      process,
      chunks: Iterable[streaming.Chunk],
      deadline: rdfvalue.RDFDatetime,
  ) -> Iterator[rdf_memory.YaraMatch]:
    if not self._current_batch.ContainsPid(process.pid):
      while True:
        if not self._batches:
          raise ValueError(
              "`_batches` is empty. "
              "Processes must be passed to `Match` in the same order as they "
              "appear in `psutil_processes`."
          )
        if self._batches[0].ContainsPid(process.pid):
          break
        self._batches.pop(0)
      self._current_batch.Close()
      self._current_batch = self._batches.pop(0)
      self._current_batch.Open()

    yield from self._current_batch.Match(
        process, chunks, deadline, self._context_window
    )

  def Open(self) -> None:
    self._current_batch.Open()

  def Close(self) -> None:
    self._current_batch.Close()


class YaraScanRequestMatcher:
  """Applies the yara matching function to a process under constraints of a scan_request."""

  MAX_BATCH_SIZE_CHUNKS = 100

  def __init__(self, yara_wrapper: YaraWrapper) -> None:
    self._yara_wrapper = yara_wrapper

  def GetMatchesForProcess(
      self,
      psutil_process: psutil.Process,
      scan_request: rdf_memory.YaraProcessScanRequest,
  ) -> Sequence[rdf_memory.YaraMatch]:
    """Scans the memory of a process, applies scan_request constraints."""

    if scan_request.per_process_timeout:
      deadline = rdfvalue.RDFDatetime.Now() + scan_request.per_process_timeout
    else:
      deadline = rdfvalue.RDFDatetime.Now() + rdfvalue.Duration.From(
          1, rdfvalue.WEEKS
      )

    process = client_utils.OpenProcessForMemoryAccess(pid=psutil_process.pid)
    with process:
      matches = []

      try:
        for chunks in self._BatchIterateRegions(process, scan_request):
          for m in self._ScanRegion(process, chunks, deadline):
            matches.append(m)
            if 0 < scan_request.max_results_per_process <= len(matches):
              return matches
      except TooManyMatchesError:
        # We need to report this as a hit, not an error.
        return matches

    return matches

  def _ScanRegion(
      self,
      process,
      chunks: Iterable[streaming.Chunk],
      deadline: rdfvalue.RDFDatetime,
  ) -> Iterator[rdf_memory.YaraMatch]:
    assert self._yara_wrapper is not None
    yield from self._yara_wrapper.Match(process, chunks, deadline)

  # Windows has 1000-2000 regions per process.
  # There a lot of small regions consiting of 1 chunk only.
  # With sandboxing, using 1 RPC per region creates a significant overhead.
  # To avoid the overhead, chunks are grouped into batches which are in turn
  # send to the sandboxed process in 1 RPC.
  # Without sandboxing, the batching has no effect.
  def _BatchIterateRegions(
      self, process, scan_request: rdf_memory.YaraProcessScanRequest
  ) -> Iterator[list[streaming.Chunk]]:
    """Iterates over regions of a process."""
    streamer = streaming.Streamer(
        chunk_size=scan_request.chunk_size,
        overlap_size=scan_request.overlap_size,
    )
    batch = []
    batch_size_bytes = 0
    for region in client_utils.MemoryRegions(process, scan_request):
      chunks = streamer.StreamRanges(offset=region.start, amount=region.size)
      for chunk in chunks:
        batch.append(chunk)
        batch_size_bytes += chunk.amount
        if (
            len(batch) >= self.MAX_BATCH_SIZE_CHUNKS
            or batch_size_bytes >= scan_request.chunk_size
        ):
          yield batch
          batch = []
          batch_size_bytes = 0
    if batch:
      yield batch


class YaraProcessScan(actions.ActionPlugin):
  """Scans the memory of a number of processes using Yara."""

  in_rdfvalue = rdf_memory.YaraProcessScanRequest
  out_rdfvalues = [rdf_memory.YaraProcessScanResponse]

  # We don't want individual response messages to get too big so we send
  # multiple responses for 100 processes each.
  _RESULTS_PER_RESPONSE = 100

  def __init__(self, grr_worker=None):
    super().__init__(grr_worker=grr_worker)
    self._yara_process_matcher = None

  def _ScanProcess(
      self,
      process: psutil.Process,
      scan_request: rdf_memory.YaraProcessScanRequest,
      scan_response: rdf_memory.YaraProcessScanResponse,
      matcher: YaraScanRequestMatcher,
  ) -> None:
    rdf_process = rdf_client.Process.FromPsutilProcess(process)

    start_time = rdfvalue.RDFDatetime.Now()
    try:
      matches = matcher.GetMatchesForProcess(process, scan_request)
      scan_time = rdfvalue.RDFDatetime.Now() - start_time
      scan_time_us = scan_time.ToInt(rdfvalue.MICROSECONDS)
    except YaraTimeoutError:
      err = rdf_memory.ProcessMemoryError(
          process=rdf_process,
          error="Scanning timed out (%s)."
          % (rdfvalue.RDFDatetime.Now() - start_time),
      )
      if _ShouldIncludeError(scan_request.include_errors_in_results, err):
        scan_response.errors.Append(err)
      return
    except Exception as e:  # pylint: disable=broad-except
      err = rdf_memory.ProcessMemoryError(process=rdf_process, error=str(e))
      if _ShouldIncludeError(scan_request.include_errors_in_results, err):
        scan_response.errors.Append(err)
      return

    if matches:
      scan_response.matches.Append(
          rdf_memory.YaraProcessScanMatch(
              process=rdf_process, match=matches, scan_time_us=scan_time_us
          )
      )
    else:
      if scan_request.include_misses_in_results:
        scan_response.misses.Append(
            rdf_memory.YaraProcessScanMiss(
                process=rdf_process, scan_time_us=scan_time_us
            )
        )

  def _SaveSignatureShard(self, scan_request):
    """Writes a YaraSignatureShard received from the server to disk.

    Args:
      scan_request: The YaraProcessScanRequest sent by the server.

    Returns:
      The full Yara signature, if all shards have been received. Otherwise,
      None is returned.
    """

    def GetShardName(shard_index, num_shards):
      return "shard_%02d_of_%02d" % (shard_index, num_shards)

    signature_dir = os.path.join(
        tempfiles.GetDefaultGRRTempDirectory(),
        "Sig_%s" % self.session_id.Basename(),
    )
    # Create the temporary directory and set permissions, if it does not exist.
    tempfiles.EnsureTempDirIsSane(signature_dir)
    shard_path = os.path.join(
        signature_dir,
        GetShardName(
            scan_request.signature_shard.index,
            scan_request.num_signature_shards,
        ),
    )
    with io.open(shard_path, "wb") as f:
      f.write(scan_request.signature_shard.payload)

    dir_contents = set(os.listdir(signature_dir))
    all_shards = [
        GetShardName(i, scan_request.num_signature_shards)
        for i in range(scan_request.num_signature_shards)
    ]
    if dir_contents.issuperset(all_shards):
      # All shards have been received; delete the temporary directory and
      # return the full signature.
      full_signature = io.BytesIO()
      for shard in all_shards:
        with io.open(os.path.join(signature_dir, shard), "rb") as f:
          full_signature.write(f.read())
      shutil.rmtree(signature_dir, ignore_errors=True)
      return full_signature.getvalue().decode("utf-8")
    else:
      return None

  def Run(self, args):
    if args.yara_signature or not args.signature_shard.payload:
      raise ValueError(
          "A Yara signature shard is required, and not the full signature."
      )

    if args.num_signature_shards == 1:
      # Skip saving to disk if there is just one shard.
      yara_signature = args.signature_shard.payload.decode("utf-8")
    else:
      yara_signature = self._SaveSignatureShard(args)
      if yara_signature is None:
        # We haven't received the whole signature yet.
        return

    scan_request = args.Copy()
    scan_request.yara_signature = yara_signature
    scan_response = rdf_memory.YaraProcessScanResponse()
    processes = list(
        ProcessIterator(
            scan_request.pids,
            scan_request.process_regex,
            scan_request.cmdline_regex,
            scan_request.ignore_grr_process,
            scan_request.ignore_parent_processes,
            scan_response.errors,
        )
    )
    if not processes:
      err = rdf_memory.ProcessMemoryError(
          error="No matching processes to scan."
      )
      if _ShouldIncludeError(scan_request.include_errors_in_results, err):
        scan_response.errors.Append(err)
      self.SendReply(scan_response)
      return

    if self._UseSandboxing(args):
      yara_wrapper: YaraWrapper = BatchedUnprivilegedYaraWrapper(
          str(scan_request.yara_signature),
          processes,
          scan_request.context_window,
      )
    else:
      yara_wrapper: YaraWrapper = DirectYaraWrapper(
          str(scan_request.yara_signature),
          self.Progress,
          scan_request.context_window,
      )

    with yara_wrapper:
      matcher = YaraScanRequestMatcher(yara_wrapper)
      for process in processes:
        self.Progress()
        num_results = (
            len(scan_response.errors)
            + len(scan_response.matches)
            + len(scan_response.misses)
        )
        if num_results >= self._RESULTS_PER_RESPONSE:
          self.SendReply(scan_response)
          scan_response = rdf_memory.YaraProcessScanResponse()
        self._ScanProcess(
            process,
            scan_request,
            scan_response,
            matcher,
        )

      self.SendReply(scan_response)

  def _UseSandboxing(self, args: rdf_memory.YaraProcessScanRequest) -> bool:
    # Memory sandboxing is currently not supported on macOS.
    if platform.system() == "Darwin":
      return False
    if (
        args.implementation_type
        == rdf_memory.YaraProcessScanRequest.ImplementationType.DIRECT
    ):
      return False
    elif (
        args.implementation_type
        == rdf_memory.YaraProcessScanRequest.ImplementationType.SANDBOX
    ):
      return True
    else:
      return config.CONFIG["Client.use_memory_sandboxing"]


def _PrioritizeRegions(
    regions: Iterable[rdf_memory.ProcessMemoryRegion],
    prioritize_offsets: Iterable[int],
) -> Iterable[rdf_memory.ProcessMemoryRegion]:
  """Returns reordered `regions` to prioritize regions containing offsets.

  Args:
    regions: Iterable of ProcessMemoryRegions.
    prioritize_offsets: List of integers containing prioritized offsets.  Pass
      pre-sorted regions and offsets to improve this functions performance from
      O(n * log n) to O(n) respectively.

  Returns:
    An iterable of first all ProcessMemoryRegions that contain a prioritized
    offset, followed by all regions that do not contain a prioritized offset.
    All prioritized regions and all unprioritized regions are sorted by their
    starting address.
  """

  # Sort regions and offsets to be mononotically increasing and insert sentinel.
  all_regions = collections.deque(sorted(regions, key=lambda r: r.start))
  all_regions.append(None)
  region = all_regions.popleft()

  all_offsets = collections.deque(sorted(prioritize_offsets))
  all_offsets.append(None)
  offset = all_offsets.popleft()

  prio_regions = []
  nonprio_regions = []

  # This loop runs in O(max(|regions|, |offsets|)) with use of invariants:
  # - offset is increasing monotonically.
  # - region[n+1] end >= region[n+1] start >= region[n] start
  # Because memory regions could theoretically overlap, no relationship exists
  # between the end of region[n+1] and region[n].

  while region is not None and offset is not None:
    # pytype sees region as nullable
    if offset < region.start:  # pytype: disable=attribute-error
      # Offset is before the first region, thus cannot be contained in any
      # region. This could happen when some memory regions are unreadable.
      offset = all_offsets.popleft()
    # pytype sees region as nullable
    elif offset >= region.start + region.size:  # pytype: disable=attribute-error
      # Offset comes after the first region. The first region can not contain
      # any following offsets, because offsets increase monotonically.
      nonprio_regions.append(region)
      region = all_regions.popleft()
    else:
      # The first region contains the offset. Mark it as prioritized and
      # proceed with the next offset. All following offsets that are contained
      # in the current region are skipped with the first if-branch.
      prio_regions.append(region)
      region = all_regions.popleft()
      offset = all_offsets.popleft()

  all_regions.appendleft(region)  # Put back the current region or sentinel.
  all_regions.pop()  # Remove sentinel.

  # When there are fewer offsets than regions, remaining regions can be present
  # in `all_regions`.
  # pytype sees all_regions as possibly containing None
  return prio_regions + nonprio_regions + list(all_regions)  # pytype: disable=bad-return-type


def _ApplySizeLimit(
    regions: Iterable[rdf_memory.ProcessMemoryRegion], size_limit: int
) -> list[rdf_memory.ProcessMemoryRegion]:
  """Truncates regions so that the total size stays in size_limit."""
  total_size = 0
  regions_in_limit = []
  for region in regions:
    if total_size >= size_limit:
      break
    region.dumped_size = min(region.size, size_limit - total_size)
    regions_in_limit.append(region)
    total_size += region.dumped_size
  return regions_in_limit


class YaraProcessDump(actions.ActionPlugin):
  """Dumps a process to disk and returns pathspecs for GRR to pick up."""

  in_rdfvalue = rdf_memory.YaraProcessDumpArgs
  out_rdfvalues = [rdf_memory.YaraProcessDumpResponse]

  def _SaveMemDumpToFile(
      self,
      fd: IO[bytes],
      chunks: Iterator[streaming.Chunk],
  ) -> int:
    bytes_written = 0

    for chunk in chunks:
      if not chunk.data:
        return 0

      fd.write(chunk.data)
      bytes_written += len(chunk.data)

    return bytes_written

  def _SaveMemDumpToFilePath(
      self,
      filename: str,
      chunks: Iterator[streaming.Chunk],
  ) -> int:
    with open(filename, "wb") as fd:
      bytes_written = self._SaveMemDumpToFile(fd, chunks)

    # When getting read errors, we just delete the file and move on.
    if not bytes_written:
      try:
        os.remove(filename)
      except OSError:
        pass

    return bytes_written

  def _SaveRegionToDirectory(
      self,
      psutil_process: psutil.Process,
      process: Any,  # Each platform uses a specific type without common base.
      region: rdf_memory.ProcessMemoryRegion,
      tmp_dir: tempfiles.TemporaryDirectory,
      streamer: streaming.Streamer,
  ) -> Optional[rdf_paths.PathSpec]:
    end = region.start + region.size

    # _ReplaceDumpPathspecsWithMultiGetFilePathspec in DumpProcessMemory
    # flow asserts that MemoryRegions can be uniquely identified by their
    # file's basename.
    filename = "%s_%d_%x_%x.tmp" % (
        psutil_process.name(),
        psutil_process.pid,
        region.start,
        end,
    )
    filepath = os.path.join(tmp_dir.path, filename)

    chunks = streamer.StreamMemory(
        process, offset=region.start, amount=region.dumped_size
    )
    bytes_written = self._SaveMemDumpToFilePath(filepath, chunks)

    if not bytes_written:
      return None

    # TODO: Remove workaround after client_utils are fixed.
    canonical_path = client_utils.LocalPathToCanonicalPath(filepath)
    if not canonical_path.startswith("/"):
      canonical_path = "/" + canonical_path

    return rdf_paths.PathSpec(
        path=canonical_path, pathtype=rdf_paths.PathSpec.PathType.TMPFILE
    )

  def DumpProcess(
      self,
      psutil_process: psutil.Process,
      args: rdf_memory.YaraProcessScanRequest,
  ) -> rdf_memory.YaraProcessDumpInformation:
    response = rdf_memory.YaraProcessDumpInformation()
    response.process = rdf_client.Process.FromPsutilProcess(psutil_process)
    streamer = streaming.Streamer(chunk_size=args.chunk_size)

    with client_utils.OpenProcessForMemoryAccess(psutil_process.pid) as process:
      regions = list(client_utils.MemoryRegions(process, args))

      if args.prioritize_offsets:
        regions = _PrioritizeRegions(regions, args.prioritize_offsets)

      if args.size_limit:
        total_regions = len(regions)
        regions = _ApplySizeLimit(regions, args.size_limit)
        if len(regions) < total_regions:
          response.error = (
              "Byte limit exceeded. Writing {} of {} regions."
          ).format(len(regions), total_regions)
      else:
        for region in regions:
          region.dumped_size = region.size

      regions = sorted(regions, key=lambda r: r.start)

      with tempfiles.TemporaryDirectory(cleanup=False) as tmp_dir:
        for region in regions:
          self.Progress()
          pathspec = self._SaveRegionToDirectory(
              psutil_process, process, region, tmp_dir, streamer
          )
          if pathspec is not None:
            region.file = pathspec
            response.memory_regions.Append(region)

    return response

  def Run(
      self,
      args: rdf_memory.YaraProcessScanRequest,
  ) -> None:
    if args.prioritize_offsets and len(args.pids) != 1:
      raise ValueError(
          "Supplied prioritize_offsets {} for PIDs {} in YaraProcessDump. "
          "Required exactly one PID.".format(args.prioritize_offsets, args.pids)
      )

    result = rdf_memory.YaraProcessDumpResponse()
    errors = []

    for p in ProcessIterator(
        args.pids,
        args.process_regex,
        None,
        args.ignore_grr_process,
        args.ignore_parent_processes,
        errors,
    ):
      self.Progress()
      start = rdfvalue.RDFDatetime.Now()

      try:
        response = self.DumpProcess(p, args)
        now = rdfvalue.RDFDatetime.Now()
        response.dump_time_us = (now - start).ToInt(rdfvalue.MICROSECONDS)
        result.dumped_processes.Append(response)
        if response.error:
          # Limit exceeded, we bail out early.
          break
      except Exception as e:  # pylint: disable=broad-except
        errors.append(
            rdf_memory.ProcessMemoryError(
                process=rdf_client.Process.FromPsutilProcess(p),
                error=str(e),
            )
        )
        continue

    result.errors = errors
    self.SendReply(result)
