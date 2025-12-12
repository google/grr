#!/usr/bin/env python
"""GRR Colab module.

The module contains classes that Colab users will use to interact with GRR API.
"""
from collections.abc import Sequence
import datetime
import io
from typing import Optional, Union

from IPython.lib import pretty

from google.protobuf import message
from grr_api_client import client
from grr_api_client import errors as api_errors
from grr_api_client import utils as api_utils
from grr_colab import _api
from grr_colab import _timeout
from grr_colab import errors
from grr_colab import fs
from grr_colab import representer
from grr_colab import vfs
from grr_colab._textify import client as client_textify
from grr_response_proto import artifact_pb2
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import knowledge_base_pb2
from grr_response_proto import objects_pb2
from grr_response_proto import osquery_pb2
from grr_response_proto import sysinfo_pb2


def set_no_flow_timeout() -> None:
  """Disables flow timeout (it means wait forever).

  Returns:
    Nothing.
  """
  _timeout.set_timeout(None)


def set_default_flow_timeout() -> None:
  """Sets flow timeout to default value (30 seconds).

  Returns:
    Nothing.
  """
  _timeout.reset_timeout()


def set_flow_timeout(timeout: int) -> None:
  """Sets flow timeout.

  Args:
    timeout: timeout in seconds. 0 means not to wait.

  Returns:
    Nothing.
  """
  if timeout is None:
    raise ValueError('Timeout is not specified')
  if timeout < 0:
    raise ValueError('Timeout cannot be negative')
  _timeout.set_timeout(timeout)


def list_artifacts() -> Sequence[artifact_pb2.ArtifactDescriptor]:
  """Lists all registered artifacts.

  Returns:
    A list of artifact descriptors.
  """
  return [artifact.data for artifact in _api.get().ListArtifacts()]


class Client(object):
  """Wrapper for a GRR Client.

  Offers easy to use methods to interact with GRR API
  from Colab.

  Attributes:
    id: Id of the client.
    hostname: Hostname of the client.
    ifaces: A list of network interfaces of the given client.
    knowledgebase: Knowledgebase for the client.
    arch: Architectire that the client is running on.
    kernel: Kernel version string of the client.
    labels: A list of labels associated with the client.
    first_seen: Returns the time the client was seen for the first time.
    last_seen: Returns the time the client was seen for the last time.
    cached: A VFS instance that allows to work with filesystem data saved on the
      server that may not be up-to-date but is a way faster.
    os: OS filesystem instance that encapsulates filesystem related operations.
    tsk: TSK filesystem instance that encapsulates filesystem related
      operations.
    ntfs: NTFS filesystem instance that encapsulates filesystem related
      operations.
    registry: REGISTRY filesystem instance that encapsulates filesystem related
      operations.
  """

  def __init__(self, client_: client.Client) -> None:
    self._client = client_
    self._snapshot: objects_pb2.ClientSnapshot = None

  @classmethod
  def with_id(cls, client_id: str) -> 'Client':
    try:
      return cls(_api.get().Client(client_id).Get())
    except api_errors.UnknownError as e:
      raise errors.UnknownClientError(client_id, e)

  @classmethod
  def with_hostname(cls, hostname: str) -> 'Client':
    clients = cls.search(host=hostname)
    if not clients:
      raise errors.UnknownHostnameError(hostname)
    if len(clients) > 1:
      raise errors.AmbiguousHostnameError(hostname, [_.id for _ in clients])
    return clients[0]

  @classmethod
  def search(
      cls,
      ip: Optional[str] = None,
      mac: Optional[str] = None,
      host: Optional[str] = None,
      version: Optional[int] = None,
      labels: Optional[list[str]] = None,
      user: Optional[str] = None,
  ) -> Sequence['Client']:
    """Searches for clients specified with keywords.

    Args:
      ip: Client IP address.
      mac: Client MAC address.
      host: Client hostname.
      version: Client version.
      labels: Client labels.
      user: Client username.

    Returns:
      A sequence of clients.
    """

    def format_keyword(key: str, value: str) -> str:
      return '{}:{}'.format(key, value)

    keywords = []
    if ip is not None:
      keywords.append(format_keyword('ip', ip))
    if mac is not None:
      keywords.append(format_keyword('mac', mac))
    if host is not None:
      keywords.append(format_keyword('host', host))
    if version is not None:
      keywords.append(format_keyword('client', str(version)))
    if labels:
      for label in labels:
        keywords.append(format_keyword('label', label))
    if user is not None:
      keywords.append(format_keyword('user', user))

    query = ' '.join(keywords)
    clients = _api.get().SearchClients(query)
    return representer.ClientList([cls(_) for _ in clients])

  @property
  def id(self) -> str:
    return self._client.client_id

  @property
  def hostname(self) -> str:
    if self._snapshot is not None:
      return self._snapshot.knowledge_base.fqdn
    return self.knowledgebase.fqdn

  @property
  def ifaces(self) -> Sequence[jobs_pb2.Interface]:
    if self._snapshot is not None:
      return representer.InterfaceList(self._snapshot.interfaces)
    return representer.InterfaceList(self._client.data.interfaces)

  @property
  def knowledgebase(self) -> knowledge_base_pb2.KnowledgeBase:
    return self._client.data.knowledge_base

  @property
  def arch(self) -> str:
    if self._snapshot is not None:
      return self._snapshot.arch
    return self._client.data.os_info.machine

  @property
  def kernel(self) -> str:
    if self._snapshot is not None:
      return self._snapshot.kernel
    return self._client.data.os_info.kernel

  @property
  def labels(self) -> Sequence[str]:
    return [_.name for _ in self._client.data.labels]

  @property
  def first_seen(self) -> datetime.datetime:
    return _microseconds_to_datetime(self._client.data.first_seen_at)

  @property
  def last_seen(self) -> datetime.datetime:
    return _microseconds_to_datetime(self._client.data.last_seen_at)

  @property
  def os(self) -> fs.FileSystem:
    return fs.FileSystem(self._client, jobs_pb2.PathSpec.OS)

  @property
  def tsk(self) -> fs.FileSystem:
    return fs.FileSystem(self._client, jobs_pb2.PathSpec.TSK)

  @property
  def ntfs(self) -> fs.FileSystem:
    return fs.FileSystem(self._client, jobs_pb2.PathSpec.NTFS)

  @property
  def registry(self) -> fs.FileSystem:
    return fs.FileSystem(self._client, jobs_pb2.PathSpec.REGISTRY)

  @property
  def cached(self) -> vfs.VFS:
    return self.os.cached

  def request_approval(self, approvers: list[str], reason: str) -> None:
    """Sends approval request to the client for the current user.

    Args:
      approvers: List of users who will be notified of this request.
      reason: Reason for this approval.

    Returns:
      Nothing.
    """
    if not reason:
      raise ValueError('Approval reason is not provided')
    if not approvers:
      raise ValueError('List of approvers is empty')

    self._client.CreateApproval(reason=reason, notified_users=approvers)

  def request_approval_and_wait(
      self, approvers: list[str], reason: str
  ) -> None:
    """Sends approval request and waits until it's granted.

    Args:
      approvers: List of users who will be notified of this request.
      reason: Reason for this approval.

    Returns:
      Nothing.
    """
    if not reason:
      raise ValueError('Approval reason is not provided')
    if not approvers:
      raise ValueError('List of approvers is empty')

    approval = self._client.CreateApproval(
        reason=reason, notified_users=approvers)
    approval.WaitUntilValid()

  def interrogate(self) -> objects_pb2.ClientSnapshot:
    """Grabs fresh metadata about the client.

    Returns:
      A client snapshot.
    """
    try:
      interrogate = self._client.CreateFlow(name='Interrogate')
    except api_errors.AccessForbiddenError as e:
      raise errors.ApprovalMissingError(self.id, e)

    _timeout.await_flow(interrogate)

    result = list(interrogate.ListResults())[0].payload
    if not isinstance(result, objects_pb2.ClientSnapshot):
      raise TypeError(f'Unexpected flow result type: {type(result)!r}')

    self._snapshot = result
    return self._snapshot

  def ps(self) -> Sequence[sysinfo_pb2.Process]:
    """Returns a list of processes running on the client."""
    args = flows_pb2.ListProcessesArgs()

    try:
      ps = self._client.CreateFlow(name='ListProcesses', args=args)
    except api_errors.AccessForbiddenError as e:
      raise errors.ApprovalMissingError(self.id, e)

    _timeout.await_flow(ps)

    def process(result: message.Message) -> sysinfo_pb2.Process:
      if not isinstance(result, sysinfo_pb2.Process):
        raise TypeError(f'Unexpected flow result type: {type(result)!r}')

      return result

    results = [process(response.payload) for response in ps.ListResults()]
    return representer.ProcessList(results)

  def ls(self, path: str, max_depth: int = 1) -> Sequence[jobs_pb2.StatEntry]:
    """Lists contents of a given directory.

    Args:
      path: A path to the directory to list the contents of.
      max_depth: Max depth of subdirectories to explore. If max_depth is >1,
        then the results will also include the contents of subdirectories (and
        sub-subdirectories and so on).

    Returns:
      A sequence of stat entries.
    """
    return self.os.ls(path, max_depth)

  def glob(self, path: str) -> Sequence[jobs_pb2.StatEntry]:
    """Globs for files on the given client.

    Args:
      path: A glob expression (that may include `*` and `**`).

    Returns:
      A sequence of stat entries to the found files.
    """
    return self.os.glob(path)

  def grep(
      self, path: str, pattern: bytes
  ) -> Sequence[jobs_pb2.BufferReference]:
    """Greps for given content on the specified path.

    Args:
      path: A path to a file to be searched.
      pattern: A regular expression on search for.

    Returns:
      A list of buffer references to the matched content.
    """
    return self.os.grep(path, pattern)

  def fgrep(
      self, path: str, literal: bytes
  ) -> Sequence[jobs_pb2.BufferReference]:
    """Greps for given content on the specified path.

    Args:
      path: A path to a file to be searched.
      literal: A literal expression on search for.

    Returns:
      A list of buffer references to the matched content.
    """
    return self.os.fgrep(path, literal)

  def osquery(
      self, query: str, timeout: int = 30000, ignore_stderr_errors: bool = False
  ) -> osquery_pb2.OsqueryTable:
    """Runs given query on the client.

    Args:
      query: An SQL query to run against osquery on the client.
      timeout: Query timeout in millis.
      ignore_stderr_errors: If true, will not break in case of stderr errors.

    Returns:
      An osquery table corresponding to the result of running the query.
    """

    args = osquery_pb2.OsqueryFlowArgs()
    args.query = query
    args.timeout_millis = timeout
    args.ignore_stderr_errors = ignore_stderr_errors

    try:
      oq = self._client.CreateFlow(name='OsqueryFlow', args=args)
    except api_errors.AccessForbiddenError as e:
      raise errors.ApprovalMissingError(self.id, e)

    _timeout.await_flow(oq)

    result_table = osquery_pb2.OsqueryTable()
    # We use the query from the function parameter in case we don't get any
    # result back (which may happen if the query yields no rows).
    result_table.query = query

    for flow_result in oq.ListResults():
      result_part = osquery_pb2.OsqueryResult()
      if not flow_result.data.payload.Unpack(result_part):
        raise TypeError(
            f'Unexpected flow result type: {flow_result.data.payload.type_url}'
        )

      # Ideally, we would like to do `result.table.MergeFrom(result_part.table)`
      # but unfortunately this would recursively merge header as well which will
      # duplicate columns. Hence, we explicitly copy the `header` field but for
      # rows we use concatenation.
      result_table.header.CopyFrom(result_part.table.header)
      result_table.rows.extend(result_part.table.rows)

    return result_table

  def collect(
      self,
      artifact: str,
  ) -> Sequence[Union[message.Message, api_utils.UnknownProtobuf]]:
    """Collects specified artifact.

    Args:
      artifact: A name of the artifact to collect.

    Returns:
      A list of results that artifact collection yielded.
    """

    args = flows_pb2.ArtifactCollectorFlowArgs()
    args.artifact_list.append(artifact)

    try:
      ac = self._client.CreateFlow(name='ArtifactCollectorFlow', args=args)
    except api_errors.AccessForbiddenError as e:
      raise errors.ApprovalMissingError(self.id, e)

    _timeout.await_flow(ac)
    return [_.payload for _ in ac.ListResults()]

  def yara(
      self,
      signature: str,
      pids: Optional[Sequence[int]] = None,
      regex: Optional[str] = None,
  ) -> Sequence[flows_pb2.YaraProcessScanMatch]:
    """Scans processes using provided YARA rule.

    Args:
      signature: YARA rule to run.
      pids: List of pids of processes to scan.
      regex: A regex to match against the process name.

    Returns:
      A list of YARA matches.
    """
    if pids is None:
      pids = []

    args = flows_pb2.YaraProcessScanRequest()
    args.yara_signature = signature
    args.ignore_grr_process = False

    if regex is not None:
      args.process_regex = regex

    args.pids.extend(pids)

    try:
      yara = self._client.CreateFlow(name='YaraProcessScan', args=args)
    except api_errors.AccessForbiddenError as e:
      raise errors.ApprovalMissingError(self.id, e)

    _timeout.await_flow(yara)

    def yara_result(result: message.Message) -> flows_pb2.YaraProcessScanMatch:
      if not isinstance(result, flows_pb2.YaraProcessScanMatch):
        raise TypeError(f'Unexpected flow result type: {type(result)!r}')

      return result

    return [yara_result(result.payload) for result in yara.ListResults()]

  def wget(self, path: str) -> str:
    """Downloads a file and returns a link to it.

    Args:
      path: A path to download.

    Returns:
      A link to the file.
    """
    return self.os.wget(path)

  def open(self, path: str) -> io.BufferedIOBase:
    """Opens a file object corresponding to the given path on the client.

    The returned file object is read-only.

    Args:
      path: A path to the file to open.

    Returns:
      A file-like object (implementing standard IO interface).
    """
    return self.os.open(path)

  def _repr_pretty_(self, p: pretty.PrettyPrinter, cycle: bool) -> None:
    del cycle  # Unused.
    icon = client_textify.online_icon(self._client.data.last_seen_at)
    last_seen = client_textify.last_seen(self._client.data.last_seen_at)
    data = '{icon} {id} @ {host} ({last_seen})'.format(
        icon=icon, id=self.id, last_seen=last_seen, host=self.hostname)
    p.text(data)


def _microseconds_to_datetime(ms: int) -> datetime.datetime:
  return datetime.datetime.utcfromtimestamp(ms / (10**6))
