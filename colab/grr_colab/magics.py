#!/usr/bin/env python
"""GRR Colab magics module.

The module contains implementation of **magic** commands that use GRR API.
"""
import shlex
from typing import Text

from IPython.core import magic_arguments
import pandas as pd

from grr_colab import magics_impl


_PATH_TYPE_CHOICES = [
    magics_impl.OS, magics_impl.TSK, magics_impl.NTFS, magics_impl.REGISTRY
]


def grr_set_no_flow_timeout(line: Text) -> None:
  """Disables flow timeout (it means wait forever).

  Args:
    line: A string representing arguments passed to the magic command.

  Returns:
    Nothing.
  """
  del line  # Unused.
  magics_impl.grr_set_no_flow_timeout_impl()


def grr_set_default_flow_timeout(line: Text) -> None:
  """Sets flow timeout to default value (30 seconds).

  Args:
    line: A string representing arguments passed to the magic command.

  Returns:
    Nothing.
  """
  del line  # Unused.
  magics_impl.grr_set_default_flow_timeout_impl()


@magic_arguments.magic_arguments()
@magic_arguments.argument(
    'timeout', help='Timeout in seconds', type=int, nargs='?', default=None)
def grr_set_flow_timeout(line: Text) -> None:
  """Sets flow timeout.

  Specifying 0 as timeout means not to wait.

  Args:
    line: A string representing arguments passed to the magic command.

  Returns:
    Nothing.
  """
  args = grr_set_flow_timeout.parser.parse_args(shlex.split(line))
  magics_impl.grr_set_flow_timeout_impl(args.timeout)


def grr_list_artifacts(line: Text) -> pd.DataFrame:
  """Lists all registered GRR artifacts.

  Args:
    line: A string representing arguments passed to the magic command.

  Returns:
    Sequence of artifact descriptors.
  """
  del line  # Unused.
  return magics_impl.grr_list_artifacts_impl()


@magic_arguments.magic_arguments()
@magic_arguments.argument('-i', '--ip', help='IP address', type=str)
@magic_arguments.argument('-m', '--mac', help='MAC address', type=str)
@magic_arguments.argument('-h', '--host', help='Hostname', type=str)
@magic_arguments.argument('-u', '--user', help='Username', type=str)
@magic_arguments.argument('-v', '--version', help='Client version', type=str)
@magic_arguments.argument(
    '-l', '--label', help='Client label', type=str, action='append')
def grr_search_clients(line: Text) -> pd.DataFrame:
  """Searches for clients with specified keywords.

  Args:
    line: A string representing arguments passed to the magic command.

  Returns:
    List of clients.
  """
  args = grr_search_clients.parser.parse_args(shlex.split(line))
  return magics_impl.grr_search_clients_impl(
      ip=args.ip,
      mac=args.mac,
      host=args.host,
      user=args.user,
      version=args.version,
      labels=args.label)


@magic_arguments.magic_arguments()
@magic_arguments.argument('-i', '--ip', help='IP address', type=str)
@magic_arguments.argument('-m', '--mac', help='MAC address', type=str)
@magic_arguments.argument('-h', '--host', help='Hostname', type=str)
@magic_arguments.argument('-u', '--user', help='Username', type=str)
@magic_arguments.argument('-v', '--version', help='Client version', type=str)
@magic_arguments.argument(
    '-l', '--label', help='Client label', type=str, action='append')
def grr_search_online_clients(line: Text) -> pd.DataFrame:
  """Searches for online clients with specified keywords.

  Args:
    line: A string representing arguments passed to the magic command.

  Returns:
    List of online clients.
  """
  args = grr_search_online_clients.parser.parse_args(shlex.split(line))
  return magics_impl.grr_search_online_clients_impl(
      ip=args.ip,
      mac=args.mac,
      host=args.host,
      user=args.user,
      version=args.version,
      labels=args.label)


@magic_arguments.magic_arguments()
@magic_arguments.argument('-h', '--hostname', help='Hostname', type=str)
@magic_arguments.argument('-c', '--client', help='Client ID', type=str)
def grr_set_client(line: Text) -> None:
  """Sets a new client for the current state.

  Args:
    line: A string representing arguments passed to the magic command.

  Returns:
    Nothing.
  """
  args = grr_set_client.parser.parse_args(shlex.split(line))
  magics_impl.grr_set_client_impl(args.hostname, args.client)


@magic_arguments.magic_arguments()
@magic_arguments.argument(
    '-r', '--reason', help='Reason for the approval', type=str)
@magic_arguments.argument(
    '-a',
    '--approvers',
    help='Notified users who can approve the request',
    type=str,
    nargs='+')
@magic_arguments.argument(
    '-w', '--wait', action='store_true', help='Wait until approval is granted')
def grr_request_approval(line: Text) -> None:
  """Sends approval request to the selected client for the current user.

  Args:
    line: A string representing arguments passed to the magic command.

  Returns:
    Nothing.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  args = grr_request_approval.parser.parse_args(shlex.split(line))
  magics_impl.grr_request_approval_impl(args.reason, args.approvers, args.wait)


def grr_id(line: Text) -> Text:
  """Returns ID of the selected client.

  Args:
    line: A string representing arguments passed to the magic command.

  Returns:
    String representing ID of a client.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  del line  # Unused.
  return magics_impl.grr_id_impl()


@magic_arguments.magic_arguments()
@magic_arguments.argument('path', help='Directory path', type=str)
def grr_cd(line: Text) -> None:
  """Changes the current directory.

  Args:
    line: A string representing arguments passed to the magic command.

  Returns:
    Nothing.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  args = grr_cd.parser.parse_args(shlex.split(line))
  magics_impl.grr_cd_impl(args.path)


def grr_pwd(line: Text) -> Text:
  """Returns absolute path to the current directory.

  Args:
    line: A string representing arguments passed to the magic command.

  Returns:
    Absolute path to the current directory.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  del line  # Unused.
  return magics_impl.grr_pwd_impl()


@magic_arguments.magic_arguments()
@magic_arguments.argument('path', help='Directory path', type=str, nargs='?')
@magic_arguments.argument(
    '-C',
    '--cached',
    action='store_true',
    help='Use cached filesystem instead of making call to a client')
@magic_arguments.argument(
    '-P',
    '--path-type',
    help='Path type',
    type=str,
    choices=_PATH_TYPE_CHOICES,
    default=magics_impl.OS)
def grr_ls(line: Text) -> pd.DataFrame:
  """Lists files in the specified directory or the current directory.

  Args:
    line: A string representing arguments passed to the magic command.

  Returns:
    A sequence of stat entries.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  args = grr_ls.parser.parse_args(shlex.split(line))
  return magics_impl.grr_ls_impl(
      path=args.path, cached=args.cached, path_type=args.path_type)


@magic_arguments.magic_arguments()
@magic_arguments.argument('path', help='File path', type=str)
@magic_arguments.argument(
    '-P',
    '--path-type',
    help='Path type',
    type=str,
    choices=_PATH_TYPE_CHOICES,
    default=magics_impl.OS)
def grr_stat(line: Text) -> pd.DataFrame:
  """Stats the file specified.

  Accepts glob expressions as a file path.

  Args:
    line: A string representing arguments passed to the magic command.

  Returns:
    A sequence of stat entries.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  args = grr_stat.parser.parse_args(shlex.split(line))
  return magics_impl.grr_stat_impl(path=args.path, path_type=args.path_type)


@magic_arguments.magic_arguments()
@magic_arguments.argument('path', help='File path', type=str)
@magic_arguments.argument(
    '-c', '--bytes', default=4096, help='Number of bytes to read', type=int)
@magic_arguments.argument(
    '-o', '--offset', default=0, help='Number of bytes to skip', type=int)
@magic_arguments.argument(
    '-C',
    '--cached',
    action='store_true',
    help='Use cached filesystem instead of making call to a client')
@magic_arguments.argument(
    '-P',
    '--path-type',
    help='Path type',
    type=str,
    choices=_PATH_TYPE_CHOICES,
    default=magics_impl.OS)
def grr_head(line: Text) -> bytes:
  """Reads the first bytes of a specified file.

  Args:
    line: A string representing arguments passed to the magic command.

  Returns:
    Specified number of the first bytes of the file.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  args = grr_head.parser.parse_args(shlex.split(line))
  return magics_impl.grr_head_impl(
      path=args.path,
      bytes=args.bytes,
      offset=args.offset,
      cached=args.cached,
      path_type=args.path_type)


@magic_arguments.magic_arguments()
@magic_arguments.argument('pattern', help='Pattern to search for', type=str)
@magic_arguments.argument('path', help='File path', type=str)
@magic_arguments.argument(
    '-F',
    '--fixed-strings',
    action='store_true',
    help='Interpret pattern as a fixed string (literal)')
@magic_arguments.argument(
    '-P',
    '--path-type',
    help='Path type',
    type=str,
    choices=_PATH_TYPE_CHOICES,
    default=magics_impl.OS)
@magic_arguments.argument(
    '-X',
    '--hex-string',
    action='store_true',
    help='Interpret pattern as a hex-encoded byte string')
def grr_grep(line: Text) -> pd.DataFrame:
  """Greps for a given content of a specified file.

  Args:
    line: A string representing arguments passed to the magic command.

  Returns:
    A list of buffer references to the matched content.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  args = grr_grep.parser.parse_args(shlex.split(line))
  return magics_impl.grr_grep_impl(
      pattern=args.pattern,
      path=args.path,
      fixed_strings=args.fixed_strings,
      path_type=args.path_type,
      hex_string=args.hex_string)


@magic_arguments.magic_arguments()
@magic_arguments.argument('literal', help='Literal to search for', type=str)
@magic_arguments.argument('path', help='File path', type=str)
@magic_arguments.argument(
    '-P',
    '--path-type',
    help='Path type',
    type=str,
    choices=_PATH_TYPE_CHOICES,
    default=magics_impl.OS)
@magic_arguments.argument(
    '-X',
    '--hex-string',
    action='store_true',
    help='Interpret pattern as a hex-encoded byte string')
def grr_fgrep(line: Text) -> pd.DataFrame:
  """Greps for a given literal content of a specified file.

  Is the same as running: %grr_grep -F

  Args:
    line: A string representing arguments passed to the magic command.

  Returns:
    A list of buffer references to the matched content.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  args = grr_fgrep.parser.parse_args(shlex.split(line))
  return magics_impl.grr_fgrep_impl(
      literal=args.literal,
      path=args.path,
      path_type=args.path_type,
      hex_string=args.hex_string)


def grr_interrogate(line: Text) -> pd.DataFrame:
  """Creates Interrogate flow for the chosen client.

  Args:
    line: A string representing arguments passed to the magic command.

  Returns:
    Client summary including system and client info, interfaces, and users.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  del line  # Unused.
  return magics_impl.grr_interrogate_impl()


def grr_hostname(line: Text) -> Text:
  """Returns hostname of the selected client.

  Args:
    line: A string representing arguments passed to the magic command.

  Returns:
    String representing hostname of a client.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  del line  # Unused.
  return magics_impl.grr_hostname_impl()


def grr_ifconfig(line: Text) -> pd.DataFrame:
  """Lists network interfaces of the selected client.

  Args:
    line: A string representing arguments passed to the magic command.

  Returns:
    Sequence of interfaces.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  del line  # Unused.
  return magics_impl.grr_ifconfig_impl()


@magic_arguments.magic_arguments()
@magic_arguments.argument(
    '-m', '--machine', action='store_true', help='Get machine hardware name')
@magic_arguments.argument(
    '-r',
    '--kernel-release',
    action='store_true',
    help='Get kernel release string')
def grr_uname(line: Text) -> Text:
  """Returns certain system infornamtion.

  Args:
    line: A string representing arguments passed to the magic command.

  Returns:
    String representing some system information.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  args = grr_uname.parser.parse_args(shlex.split(line))
  return magics_impl.grr_uname_impl(args.machine, args.kernel_release)


def grr_ps(line: Text) -> pd.DataFrame:
  """Lists processes of the selected client.

  Args:
    line: A string representing arguments passed to the magic command.

  Returns:
    Sequence of processes.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  del line  # Unused.
  return magics_impl.grr_ps_impl()


@magic_arguments.magic_arguments()
@magic_arguments.argument('sql', help='SQL statement', type=str)
def grr_osqueryi(line: Text) -> pd.DataFrame:
  """Runs given SQL statement on client osquery.

  Args:
    line: A string representing arguments passed to the magic command.

  Returns:
    Osquery table.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  args = grr_osqueryi.parser.parse_args(shlex.split(line))
  return magics_impl.grr_osqueryi_impl(args.sql)


@magic_arguments.magic_arguments()
@magic_arguments.argument('artifact', help='Name of the artifact', type=str)
def grr_collect(line: Text) -> pd.DataFrame:
  """Collects specified artifact.

  Args:
    line: A string representing arguments passed to the magic command.

  Returns:
    Sequence of results that artifact collection yielded.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  args = grr_collect.parser.parse_args(shlex.split(line))
  return magics_impl.grr_collect_impl(args.artifact)


@magic_arguments.magic_arguments()
@magic_arguments.argument('signature', help='YARA rule to use', type=str)
@magic_arguments.argument('-r', '--regex', help='Process name regex', type=str)
@magic_arguments.argument(
    '-p', '--pids', help='Pids of processes to scan', type=int, nargs='+')
def grr_yara(line: Text) -> pd.DataFrame:
  """Scans processes using provided YARA rule.

  Args:
    line: A string representing arguments passed to the magic command.

  Returns:
    A sequence of YARA matches.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  args = grr_yara.parser.parse_args(shlex.split(line))
  return magics_impl.grr_yara_impl(args.signature, args.pids, args.regex)


@magic_arguments.magic_arguments()
@magic_arguments.argument('path', help='File path', type=str)
@magic_arguments.argument(
    '-C',
    '--cached',
    action='store_true',
    help='Use cached filesystem instead of making call to a client')
@magic_arguments.argument(
    '-P',
    '--path-type',
    help='Path type',
    type=str,
    choices=_PATH_TYPE_CHOICES,
    default=magics_impl.OS)
def grr_wget(line: Text) -> Text:
  """Downloads a file and returns a link to it.

  Args:
    line: A string representing arguments passed to the magic command.

  Returns:
    A link to the file.

  Raises:
    NoClientSelectedError: Client is not selected to perform this operation.
  """
  args = grr_wget.parser.parse_args(shlex.split(line))
  return magics_impl.grr_wget_impl(
      path=args.path, cached=args.cached, path_type=args.path_type)
