#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""GRR Colab magics implementation as usual functions."""

from __future__ import absolute_import
from __future__ import division

from __future__ import print_function
from __future__ import unicode_literals

import os
import time

from future.builtins import bytes as new_bytes
import ipaddress
import numpy as np
import pandas as pd
from typing import Text, Optional, List

import grr_colab
from grr_colab import convert


class _State(object):

  def __init__(self):
    self.client = None  # type: Optional[grr_colab.Client]
    self.cur_dir = '/'


class NoClientSelectedError(Exception):

  def __init__(self):
    msg = 'A client must be selected'
    super(NoClientSelectedError, self).__init__(msg)


_state = _State()


def grr_set_no_flow_timeout_impl():
  """Disables flow timeout (it means wait forever).

  Returns:
    Nothing.
  """
  grr_colab.set_no_flow_timeout()


def grr_set_default_flow_timeout_impl():
  """Sets flow timeout to default value (30 seconds).

  Returns:
    Nothing.
  """
  grr_colab.set_default_flow_timeout()


def grr_set_flow_timeout_impl(timeout):
  """Sets flow timeout.

  Args:
    timeout: Timeout in seconds. 0 means not to wait.

  Returns:
    Nothing.
  """
  grr_colab.set_flow_timeout(timeout)


def grr_list_artifacts_impl():
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
    ip = None,
    mac = None,
    host = None,
    user = None,
    version = None,
    labels = None):
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
    ip = None,
    mac = None,
    host = None,
    user = None,
    version = None,
    labels = None):
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


def grr_set_client_impl(hostname = None,
                        client = None):
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


def grr_request_approval_impl(reason,
                              approvers,
                              wait = False):
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


def grr_id_impl():
  """Returns ID of the selected client.

  Returns:
    String representing ID of a client.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  if _state.client is None:
    raise NoClientSelectedError()
  return _state.client.id


def grr_cd_impl(path):
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


def grr_pwd_impl():
  """Returns absolute path to the current directory.

  Returns:
    Absolute path to the current directory.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  if _state.client is None:
    raise NoClientSelectedError()
  return _state.cur_dir


def grr_ls_impl(path = None,
                cached = False):
  """Lists files in the specified directory or the current directory.

  Args:
    path: Directory path to ls.
    cached: If true, use cached filesystem instead of making call to a client.

  Returns:
    A sequence of stat entries.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  if _state.client is None:
    raise NoClientSelectedError()
  path = _build_absolute_path(path) if path else _state.cur_dir
  if cached:
    return convert.from_sequence(_state.client.cached.ls(path))
  return convert.from_sequence(_state.client.ls(path))


def grr_stat_impl(path):
  """Stats the file specified.

  Accepts glob expressions as a file path.

  Args:
    path: File path to stat.

  Returns:
    A sequence of stat entries.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  if _state.client is None:
    raise NoClientSelectedError()
  path = _build_absolute_path(path)
  return convert.from_sequence(_state.client.glob(path))


def grr_head_impl(
    path,
    bytes = 4096,  # pylint: disable=redefined-builtin
    offset = 0,
    cached = False):
  """Reads the first bytes of a specified file.

  Args:
    path: File path to head.
    bytes: Number of bytes to read.
    offset: Number of bytes to skip from the beginning of the file.
    cached: If true, use cached filesystem instead of making call to a client.

  Returns:
    Specified number of the first bytes of the file.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  if _state.client is None:
    raise NoClientSelectedError()

  path = _build_absolute_path(path)
  if cached:
    with _state.client.cached.open(path) as f:
      f.seek(offset)
      return f.read(bytes)
  with _state.client.open(path) as f:
    f.seek(offset)
    return f.read(bytes)


def grr_grep_impl(pattern,
                  path,
                  fixed_strings = False):
  """Greps for a given content of a specified file.

  Args:
    pattern: Pattern to search for.
    path: File path to grep.
    fixed_strings: If true, interpret pattern as a fixed string (literal).

  Returns:
    A list of buffer references to the matched content.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  if _state.client is None:
    raise NoClientSelectedError()

  path = _build_absolute_path(path)
  if fixed_strings:
    return convert.from_sequence(_state.client.fgrep(path, pattern))
  return convert.from_sequence(_state.client.grep(path, pattern))


def grr_fgrep_impl(literal, path):
  """Greps for a given literal content of a specified file.

  Is the same as running: %grr_grep -F

  Args:
    literal: Literal to search for.
    path: File path to grep.

  Returns:
    A list of buffer references to the matched content.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  if _state.client is None:
    raise NoClientSelectedError()

  path = _build_absolute_path(path)
  return convert.from_sequence(_state.client.fgrep(path, literal))


def grr_interrogate_impl():
  """Creates Interrogate flow for the chosen client.

  Returns:
    Client summary including system and client info, interfaces, and users.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  if _state.client is None:
    raise NoClientSelectedError()
  return convert.from_message(_state.client.interrogate())


def grr_hostname_impl():
  """Returns hostname of the selected client.

  Returns:
    String representing hostname of a client.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  if _state.client is None:
    raise NoClientSelectedError()
  return _state.client.hostname


def grr_ifconfig_impl():
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


def grr_uname_impl(machine = False, kernel_release = False):
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


def grr_ps_impl():
  """Lists processes of the selected client.

  Returns:
    Sequence of processes.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  if _state.client is None:
    raise NoClientSelectedError()
  return convert.from_sequence(_state.client.ps())


def grr_osqueryi_impl(sql):
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


def grr_collect_impl(artifact):
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


def grr_yara_impl(signature,
                  pids = None,
                  regex = None):
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


def grr_wget_impl(path, cached = False):
  """Downloads a file and returns a link to it.

  Args:
    path: A path to the file to download.
    cached: If true, use cached filesystem instead of making call to a client.

  Returns:
    A link to the file.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  if _state.client is None:
    raise NoClientSelectedError()

  path = _build_absolute_path(path)

  if cached:
    return _state.client.cached.wget(path)
  return _state.client.wget(path)


def _build_absolute_path(path):
  if path.startswith('/'):
    abs_path = path
  else:
    abs_path = os.path.join(_state.cur_dir, path)
  return os.path.normpath(abs_path)


def _add_online_status_columns(df):
  """Adds string and unicode online status columns to a dataframe of clients.

  Args:
    df: Dataframe of clients.

  Returns:
    Dataframe with columns added.
  """
  if 'last_seen_at' not in df.columns:
    return df

  current_time_secs = time.time()
  unicode_statuses = {
      'online': '🌕',
      'seen-1d': '🌓',
      'offline': '🌑',
  }

  def online_status(last_ping):
    last_seen_secs = current_time_secs - last_ping / 10**6
    if last_seen_secs < 60 * 15:
      return 'online'
    elif last_seen_secs < 60 * 60 * 24:
      return 'seen-1d'
    else:
      return 'offline'

  char_values = [online_status(last_seen) for last_seen in df['last_seen_at']]
  unicode_values = [
      unicode_statuses[online_status(last_seen)]
      for last_seen in df['last_seen_at']
  ]
  df.insert(0, 'online', pd.Series(char_values))
  df.insert(0, 'online.pretty', pd.Series(unicode_values))
  return df


def _add_last_seen_column(df):
  """Adds last seen time ago column to a dataframe of clients.

  Args:
    df: Dataframe of clients.

  Returns:
    Dataframe with a column added.
  """
  if 'last_seen_at' not in df.columns:
    return df

  current_time_secs = time.time()

  def last_seen_label(last_ping):
    """Constructs last seen label from last ping time.

    Args:
      last_ping: Last ping time in microseconds.

    Returns:
      Constructed last seen label.
    """
    last_ping_secs = last_ping / 10**6
    last_seen_secs = abs(current_time_secs - last_ping_secs)

    if last_seen_secs < 60:
      measure_unit = 'seconds'
      measure_value = int(last_seen_secs)
    elif last_seen_secs < 60 * 60:
      measure_unit = 'minutes'
      measure_value = int(last_seen_secs / 60)
    elif last_seen_secs < 60 * 60 * 24:
      measure_unit = 'hours'
      measure_value = int(last_seen_secs / (60 * 60))
    else:
      measure_unit = 'days'
      measure_value = int(last_seen_secs / (60 * 60 * 24))

    if current_time_secs >= last_ping_secs:
      return '{} {} ago'.format(measure_value, measure_unit)
    else:
      return 'in {} {}'.format(measure_value, measure_unit)

  seen_ago = [last_seen_label(last_seen) for last_seen in df['last_seen_at']]
  df.insert(0, 'last_seen_ago', pd.Series(seen_ago))
  return df


def _add_pretty_ipaddress_column(df,
                                 col_name):
  """Adds a column with pretty representation of IP address value.

  Args:
    df: Dataframe to add a column to.
    col_name: Name of IP address column.

  Returns:
    Dataframe with a column added.
  """

  if col_name not in df.columns:
    return df

  def convert_to_pretty_str(packed):
    if len(packed) == 4:
      return str(ipaddress.IPv4Address(packed))
    return str(ipaddress.IPv6Address(packed))

  pretty_values = [convert_to_pretty_str(packed) for packed in df[col_name]]
  return convert.add_pretty_column(df, col_name, pretty_values)


def _add_pretty_mac_column(df, col_name):
  """Adds a column with pretty representation of MAC address value.

  Args:
    df: Dataframe to add a column to.
    col_name: Name of MAC address column.

  Returns:
    Dataframe with a column added.
  """

  if col_name not in df.columns:
    return df

  def convert_to_pretty_str(packed):
    if pd.isna(packed):
      return np.nan
    # TODO: In Python3 new_bytes call is noop but in Python2 it
    #  will convert old bytes to future compatible interface. Remove as soon as
    #  support for Python2 is dropped.
    return ':'.join('{:02x}'.format(b) for b in new_bytes(packed))

  pretty_values = [convert_to_pretty_str(packed) for packed in df[col_name]]
  return convert.add_pretty_column(df, col_name, pretty_values)
