#!/usr/bin/env python
"""GRR Colab magics implementation as usual functions."""
import binascii
import ipaddress
import os
from typing import Optional

import numpy as np
import pandas as pd

import grr_colab
from grr_colab import convert
from grr_colab import fs
from grr_colab._textify import client as client_textify

OS = 'os'
TSK = 'tsk'
NTFS = 'ntfs'
REGISTRY = 'registry'


class _State(object):

  def __init__(self) -> None:
    self.client: Optional[grr_colab.Client] = None
    self.cur_dir = '/'


class NoClientSelectedError(Exception):

  def __init__(self) -> None:
    msg = 'A client must be selected'
    super().__init__(msg)


_state = _State()


def grr_set_no_flow_timeout_impl() -> None:
  """Disables flow timeout (it means wait forever).

  Returns:
    Nothing.
  """
  grr_colab.set_no_flow_timeout()


def grr_set_default_flow_timeout_impl() -> None:
  """Sets flow timeout to default value (30 seconds).

  Returns:
    Nothing.
  """
  grr_colab.set_default_flow_timeout()


def grr_set_flow_timeout_impl(timeout: int) -> None:
  """Sets flow timeout.

  Args:
    timeout: Timeout in seconds. 0 means not to wait.

  Returns:
    Nothing.
  """
  grr_colab.set_flow_timeout(timeout)


def grr_list_artifacts_impl() -> pd.DataFrame:
  """Lists all registered GRR artifacts.

  Returns:
    A list of artifact descriptors.
  """
  df = convert.from_sequence(grr_colab.list_artifacts())

  priority_columns = [
      'artifact.name',
      'artifact.doc',
      'artifact.supported_os',
      'artifact.labels',
  ]
  df = convert.reindex_dataframe(df, priority_columns=priority_columns)

  return df


def grr_search_clients_impl(
    ip: Optional[str] = None,
    mac: Optional[str] = None,
    host: Optional[str] = None,
    user: Optional[str] = None,
    version: Optional[str] = None,
    labels: Optional[list[str]] = None,
) -> pd.DataFrame:
  """Searches for clients with specified keywords.

  Args:
    ip: IP address.
    mac: MAC address.
    host: Hostname.
    user: Username.
    version: Client version.
    labels: List of client labels.

  Returns:
    List of clients.
  """
  clients = grr_colab.Client.search(
      ip=ip, mac=mac, host=host, user=user, version=version, labels=labels)
  clients_data = [_._client.data for _ in clients]  # pylint: disable=protected-access

  df = convert.from_sequence(clients_data)

  _add_last_seen_column(df)
  _add_online_status_columns(df)

  priority_columns = [
      'online.pretty', 'online', 'client_id', 'last_seen_ago',
      'last_seen_at.pretty', 'knowledge_base.fqdn', 'os_info.version'
  ]
  df = convert.reindex_dataframe(df, priority_columns=priority_columns)

  if 'last_seen_at' in df.columns:
    return df.sort_values(
        by='last_seen_at', ascending=False).reset_index(drop=True)
  return df


def grr_search_online_clients_impl(
    ip: Optional[str] = None,
    mac: Optional[str] = None,
    host: Optional[str] = None,
    user: Optional[str] = None,
    version: Optional[str] = None,
    labels: Optional[list[str]] = None,
) -> pd.DataFrame:
  """Searches for online clients with specified keywords.

  Args:
    ip: IP address.
    mac: MAC address.
    host: Hostname.
    user: Username.
    version: Client version.
    labels: List of client labels..

  Returns:
    List of online clients.
  """
  df = grr_search_clients_impl(ip, mac, host, user, version, labels)
  return df[df.online == 'online'].reset_index(drop=True)


def grr_set_client_impl(
    hostname: Optional[str] = None, client: Optional[str] = None
) -> None:
  """Sets a new client for the current state.

  Args:
    hostname: Client hostname.
    client: Client ID.

  Returns:
    Nothing.
  """
  if hostname is None and client is None:
    raise ValueError('Hostname and client ID cannot be None at the same time.')
  if hostname is not None and client is not None:
    raise ValueError('Hostname and client ID cannot be both specified.')
  if hostname is not None:
    _state.client = grr_colab.Client.with_hostname(hostname)
  if client is not None:
    _state.client = grr_colab.Client.with_id(client)
  _state.cur_dir = '/'


def grr_request_approval_impl(
    reason: str, approvers: list[str], wait: bool = False
) -> None:
  """Sends approval request to the selected client for the current user.

  Args:
    reason: Reason for the approval.
    approvers: List of notified users who can approve the request.
    wait: If true, wait until approval is granted.

  Returns:
    Nothing.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  if _state.client is None:
    raise NoClientSelectedError()

  if wait:
    _state.client.request_approval_and_wait(approvers=approvers, reason=reason)
  else:
    _state.client.request_approval(approvers=approvers, reason=reason)


def grr_id_impl() -> str:
  """Returns ID of the selected client.

  Returns:
    String representing ID of a client.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  if _state.client is None:
    raise NoClientSelectedError()
  return _state.client.id


def grr_cd_impl(path: str) -> None:
  """Changes the current directory.

  Args:
    path: Directory path to cd in.

  Returns:
    Nothing.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  if _state.client is None:
    raise NoClientSelectedError()
  _state.cur_dir = _build_absolute_path(path)


def grr_pwd_impl() -> str:
  """Returns absolute path to the current directory.

  Returns:
    Absolute path to the current directory.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  if _state.client is None:
    raise NoClientSelectedError()
  return _state.cur_dir


def grr_ls_impl(
    path: Optional[str] = None, cached: bool = False, path_type: str = OS
) -> pd.DataFrame:
  """Lists files in the specified directory or the current directory.

  Args:
    path: Directory path to ls.
    cached: If true, use cached filesystem instead of making call to a client.
    path_type: Path type to use (one of os, tsk, ntfs, registry).

  Returns:
    A sequence of stat entries.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  if _state.client is None:
    raise NoClientSelectedError()

  path = _build_absolute_path(path) if path else _state.cur_dir
  filesystem = _get_filesystem(path_type)

  if cached:
    return convert.from_sequence(filesystem.cached.ls(path))
  return convert.from_sequence(filesystem.ls(path))


def grr_stat_impl(path: str, path_type: str = OS) -> pd.DataFrame:
  """Stats the file specified.

  Accepts glob expressions as a file path.

  Args:
    path: File path to stat.
    path_type: Path type to use (one of os, tsk, ntfs, registry).

  Returns:
    A sequence of stat entries.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  if _state.client is None:
    raise NoClientSelectedError()

  path = _build_absolute_path(path)
  filesystem = _get_filesystem(path_type)

  return convert.from_sequence(filesystem.glob(path))


def grr_head_impl(
    path: str,
    bytes: int = 4096,  # pylint: disable=redefined-builtin
    offset: int = 0,
    cached: bool = False,
    path_type: str = OS,
) -> bytes:
  """Reads the first bytes of a specified file.

  Args:
    path: File path to head.
    bytes: Number of bytes to read.
    offset: Number of bytes to skip from the beginning of the file.
    cached: If true, use cached filesystem instead of making call to a client.
    path_type: Path type to use (one of os, tsk, ntfs, registry).

  Returns:
    Specified number of the first bytes of the file.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  if _state.client is None:
    raise NoClientSelectedError()

  path = _build_absolute_path(path)
  filesystem = _get_filesystem(path_type)

  if cached:
    with filesystem.cached.open(path) as f:
      f.seek(offset)
      return f.read(bytes)
  with filesystem.open(path) as f:
    f.seek(offset)
    return f.read(bytes)


def grr_grep_impl(
    pattern: str,
    path: str,
    fixed_strings: bool = False,
    path_type: str = OS,
    hex_string: bool = False,
) -> pd.DataFrame:
  """Greps for a given content of a specified file.

  Args:
    pattern: Pattern to search for.
    path: File path to grep.
    fixed_strings: If true, interpret pattern as a fixed string (literal).
    path_type: Path type to use (one of os, tsk, ntfs, registry).
    hex_string: If true, interpret pattern as a hex-encoded byte string.

  Returns:
    A list of buffer references to the matched content.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  if _state.client is None:
    raise NoClientSelectedError()

  if hex_string:
    byte_pattern = binascii.unhexlify(pattern)
  else:
    byte_pattern = pattern.encode('utf-8')

  path = _build_absolute_path(path)
  filesystem = _get_filesystem(path_type)

  if fixed_strings:
    return convert.from_sequence(filesystem.fgrep(path, byte_pattern))
  return convert.from_sequence(filesystem.grep(path, byte_pattern))


def grr_fgrep_impl(
    literal: str, path: str, path_type: str = OS, hex_string: bool = False
) -> pd.DataFrame:
  """Greps for a given literal content of a specified file.

  Is the same as running: %grr_grep -F

  Args:
    literal: Literal to search for.
    path: File path to grep.
    path_type: Path type to use (one of os, tsk, ntfs, registry).
    hex_string: If true, interpret pattern as a hex-encoded byte string.

  Returns:
    A list of buffer references to the matched content.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  if _state.client is None:
    raise NoClientSelectedError()

  if hex_string:
    byte_literal = binascii.unhexlify(literal)
  else:
    byte_literal = literal.encode('utf-8')

  path = _build_absolute_path(path)
  filesystem = _get_filesystem(path_type)

  return convert.from_sequence(filesystem.fgrep(path, byte_literal))


def grr_interrogate_impl() -> pd.DataFrame:
  """Creates Interrogate flow for the chosen client.

  Returns:
    Client summary including system and client info, interfaces, and users.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  if _state.client is None:
    raise NoClientSelectedError()
  return convert.from_message(_state.client.interrogate())


def grr_hostname_impl() -> str:
  """Returns hostname of the selected client.

  Returns:
    String representing hostname of a client.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  if _state.client is None:
    raise NoClientSelectedError()
  return _state.client.hostname


def grr_ifconfig_impl() -> pd.DataFrame:
  """Lists network interfaces of the selected client.

  Returns:
    Sequence of interfaces.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  if _state.client is None:
    raise NoClientSelectedError()
  df = convert.from_sequence(_state.client.ifaces)

  if 'addresses' in df.columns:
    for i in range(len(df['addresses'])):
      if isinstance(df['addresses'][i], pd.DataFrame):
        df['addresses'][i] = _add_pretty_ipaddress_column(
            df['addresses'][i], 'packed_bytes')

  df = _add_pretty_mac_column(df, 'mac_address')

  return df


def grr_uname_impl(machine: bool = False, kernel_release: bool = False) -> str:
  """Returns certain system infornamtion.

  Args:
    machine: If true, get machine hardware name.
    kernel_release: If true, get kernel release string.

  Returns:
    String representing some system information.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  if _state.client is None:
    raise NoClientSelectedError()

  if machine:
    return _state.client.arch
  if kernel_release:
    return _state.client.kernel
  raise ValueError('No options were specified')


def grr_ps_impl() -> pd.DataFrame:
  """Lists processes of the selected client.

  Returns:
    Sequence of processes.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  if _state.client is None:
    raise NoClientSelectedError()
  return convert.from_sequence(_state.client.ps())


def grr_osqueryi_impl(sql: str) -> pd.DataFrame:
  """Runs given SQL statement on client osquery.

  Args:
    sql: SQL statement to execute.

  Returns:
    Osquery table.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  if _state.client is None:
    raise NoClientSelectedError()
  return convert.from_osquery_table(_state.client.osquery(sql))


def grr_collect_impl(artifact: str) -> pd.DataFrame:
  """Collects specified artifact.

  Args:
    artifact: A name of the artifact to collect.

  Returns:
    A list of results that artifact collection yielded.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  if _state.client is None:
    raise NoClientSelectedError()
  return convert.from_sequence(_state.client.collect(artifact))


def grr_yara_impl(
    signature: str,
    pids: Optional[list[int]] = None,
    regex: Optional[str] = None,
) -> pd.DataFrame:
  """Scans processes using provided YARA rule.

  Args:
    signature: YARA rule to run.
    pids: List of pids of processes to scan.
    regex: A regex to match against the process name.

  Returns:
    A sequence of YARA matches.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  if _state.client is None:
    raise NoClientSelectedError()
  return convert.from_sequence(_state.client.yara(signature, pids, regex))


def grr_wget_impl(path: str, cached: bool = False, path_type: str = OS) -> str:
  """Downloads a file and returns a link to it.

  Args:
    path: A path to the file to download.
    cached: If true, use cached filesystem instead of making call to a client.
    path_type: Path type to use (one of os, tsk, ntfs, registry).

  Returns:
    A link to the file.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  if _state.client is None:
    raise NoClientSelectedError()

  path = _build_absolute_path(path)
  filesystem = _get_filesystem(path_type)

  if cached:
    return filesystem.cached.wget(path)
  return filesystem.wget(path)


def _build_absolute_path(path: str) -> str:
  if path.startswith('/'):
    abs_path = path
  else:
    abs_path = os.path.join(_state.cur_dir, path)
  return os.path.normpath(abs_path)


def _get_filesystem(path_type: str) -> fs.FileSystem:
  """Returns filesystem depending on provided path type.

  Args:
    path_type: String representing path type.

  Returns:
    FileSystem of the specified path type.

  Raises:
    NoClientSelectedError: If client is not selected to perform this operation.
  """
  if _state.client is None:
    raise NoClientSelectedError
  if path_type == OS:
    return _state.client.os
  elif path_type == TSK:
    return _state.client.tsk
  elif path_type == NTFS:
    return _state.client.ntfs
  elif path_type == REGISTRY:
    return _state.client.registry
  raise ValueError('Unsupported path type `{}`'.format(path_type))


def _add_online_status_columns(df: pd.DataFrame) -> pd.DataFrame:
  """Adds string and unicode online status columns to a dataframe of clients.

  Args:
    df: Dataframe of clients.

  Returns:
    Dataframe with columns added.
  """
  if 'last_seen_at' not in df.columns:
    return df

  statuses = [client_textify.online_status(tm) for tm in df['last_seen_at']]
  icons = [client_textify.online_icon(tm) for tm in df['last_seen_at']]
  df.insert(0, 'online', pd.Series(statuses))
  df.insert(0, 'online.pretty', pd.Series(icons))
  return df


def _add_last_seen_column(df: pd.DataFrame) -> pd.DataFrame:
  """Adds last seen time ago column to a dataframe of clients.

  Args:
    df: Dataframe of clients.

  Returns:
    Dataframe with a column added.
  """
  if 'last_seen_at' not in df.columns:
    return df

  seen_ago = [client_textify.last_seen(tm) for tm in df['last_seen_at']]
  df.insert(0, 'last_seen_ago', pd.Series(seen_ago))
  return df


def _add_pretty_ipaddress_column(
    df: pd.DataFrame, col_name: str
) -> pd.DataFrame:
  """Adds a column with pretty representation of IP address value.

  Args:
    df: Dataframe to add a column to.
    col_name: Name of IP address column.

  Returns:
    Dataframe with a column added.
  """

  if col_name not in df.columns:
    return df

  def convert_to_pretty_str(packed: bytes) -> str:
    if len(packed) == 4:
      return str(ipaddress.IPv4Address(packed))
    return str(ipaddress.IPv6Address(packed))

  pretty_values = [convert_to_pretty_str(packed) for packed in df[col_name]]
  return convert.add_pretty_column(df, col_name, pretty_values)


def _add_pretty_mac_column(df: pd.DataFrame, col_name: str) -> pd.DataFrame:
  """Adds a column with pretty representation of MAC address value.

  Args:
    df: Dataframe to add a column to.
    col_name: Name of MAC address column.

  Returns:
    Dataframe with a column added.
  """

  if col_name not in df.columns:
    return df

  def convert_to_pretty_str(packed: bytes) -> str:
    if pd.isna(packed):
      return np.nan
    return client_textify.mac(packed)

  pretty_values = [convert_to_pretty_str(packed) for packed in df[col_name]]
  return convert.add_pretty_column(df, col_name, pretty_values)
