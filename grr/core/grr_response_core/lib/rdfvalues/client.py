#!/usr/bin/env python
"""AFF4 RDFValue implementations for client information.

This module contains the RDFValue implementations used to communicate with the
client.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import hashlib
import logging
import platform
import re
import socket
import struct


from future.utils import iteritems
from future.utils import string_types
from past.builtins import long
import psutil

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import type_info
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import precondition
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


class ClientURN(rdfvalue.RDFURN):
  """A client urn has to have a specific form."""

  # Valid client urns must match this expression.
  CLIENT_ID_RE = re.compile(r"^(aff4:)?/?(?P<clientid>(c|C)\.[0-9a-fA-F]{16})$")

  def __init__(self, initializer=None, age=None):
    if isinstance(initializer, rdfvalue.RDFURN):
      if not self.Validate(initializer.Path()):
        raise type_info.TypeValueError("Client urn malformed: %s" % initializer)
    super(ClientURN, self).__init__(initializer=initializer, age=age)

  def ParseFromUnicode(self, value):
    """Parse a string into a client URN.

    Convert case so that all URNs are of the form C.[0-9a-f].

    Args:
      value: string value to parse
    """
    precondition.AssertType(value, unicode)
    value = value.strip()

    super(ClientURN, self).ParseFromUnicode(value)

    match = self.CLIENT_ID_RE.match(self._string_urn)
    if not match:
      raise type_info.TypeValueError("Client urn malformed: %s" % value)

    clientid = match.group("clientid")
    clientid_correctcase = "".join((clientid[0].upper(), clientid[1:].lower()))

    self._string_urn = self._string_urn.replace(clientid, clientid_correctcase,
                                                1)

  @classmethod
  def Validate(cls, value):
    if value:
      return bool(cls.CLIENT_ID_RE.match(unicode(value)))

    return False

  @classmethod
  def FromPrivateKey(cls, private_key):
    return cls.FromPublicKey(private_key.GetPublicKey())

  @classmethod
  def FromPublicKey(cls, public_key):
    """An alternate constructor which generates a new client id."""
    # Our CN will be the first 64 bits of the hash of the public key
    # in MPI format - the length of the key in 4 bytes + the key
    # prefixed with a 0. This weird format is an artifact from the way
    # M2Crypto handled this, we have to live with it for now.
    n = public_key.GetN()
    raw_n = ("%x" % n).decode("hex")

    mpi_format = struct.pack(">i", len(raw_n) + 1) + b"\x00" + raw_n

    return cls("C.%s" % (hashlib.sha256(mpi_format).digest()[:8].encode("hex")))

  def Add(self, path, age=None):
    """Add a relative stem to the current value and return a new RDFURN.

    Note that this returns an RDFURN, not a ClientURN since the resulting object
    would not pass validation.

    Args:
      path: A string containing a relative path.
      age: The age of the object. If None set to current time.

    Returns:
       A new RDFURN that can be chained.

    Raises:
       ValueError: if the path component is not a string.
    """
    if not isinstance(path, string_types):
      raise ValueError("Only strings should be added to a URN.")

    result = rdfvalue.RDFURN(self.Copy(age))
    result.Update(path=utils.JoinPath(self._string_urn, path))

    return result

  def Queue(self):
    """Returns the queue name of this clients task queue."""
    return self.Add("tasks")


def GetClientURNFromPath(path):
  """Extracts the Client id from the path, if it is present."""

  # Make sure that the first component of the path looks like a client.
  try:
    return ClientURN(path.split("/")[1])
  except (type_info.TypeValueError, IndexError):
    return None


class PCIDevice(rdf_structs.RDFProtoStruct):
  """A PCI device on the client.

  This class describes a PCI device located on the client.
  """
  protobuf = sysinfo_pb2.PCIDevice


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

  def __init__(self, initializer=None, age=None, **kwargs):
    if isinstance(initializer, KnowledgeBaseUser):
      # KnowledgeBaseUser was renamed to User, the protos are identical. This
      # allows for backwards compatibility with clients returning KBUser
      # objects.
      # TODO(user): remove once all clients are newer than 3.0.7.1.
      super(User, self).__init__(initializer=None, age=age, **kwargs)
      self.ParseFromString(initializer.SerializeToString())
    else:
      super(User, self).__init__(initializer=initializer, age=age, **kwargs)


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

  def _CreateNewUser(self, kb_user):
    self.users.Append(kb_user)
    return ["users.%s" % k for k in kb_user.AsDict()]

  def MergeOrAddUser(self, kb_user):
    """Merge a user into existing users or add new if it doesn't exist.

    Args:
      kb_user: A User rdfvalue.

    Returns:
      A list of strings with the set attribute names, e.g. ["users.sid"]
    """

    user = self.GetUser(
        sid=kb_user.sid, uid=kb_user.uid, username=kb_user.username)
    new_attrs = []
    merge_conflicts = []  # Record when we overwrite a value.
    if not user:
      new_attrs = self._CreateNewUser(kb_user)
    else:
      for key, val in iteritems(kb_user.AsDict()):
        if user.Get(key) and user.Get(key) != val:
          merge_conflicts.append((key, user.Get(key), val))
        user.Set(key, val)
        new_attrs.append("users.%s" % key)

    return new_attrs, merge_conflicts

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

    for field in process_fields:
      try:
        value = getattr(psutil_process, field)
        if value is None:
          continue

        if callable(value):
          value = value()

        if not isinstance(value, (int, long)):
          value = utils.SmartUnicode(value)

        setattr(response, field, value)
      except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
        pass

    try:
      for arg in psutil_process.cmdline():
        response.cmdline.append(utils.SmartUnicode(arg))
    except (psutil.NoSuchProcess, psutil.AccessDenied):
      pass

    try:
      response.nice = psutil_process.nice()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
      pass

    try:
      # Not available on Windows.
      if hasattr(psutil_process, "uids"):
        (response.real_uid, response.effective_uid,
         response.saved_uid) = psutil_process.uids()
        (response.real_gid, response.effective_gid,
         response.saved_gid) = psutil_process.gids()
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

    try:
      response.num_threads = psutil_process.num_threads()
    except (psutil.NoSuchProcess, psutil.AccessDenied, RuntimeError):
      pass

    try:
      cpu_times = psutil_process.cpu_times()
      response.user_cpu_time = cpu_times.user
      response.system_cpu_time = cpu_times.system
      # This is very time consuming so we do not collect cpu_percent here.
      # response.cpu_percent = psutil_process.get_cpu_percent()
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
            family=c.family, type=c.type, pid=psutil_process.pid)

        try:
          conn.state = c.status
        except ValueError:
          logging.info("Encountered unknown connection status (%s).", c.status)

        try:
          conn.local_address.ip, conn.local_address.port = c.laddr

          # Could be in state LISTEN.
          if c.raddr:
            conn.remote_address.ip, conn.remote_address.port = c.raddr
        except AttributeError:
          conn.local_address.ip, conn.local_address.port = c.local_address

          # Could be in state LISTEN.
          if c.remote_address:
            (conn.remote_address.ip,
             conn.remote_address.port) = c.remote_address

    except (psutil.NoSuchProcess, psutil.AccessDenied):
      pass

    return response


class SoftwarePackage(rdf_structs.RDFProtoStruct):
  """Represent an installed package on the client."""
  protobuf = sysinfo_pb2.SoftwarePackage


class SoftwarePackages(rdf_protodict.RDFValueArray):
  """A list of installed packages on the system."""
  rdf_type = SoftwarePackage


class LogMessage(rdf_structs.RDFProtoStruct):
  """A log message sent from the client to the server."""
  protobuf = jobs_pb2.PrintStr


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

    raise ValueError("PEP 425 Signature not set - this is likely an old "
                     "component file, please back it up and remove it.")

  @classmethod
  def FromCurrentSystem(cls):
    """Fill a Uname from the currently running platform."""
    uname = platform.uname()
    fqdn = socket.getfqdn()
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
      release = platform.linux_distribution()[0]  # Ubuntu
      version = platform.linux_distribution()[1]  # 12.04

    # Emulate PEP 425 naming conventions - e.g. cp27-cp27mu-linux_x86_64.
    if pep425tags:
      pep425tag = "%s%s-%s-%s" % (
          pep425tags.get_abbr_impl(), pep425tags.get_impl_ver(),
          str(pep425tags.get_abi_tag()).lower(), pep425tags.get_platform())
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
  protobuf = jobs_pb2.StartupInfo
  rdf_deps = [
      ClientInformation,
      rdfvalue.RDFDatetime,
  ]


class WindowsServiceInformation(rdf_structs.RDFProtoStruct):
  """Windows Service."""
  protobuf = sysinfo_pb2.WindowsServiceInformation
  rdf_deps = [
      rdf_protodict.Dict,
      rdf_client_fs.StatEntry,
  ]


class OSXServiceInformation(rdf_structs.RDFProtoStruct):
  """OSX Service (launchagent/daemon)."""
  protobuf = sysinfo_pb2.OSXServiceInformation
  rdf_deps = [
      rdfvalue.RDFURN,
  ]


class LinuxServiceInformation(rdf_structs.RDFProtoStruct):
  """Linux Service (init/upstart/systemd)."""
  protobuf = sysinfo_pb2.LinuxServiceInformation
  rdf_deps = [
      rdf_protodict.AttributedDict,
      SoftwarePackage,
      rdf_client_fs.StatEntry,
  ]


# Start of the Registry Specific Data types
class RunKey(rdf_structs.RDFProtoStruct):
  protobuf = sysinfo_pb2.RunKey


class RunKeyEntry(rdf_protodict.RDFValueArray):
  """Structure of a Run Key entry with keyname, filepath, and last written."""
  rdf_type = RunKey


class ClientCrash(rdf_structs.RDFProtoStruct):
  """Details of a client crash."""
  protobuf = jobs_pb2.ClientCrash
  rdf_deps = [
      ClientInformation,
      ClientURN,
      rdfvalue.RDFDatetime,
      rdfvalue.SessionID,
  ]


class ClientSummary(rdf_structs.RDFProtoStruct):
  """Object containing client's summary data."""
  protobuf = jobs_pb2.ClientSummary
  rdf_deps = [
      ClientInformation,
      ClientURN,
      rdf_client_network.Interface,
      rdfvalue.RDFDatetime,
      Uname,
      User,
  ]


class VersionString(rdfvalue.RDFString):

  @property
  def versions(self):
    version = unicode(self)
    result = []
    for x in version.split("."):
      try:
        result.append(int(x))
      except ValueError:
        break

    return result
