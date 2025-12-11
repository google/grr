#!/usr/bin/env python
"""AFF4 RDFValue implementations for client information.

This module contains the RDFValue implementations used to communicate with the
client.
"""

from collections.abc import Mapping
import logging
import platform
import re
import socket
import sys

import distro
import psutil

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import type_info
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import jobs_pb2
from grr_response_proto import knowledge_base_pb2
from grr_response_proto import sysinfo_pb2

# ntop does not exist on Windows.
# pylint: disable=g-socket-inet-aton,g-socket-inet-ntoa

# We try to support PEP 425 style component names if possible. This makes it
# possible to have wheel as an optional dependency.
try:
  # pytype: disable=import-error
  from wheel import pep425tags  # pylint: disable=g-import-not-at-top
  # pytype: enable=import-error
except ImportError:
  pep425tags = None

FS_ENCODING = sys.getfilesystemencoding() or sys.getdefaultencoding()

_LOCALHOST = "localhost"
_LOCALHOST_LOCALDOMAIN = "localhost.localdomain"
_ARPA_SUFFIXES = ("ip6.arpa", "in-addr.arpa")


class ClientURN(rdfvalue.RDFURN):
  """A client urn has to have a specific form."""

  # Valid client urns must match this expression.
  CLIENT_ID_RE = re.compile(r"^(aff4:)?/?(?P<clientid>(c|C)\.[0-9a-fA-F]{16})$")

  def __init__(self, initializer=None):
    super().__init__(initializer)

    if self._value and not self.Validate(self._value):
      raise type_info.TypeValueError("Client urn malformed: %s" % initializer)

  @classmethod
  def _Normalize(cls, string):
    normalized = super()._Normalize(string.strip())

    if normalized:
      match = cls.CLIENT_ID_RE.match(normalized)
      if not match:
        raise type_info.TypeValueError(
            "Client URN '{!r} from initializer {!r} malformed".format(
                normalized, string
            )
        )

      clientid = match.group("clientid")
      clientid_correctcase = "".join(
          (clientid[0].upper(), clientid[1:].lower())
      )

      normalized = normalized.replace(clientid, clientid_correctcase, 1)
    return normalized

  @classmethod
  def Validate(cls, value):
    if value:
      return bool(cls.CLIENT_ID_RE.match(str(value)))

    return False

  def Add(self, path):
    """Add a relative stem to the current value and return a new RDFURN.

    Note that this returns an RDFURN, not a ClientURN since the resulting object
    would not pass validation.

    Args:
      path: A string containing a relative path.

    Returns:
       A new RDFURN that can be chained.

    Raises:
       ValueError: if the path component is not a string.
    """
    if not isinstance(path, str):
      raise ValueError("Only strings should be added to a URN.")

    return rdfvalue.RDFURN(utils.JoinPath(self._value, path))


class PackageRepository(rdf_structs.RDFProtoStruct):
  """Description of the configured repositories (Yum etc).

  Describes the configured software package repositories.
  """

  protobuf = sysinfo_pb2.PackageRepository


class ManagementAgent(rdf_structs.RDFProtoStruct):
  """Description of the running management agent (puppet etc).

  Describes the state, last run timestamp, and name of the management agent
  installed on the system.
  """

  protobuf = sysinfo_pb2.ManagementAgent
  rdf_deps = [
      rdfvalue.RDFDatetime,
  ]


class PwEntry(rdf_structs.RDFProtoStruct):
  """Information about password structures."""

  protobuf = knowledge_base_pb2.PwEntry


class Group(rdf_structs.RDFProtoStruct):
  """Information about system posix groups."""

  protobuf = knowledge_base_pb2.Group
  rdf_deps = [
      PwEntry,
  ]


class User(rdf_structs.RDFProtoStruct):
  """Information about the users."""

  protobuf = knowledge_base_pb2.User
  rdf_deps = [
      PwEntry,
      rdfvalue.RDFDatetime,
  ]

  def __init__(self, initializer=None, **kwargs):
    if isinstance(initializer, KnowledgeBaseUser):
      # KnowledgeBaseUser was renamed to User, the protos are identical. This
      # allows for backwards compatibility with clients returning KBUser
      # objects.
      # TODO(user): remove once all clients are newer than 3.0.7.1.
      initializer = User.FromSerializedBytes(initializer.SerializeToBytes())
    super().__init__(initializer=initializer, **kwargs)


class KnowledgeBaseUser(User):
  """Backwards compatibility for old clients.

  Linux client action EnumerateUsers previously returned KnowledgeBaseUser
  objects.
  """


class KnowledgeBase(rdf_structs.RDFProtoStruct):
  """Information about the system and users."""

  protobuf = knowledge_base_pb2.KnowledgeBase
  rdf_deps = [
      User,
  ]

  def MergeOrAddUser(self, kb_user: User) -> None:
    """Merge a user into existing users or add new if it doesn't exist.

    Args:
      kb_user: A User rdfvalue.
    """

    user = self.GetUser(
        sid=kb_user.sid, uid=kb_user.uid, username=kb_user.username
    )
    if not user:
      self.users.Append(kb_user)
    else:
      for key, val in kb_user.AsDict().items():
        user.Set(key, val)

  def GetUser(self, sid=None, uid=None, username=None):
    """Retrieve a User based on sid, uid or username.

    On windows we first get a SID and use it to find the username.  We want to
    avoid combining users with name collisions, which occur when local users
    have the same username as domain users (something like Admin is particularly
    common).  So if a SID is provided, don't also try to match by username.

    On linux we first get a username, then use this to find the UID, so we want
    to combine these records or we end up with multiple partially-filled user
    records.

    TODO(user): this won't work at all well with a query for uid=0 because
    that is also the default for User objects that don't have uid
    set.

    Args:
      sid: Windows user sid
      uid: Linux/Darwin user id
      username: string

    Returns:
      rdf_client.User or None
    """
    if sid:
      for user in self.users:
        if user.sid == sid:
          return user
      return None
    if uid:
      for user in self.users:
        if user.uid == uid:
          return user
    if username:
      for user in self.users:
        if user.username == username:
          # Make sure we aren't combining different uids if we know them
          # user.uid = 0 is the default, which makes this more complicated.
          if uid and user.uid and user.uid != uid:
            return None
          else:
            return user

  def GetKbFieldNames(self):
    fields = set(self.type_infos.descriptor_names)

    # DEPRECATED_users field is maintained for backwards compatibility reasons
    # only, as type of the "users" field has changed from jobs.User to
    # knowledge_base.User.
    fields.remove("DEPRECATED_users")

    # We used to have a "hostname" field that contained an fqdn and is
    # therefore now renamed to "fqdn".
    # TODO(amoser): Remove once the artifact has removed the provides
    # section upstream.
    fields.add("hostname")

    fields.remove("users")
    for field in self.users.type_descriptor.type.type_infos.descriptor_names:
      fields.add("users.%s" % field)
    return sorted(fields)


class HardwareInfo(rdf_structs.RDFProtoStruct):
  """Various hardware information."""

  protobuf = sysinfo_pb2.HardwareInfo


class ClientInformation(rdf_structs.RDFProtoStruct):
  """The GRR client information."""

  protobuf = jobs_pb2.ClientInformation


class BufferReference(rdf_structs.RDFProtoStruct):
  """Stores information about a buffer in a file on the client."""

  protobuf = jobs_pb2.BufferReference
  rdf_deps = [
      rdf_paths.PathSpec,
  ]

  def __eq__(self, other):
    return self.data == other


class Process(rdf_structs.RDFProtoStruct):
  """Represent a process on the client."""

  protobuf = sysinfo_pb2.Process
  rdf_deps = [
      rdf_client_network.NetworkConnection,
  ]

  @classmethod
  def FromPsutilProcess(cls, psutil_process):
    response = cls()
    process_fields = ["pid", "ppid", "name", "exe", "username", "terminal"]

    with psutil_process.oneshot():
      for field in process_fields:
        try:
          value = getattr(psutil_process, field)
          if value is None:
            continue

          if callable(value):
            value = value()

          if not isinstance(value, int):
            value = utils.SmartUnicode(value)

          setattr(response, field, value)
        except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
          pass

      try:
        response.cmdline = list(psutil_process.cmdline())
      except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
      except Exception as e:  # pylint: disable=broad-except
        # Windows now has Virtual Secure Mode (VSM) processes that have
        # additional memory protection. For those, cmdline() and cwd() will
        # raise a Windows Error 998 (ERROR_NOACCESS, Invalid access to memory
        # location).
        if not hasattr(e, "winerror") or e.winerror != 998:  # pytype: disable=attribute-error
          raise

      try:
        response.nice = psutil_process.nice()
      except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

      try:
        # Not available on Windows.
        if hasattr(psutil_process, "uids"):
          (response.real_uid, response.effective_uid, response.saved_uid) = (
              psutil_process.uids()
          )
          (response.real_gid, response.effective_gid, response.saved_gid) = (
              psutil_process.gids()
          )
      except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

      try:
        response.ctime = int(psutil_process.create_time() * 1e6)
        response.status = str(psutil_process.status())
      except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

      try:
        # Not available on OSX.
        if hasattr(psutil_process, "cwd"):
          response.cwd = utils.SmartUnicode(psutil_process.cwd())
      except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
      # We have seen psutil on macos raise OSError here with errno 2 - ENOENT -
      # but we haven't managed to reproduce this behavior. This might be fixed
      # in more recent versions of psutil but we play it safe and just catch the
      # error.
      except OSError:
        pass
      except Exception as e:  # pylint: disable=broad-except
        # Windows now has Virtual Secure Mode (VSM) processes that have
        # additional memory protection. For those, cmdline() and cwd() will
        # raise a Windows Error 998 (ERROR_NOACCESS, Invalid access to memory
        # location).
        if not hasattr(e, "winerror") or e.winerror != 998:  # pytype: disable=attribute-error
          raise

      try:
        response.num_threads = psutil_process.num_threads()
      except (psutil.NoSuchProcess, psutil.AccessDenied, RuntimeError):
        pass

      try:
        cpu_times = psutil_process.cpu_times()
        response.user_cpu_time = cpu_times.user
        response.system_cpu_time = cpu_times.system
        # psutil_process.get_cpu_percent() is very time consuming so we do not
        # collect it.
      except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

      try:
        pmem = psutil_process.memory_info()
        response.RSS_size = pmem.rss  # pylint: disable=invalid-name
        response.VMS_size = pmem.vms  # pylint: disable=invalid-name
        response.memory_percent = psutil_process.memory_percent()
      except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

      # Due to a bug in psutil, this function is disabled for now
      # (https://github.com/giampaolo/psutil/issues/340)
      # try:
      #  for f in psutil_process.open_files():
      #    response.open_files.append(utils.SmartUnicode(f.path))
      # except (psutil.NoSuchProcess, psutil.AccessDenied):
      #  pass

      try:
        for c in psutil_process.connections():
          conn = response.connections.Append(
              family=c.family, type=c.type, pid=psutil_process.pid
          )

          try:
            conn.state = c.status
          except ValueError:
            logging.info(
                "Encountered unknown connection status (%s).", c.status
            )

          try:
            conn.local_address.ip, conn.local_address.port = c.laddr

            # Could be in state LISTEN.
            if c.raddr:
              conn.remote_address.ip, conn.remote_address.port = c.raddr
          except AttributeError:
            conn.local_address.ip, conn.local_address.port = c.local_address

            # Could be in state LISTEN.
            if c.remote_address:
              (conn.remote_address.ip, conn.remote_address.port) = (
                  c.remote_address
              )

      except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

      return response


class NamedPipe(rdf_structs.RDFProtoStruct):
  """An RDF wrapper for the named pipe message."""

  protobuf = sysinfo_pb2.NamedPipe
  rdf_deps = []


class SoftwarePackage(rdf_structs.RDFProtoStruct):
  """Represent an installed package on the client."""

  protobuf = sysinfo_pb2.SoftwarePackage

  @classmethod
  def Installed(cls, **kwargs):
    return SoftwarePackage(
        install_state=SoftwarePackage.InstallState.INSTALLED, **kwargs
    )

  @classmethod
  def Pending(cls, **kwargs):
    return SoftwarePackage(
        install_state=SoftwarePackage.InstallState.PENDING, **kwargs
    )

  @classmethod
  def Uninstalled(cls, **kwargs):
    return SoftwarePackage(
        install_state=SoftwarePackage.InstallState.UNINSTALLED, **kwargs
    )


class SoftwarePackages(rdf_structs.RDFProtoStruct):
  """A list of installed packages on the system."""

  protobuf = sysinfo_pb2.SoftwarePackages

  rdf_deps = [
      SoftwarePackage,
  ]


class LogMessage(rdf_structs.RDFProtoStruct):
  """A log message sent from the client to the server."""

  protobuf = jobs_pb2.LogMessage


class Uname(rdf_structs.RDFProtoStruct):
  """A protobuf to represent the current system."""

  protobuf = jobs_pb2.Uname
  rdf_deps = [
      rdfvalue.RDFDatetime,
  ]

  @property
  def arch(self):
    """Return a more standard representation of the architecture."""
    if self.machine in ["x86_64", "AMD64", "i686"]:
      # 32 bit binaries running on AMD64 will still have a i386 arch.
      if self.architecture == "32bit":
        return "i386"

      return "amd64"
    elif self.machine == "x86":
      return "i386"

    return self.machine

  def signature(self):
    """Returns a unique string that encapsulates the architecture."""
    # If the protobuf contains a proper pep425 tag return that.
    result = self.pep425tag
    if result:
      return result

    raise ValueError(
        "PEP 425 Signature not set - this is likely an old "
        "component file, please back it up and remove it."
    )

  @classmethod
  def FromCurrentSystem(cls):
    """Fill a Uname from the currently running platform."""
    uname = platform.uname()
    fqdn = socket.getfqdn()
    if (
        fqdn == _LOCALHOST
        or fqdn == _LOCALHOST_LOCALDOMAIN
        or any(fqdn.endswith(suffix) for suffix in _ARPA_SUFFIXES)
    ):
      # Avoid returning 'localhost' when there is a better value to use.
      fqdn = socket.gethostname()
    system = uname[0]
    architecture, _ = platform.architecture()
    if system == "Windows":
      service_pack = platform.win32_ver()[2]
      kernel = uname[3]  # 5.1.2600
      release = uname[2]  # XP, 2000, 7
      version = uname[3] + service_pack  # 5.1.2600 SP3, 6.1.7601 SP1
    elif system == "Darwin":
      kernel = uname[2]  # 12.2.0
      release = "OSX"  # OSX
      version = platform.mac_ver()[0]  # 10.8.2
    elif system == "Linux":
      kernel = uname[2]  # 3.2.5
      release = distro.name()
      version = distro.version()

    # Emulate PEP 425 naming conventions - e.g. cp27-cp27mu-linux_x86_64.
    if pep425tags:
      try:
        # 0.33.6
        pep_platform = pep425tags.get_platform()
      except TypeError:
        # 0.34.2
        pep_platform = pep425tags.get_platform(None)
      pep425tag = "%s%s-%s-%s" % (
          pep425tags.get_abbr_impl(),
          pep425tags.get_impl_ver(),
          str(pep425tags.get_abi_tag()).lower(),
          pep_platform,
      )
    else:
      # For example: windows_7_amd64
      pep425tag = "%s_%s_%s" % (system, release, architecture)

    return cls(
        system=system,
        architecture=architecture,
        release=release,
        version=version,
        machine=uname[4],  # x86, x86_64
        kernel=kernel,
        fqdn=fqdn,
        pep425tag=pep425tag,
    )


class StartupInfo(rdf_structs.RDFProtoStruct):
  """Information about the startup of a GRR agent."""

  protobuf = jobs_pb2.StartupInfo
  rdf_deps = [
      ClientInformation,
      rdfvalue.RDFDatetime,
  ]


class OSXServiceInformation(rdf_structs.RDFProtoStruct):
  """OSX Service (launchagent/daemon)."""

  protobuf = sysinfo_pb2.OSXServiceInformation
  rdf_deps = [
      rdfvalue.RDFURN,
  ]


# Start of the Registry Specific Data types
class RunKey(rdf_structs.RDFProtoStruct):
  protobuf = sysinfo_pb2.RunKey


class ClientCrash(rdf_structs.RDFProtoStruct):
  """Details of a client crash."""

  protobuf = jobs_pb2.ClientCrash
  rdf_deps = [
      ClientInformation,
      ClientURN,
      rdfvalue.RDFDatetime,
      rdfvalue.SessionID,
  ]


class EdrAgent(rdf_structs.RDFProtoStruct):
  """An RDF wrapper for protobuf message containing EDR agent metadata."""

  protobuf = jobs_pb2.EdrAgent
  rdf_deps = []


class FleetspeakValidationInfoTag(rdf_structs.RDFProtoStruct):
  """Dictionary entry in FleetspeakValidationInfo."""

  protobuf = jobs_pb2.FleetspeakValidationInfoTag


class FleetspeakValidationInfo(rdf_structs.RDFProtoStruct):
  """Dictionary-like struct containing Fleetspeak ValidationInfo."""

  protobuf = jobs_pb2.FleetspeakValidationInfo
  rdf_deps = [FleetspeakValidationInfoTag]

  @classmethod
  def FromStringDict(cls, dct: Mapping[str, str]) -> "FleetspeakValidationInfo":
    instance = cls()
    for key, value in dct.items():
      instance.tags.Append(key=key, value=value)
    return instance

  def ToStringDict(self) -> Mapping[str, str]:
    return {tag.key: tag.value for tag in self.tags}


class ClientSummary(rdf_structs.RDFProtoStruct):
  """Object containing client's summary data."""

  protobuf = jobs_pb2.ClientSummary
  rdf_deps = [
      ClientInformation,
      ClientURN,
      EdrAgent,
      rdf_client_network.Interface,
      rdfvalue.RDFDatetime,
      Uname,
      User,
      FleetspeakValidationInfo,
  ]


class VersionString(rdfvalue.RDFString):

  @property
  def versions(self):
    result = []
    for x in str(self).split("."):
      try:
        result.append(int(x))
      except ValueError:
        break

    return result
