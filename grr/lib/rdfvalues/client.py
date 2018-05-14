#!/usr/bin/env python
"""AFF4 RDFValue implementations for client information.

This module contains the RDFValue implementations used to communicate with the
client.
"""

import hashlib
import logging
import platform
import re
import socket
import stat
import struct

import ipaddr
import psutil

from grr.lib import ipv6_utils
from grr.lib import rdfvalue
from grr.lib import type_info
from grr.lib import utils

from grr.lib.rdfvalues import crypto as rdf_crypto
from grr.lib.rdfvalues import paths
from grr.lib.rdfvalues import protodict
from grr.lib.rdfvalues import standard
from grr.lib.rdfvalues import structs

from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import knowledge_base_pb2
from grr_response_proto import sysinfo_pb2

# ntop does not exist on Windows.
# pylint: disable=g-socket-inet-aton,g-socket-inet-ntoa

# We try to support PEP 425 style component names if possible. This makes it
# possible to have wheel as an optional dependency.
try:
  from wheel import pep425tags  # pylint: disable=g-import-not-at-top
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

  def ParseFromString(self, value):
    """Parse a string into a client URN.

    Convert case so that all URNs are of the form C.[0-9a-f].

    Args:
      value: string value to parse
    """
    value = value.strip()

    super(ClientURN, self).ParseFromString(value)

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
      return bool(cls.CLIENT_ID_RE.match(str(value)))

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

    mpi_format = struct.pack(">i", len(raw_n) + 1) + "\x00" + raw_n

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
    if not isinstance(path, basestring):
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


class PCIDevice(structs.RDFProtoStruct):
  """A PCI device on the client.

  This class describes a PCI device located on the client.
  """
  protobuf = sysinfo_pb2.PCIDevice


# These are objects we store as attributes of the client.
class Filesystem(structs.RDFProtoStruct):
  """A filesystem on the client.

  This class describes a filesystem mounted on the client.
  """
  protobuf = sysinfo_pb2.Filesystem
  rdf_deps = [
      protodict.AttributedDict,
  ]


class Filesystems(protodict.RDFValueArray):
  """An array of client filesystems.

  This is used to represent the list of valid filesystems on the client.
  """
  rdf_type = Filesystem


class FolderInformation(structs.RDFProtoStruct):
  """Representation of Window's special folders information for a User.

  Windows maintains a list of "Special Folders" which are used to organize a
  user's home directory. Knowledge about these is required in order to resolve
  the location of user specific items, e.g. the Temporary folder, or the
  Internet cache.
  """
  protobuf = jobs_pb2.FolderInformation


class PackageRepository(structs.RDFProtoStruct):
  """Description of the configured repositories (Yum etc).

  Describes the configured software package repositories.
  """
  protobuf = sysinfo_pb2.PackageRepository


class ManagementAgent(structs.RDFProtoStruct):
  """Description of the running management agent (puppet etc).

  Describes the state, last run timestamp, and name of the management agent
  installed on the system.
  """
  protobuf = sysinfo_pb2.ManagementAgent
  rdf_deps = [
      rdfvalue.RDFDatetime,
  ]


class PwEntry(structs.RDFProtoStruct):
  """Information about password structures."""
  protobuf = knowledge_base_pb2.PwEntry


class Group(structs.RDFProtoStruct):
  """Information about system posix groups."""
  protobuf = knowledge_base_pb2.Group
  rdf_deps = [
      PwEntry,
  ]


class User(structs.RDFProtoStruct):
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


class KnowledgeBase(structs.RDFProtoStruct):
  """Information about the system and users."""
  protobuf = knowledge_base_pb2.KnowledgeBase
  rdf_deps = [
      User,
  ]

  def _CreateNewUser(self, kb_user):
    self.users.Append(kb_user)
    return ["users.%s" % k for k in kb_user.AsDict().keys()]

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
      for key, val in kb_user.AsDict().items():
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


class NetworkEndpoint(structs.RDFProtoStruct):
  protobuf = sysinfo_pb2.NetworkEndpoint


class NetworkConnection(structs.RDFProtoStruct):
  """Information about a single network connection."""
  protobuf = sysinfo_pb2.NetworkConnection
  rdf_deps = [
      NetworkEndpoint,
  ]


class Connections(protodict.RDFValueArray):
  """A list of connections on the host."""
  rdf_type = NetworkConnection


class NetworkAddress(structs.RDFProtoStruct):
  """A network address.

  We'd prefer to use socket.inet_pton and  inet_ntop here, but they aren't
  available on windows before python 3.4. So we use the older IPv4 functions for
  v4 addresses and our own pure python implementations for IPv6.
  """
  protobuf = jobs_pb2.NetworkAddress
  rdf_deps = [
      rdfvalue.RDFBytes,
  ]

  @property
  def human_readable_address(self):
    if self.human_readable:
      return self.human_readable
    else:
      try:
        if self.address_type == NetworkAddress.Family.INET:
          return ipv6_utils.InetNtoP(socket.AF_INET, str(self.packed_bytes))
        else:
          return ipv6_utils.InetNtoP(socket.AF_INET6, str(self.packed_bytes))
      except ValueError as e:
        return str(e)

  @human_readable_address.setter
  def human_readable_address(self, value):
    if ":" in value:
      # IPv6
      self.address_type = NetworkAddress.Family.INET6
      self.packed_bytes = ipv6_utils.InetPtoN(socket.AF_INET6, value)
    else:
      # IPv4
      self.address_type = NetworkAddress.Family.INET
      self.packed_bytes = ipv6_utils.InetPtoN(socket.AF_INET, value)

  def AsIPAddr(self):
    """Returns the ip as an ipaddr.IPADdress object.

    Raises a ValueError if the stored data does not represent a valid ip.
    """
    try:
      if self.address_type == NetworkAddress.Family.INET:
        return ipaddr.IPv4Address(self.human_readable_address)
      elif self.address_type == NetworkAddress.Family.INET6:
        return ipaddr.IPv6Address(self.human_readable_address)
      else:
        raise ValueError("Unknown address type: %d" % self.address_type)
    except ipaddr.AddressValueError:
      raise ValueError("Invalid IP address: %s" % self.human_readable_address)


class DNSClientConfiguration(structs.RDFProtoStruct):
  """DNS client config."""
  protobuf = sysinfo_pb2.DNSClientConfiguration


class MacAddress(rdfvalue.RDFBytes):
  """A MAC address."""

  @property
  def human_readable_address(self):
    return self._value.encode("hex")

  @human_readable_address.setter
  def human_readable_address(self, value):
    self._value = value.decode("hex")


class Interface(structs.RDFProtoStruct):
  """A network interface on the client system."""
  protobuf = jobs_pb2.Interface
  rdf_deps = [
      MacAddress,
      NetworkAddress,
      rdfvalue.RDFDatetime,
  ]

  def GetIPAddresses(self):
    """Return a list of IP addresses."""
    results = []
    for address in self.addresses:
      if address.human_readable:
        results.append(address.human_readable)
      else:
        if address.address_type == NetworkAddress.Family.INET:
          results.append(
              ipv6_utils.InetNtoP(socket.AF_INET, str(address.packed_bytes)))
        else:
          results.append(
              ipv6_utils.InetNtoP(socket.AF_INET6, str(address.packed_bytes)))
    return results


class Interfaces(protodict.RDFValueArray):
  """The list of interfaces on a host."""
  rdf_type = Interface

  def GetIPAddresses(self):
    """Return the list of IP addresses."""
    results = []
    for interface in self:
      results += interface.GetIPAddresses()
    return results


class WindowsVolume(structs.RDFProtoStruct):
  """A disk volume on a windows client."""
  protobuf = sysinfo_pb2.WindowsVolume


class UnixVolume(structs.RDFProtoStruct):
  """A disk volume on a unix client."""
  protobuf = sysinfo_pb2.UnixVolume


class Volume(structs.RDFProtoStruct):
  """A disk volume on the client."""
  protobuf = sysinfo_pb2.Volume
  rdf_deps = [
      rdfvalue.RDFDatetime,
      UnixVolume,
      WindowsVolume,
  ]

  def FreeSpacePercent(self):
    try:
      return (self.actual_available_allocation_units / float(
          self.total_allocation_units)) * 100.0
    except ZeroDivisionError:
      return 100

  def FreeSpaceBytes(self):
    return self.AUToBytes(self.actual_available_allocation_units)

  def AUToBytes(self, allocation_units):
    """Convert a number of allocation units to bytes."""
    return (allocation_units * self.sectors_per_allocation_unit *
            self.bytes_per_sector)

  def AUToGBytes(self, allocation_units):
    """Convert a number of allocation units to GigaBytes."""
    return self.AUToBytes(allocation_units) / 1000.0**3

  def Name(self):
    """Return the best available name for this volume."""
    return (self.name or self.device_path or self.windowsvolume.drive_letter or
            self.unixvolume.mount_point or None)


class DiskUsage(structs.RDFProtoStruct):
  protobuf = sysinfo_pb2.DiskUsage


class Volumes(protodict.RDFValueArray):
  """A list of disk volumes on the client."""
  rdf_type = Volume


class HardwareInfo(structs.RDFProtoStruct):
  """Various hardware information."""
  protobuf = sysinfo_pb2.HardwareInfo


class ClientInformation(structs.RDFProtoStruct):
  """The GRR client information."""
  protobuf = jobs_pb2.ClientInformation


class CpuSeconds(structs.RDFProtoStruct):
  """CPU usage is reported as both a system and user components."""
  protobuf = jobs_pb2.CpuSeconds


class CpuSample(structs.RDFProtoStruct):
  """A single CPU sample."""
  protobuf = jobs_pb2.CpuSample
  rdf_deps = [
      rdfvalue.RDFDatetime,
  ]

  @classmethod
  def FromMany(cls, samples):
    """Constructs a single sample that best represents a list of samples.

    Args:
      samples: An iterable collection of `CpuSample` instances.

    Returns:
      A `CpuSample` instance representing `samples`.

    Raises:
      ValueError: If `samples` is empty.
    """
    if not samples:
      raise ValueError("Empty `samples` argument")

    # It only makes sense to average the CPU percentage. For all other values
    # we simply take the biggest of them.
    cpu_percent = sum(sample.cpu_percent for sample in samples) / len(samples)

    return CpuSample(
        timestamp=max(sample.timestamp for sample in samples),
        cpu_percent=cpu_percent,
        user_cpu_time=max(sample.user_cpu_time for sample in samples),
        system_cpu_time=max(sample.system_cpu_time for sample in samples))


class IOSample(structs.RDFProtoStruct):
  protobuf = jobs_pb2.IOSample
  rdf_deps = [
      rdfvalue.RDFDatetime,
  ]

  @classmethod
  def FromMany(cls, samples):
    """Constructs a single sample that best represents a list of samples.

    Args:
      samples: An iterable collection of `IOSample` instances.

    Returns:
      An `IOSample` instance representing `samples`.

    Raises:
      ValueError: If `samples` is empty.
    """
    if not samples:
      raise ValueError("Empty `samples` argument")

    return IOSample(
        timestamp=max(sample.timestamp for sample in samples),
        read_bytes=max(sample.read_bytes for sample in samples),
        write_bytes=max(sample.write_bytes for sample in samples))


class ClientStats(structs.RDFProtoStruct):
  """A client stat object."""
  protobuf = jobs_pb2.ClientStats
  rdf_deps = [
      CpuSample,
      IOSample,
      rdfvalue.RDFDatetime,
  ]

  DEFAULT_SAMPLING_INTERVAL = rdfvalue.Duration("60s")

  @classmethod
  def Downsampled(cls, stats, interval=None):
    """Constructs a copy of given stats but downsampled to given interval.

    Args:
      stats: A `ClientStats` instance.
      interval: A downsampling interval.

    Returns:
      A downsampled `ClientStats` instance.
    """
    interval = interval or cls.DEFAULT_SAMPLING_INTERVAL

    result = cls(stats)
    result.cpu_samples = cls._Downsample(
        kind=CpuSample, samples=stats.cpu_samples, interval=interval)
    result.io_samples = cls._Downsample(
        kind=IOSample, samples=stats.io_samples, interval=interval)
    return result

  @classmethod
  def _Downsample(cls, kind, samples, interval):
    buckets = {}
    for sample in samples:
      bucket = buckets.setdefault(sample.timestamp.Floor(interval), [])
      bucket.append(sample)

    for bucket in buckets.itervalues():
      yield kind.FromMany(bucket)


class BufferReference(structs.RDFProtoStruct):
  """Stores information about a buffer in a file on the client."""
  protobuf = jobs_pb2.BufferReference
  rdf_deps = [
      paths.PathSpec,
  ]

  def __eq__(self, other):
    return self.data == other


class Process(structs.RDFProtoStruct):
  """Represent a process on the client."""
  protobuf = sysinfo_pb2.Process
  rdf_deps = [
      NetworkConnection,
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
      response.ctime = long(psutil_process.create_time() * 1e6)
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


class SoftwarePackage(structs.RDFProtoStruct):
  """Represent an installed package on the client."""
  protobuf = sysinfo_pb2.SoftwarePackage


class SoftwarePackages(protodict.RDFValueArray):
  """A list of installed packages on the system."""
  rdf_type = SoftwarePackage


class StatMode(rdfvalue.RDFInteger):
  """The mode of a file."""
  data_store_type = "unsigned_integer"

  def __unicode__(self):
    """Pretty print the file mode."""
    type_char = "-"

    mode = int(self)
    if stat.S_ISREG(mode):
      type_char = "-"
    elif stat.S_ISBLK(mode):
      type_char = "b"
    elif stat.S_ISCHR(mode):
      type_char = "c"
    elif stat.S_ISDIR(mode):
      type_char = "d"
    elif stat.S_ISFIFO(mode):
      type_char = "p"
    elif stat.S_ISLNK(mode):
      type_char = "l"
    elif stat.S_ISSOCK(mode):
      type_char = "s"

    mode_template = "rwx" * 3
    # Strip the "0b"
    bin_mode = bin(int(self))[2:]
    bin_mode = bin_mode[-9:]
    bin_mode = "0" * (9 - len(bin_mode)) + bin_mode

    bits = []
    for i in range(len(mode_template)):
      if bin_mode[i] == "1":
        bit = mode_template[i]
      else:
        bit = "-"

      bits.append(bit)

    if stat.S_ISUID & mode:
      bits[2] = "S"
    if stat.S_ISGID & mode:
      bits[5] = "S"
    if stat.S_ISVTX & mode:
      if bits[8] == "x":
        bits[8] = "t"
      else:
        bits[8] = "T"

    return type_char + "".join(bits)

  def __str__(self):
    return utils.SmartStr(self.__unicode__())


class StatExtFlagsOsx(rdfvalue.RDFInteger):
  """Extended file attributes for Mac (set by `chflags`)."""

  data_store_type = "unsigned_integer_32"


class StatExtFlagsLinux(rdfvalue.RDFInteger):
  """Extended file attributes as reported by `lsattr`."""

  data_store_type = "unsigned_integer_32"


class Iterator(structs.RDFProtoStruct):
  """An Iterated client action is one which can be resumed on the client."""
  protobuf = jobs_pb2.Iterator
  rdf_deps = [
      protodict.Dict,
  ]


class ExtAttr(structs.RDFProtoStruct):
  """An RDF value representing an extended attributes of a file."""

  protobuf = jobs_pb2.StatEntry.ExtAttr


class StatEntry(structs.RDFProtoStruct):
  """Represent an extended stat response."""
  protobuf = jobs_pb2.StatEntry
  rdf_deps = [
      protodict.DataBlob,
      paths.PathSpec,
      rdfvalue.RDFDatetimeSeconds,
      StatMode,
      StatExtFlagsOsx,
      StatExtFlagsLinux,
      ExtAttr,
  ]

  def AFF4Path(self, client_urn):
    return self.pathspec.AFF4Path(client_urn)


class FindSpec(structs.RDFProtoStruct):
  """A find specification."""
  protobuf = jobs_pb2.FindSpec
  rdf_deps = [
      paths.GlobExpression,
      Iterator,
      paths.PathSpec,
      rdfvalue.RDFDatetime,
      standard.RegularExpression,
      StatEntry,
      StatMode,
  ]

  def Validate(self):
    """Ensure the pathspec is valid."""
    self.pathspec.Validate()

    if (self.HasField("start_time") and self.HasField("end_time") and
        self.start_time > self.end_time):
      raise ValueError("Start time must be before end time.")

    if not self.path_regex and not self.data_regex and not self.path_glob:
      raise ValueError("A Find specification can not contain both an empty "
                       "path regex and an empty data regex")


class LogMessage(structs.RDFProtoStruct):
  """A log message sent from the client to the server."""
  protobuf = jobs_pb2.PrintStr


class EchoRequest(structs.RDFProtoStruct):
  protobuf = jobs_pb2.PrintStr


class ExecuteBinaryRequest(structs.RDFProtoStruct):
  protobuf = jobs_pb2.ExecuteBinaryRequest
  rdf_deps = [
      rdf_crypto.SignedBlob,
  ]


class ExecuteBinaryResponse(structs.RDFProtoStruct):
  protobuf = jobs_pb2.ExecuteBinaryResponse


class ExecutePythonRequest(structs.RDFProtoStruct):
  protobuf = jobs_pb2.ExecutePythonRequest
  rdf_deps = [
      protodict.Dict,
      rdf_crypto.SignedBlob,
  ]


class ExecutePythonResponse(structs.RDFProtoStruct):
  protobuf = jobs_pb2.ExecutePythonResponse


class ExecuteRequest(structs.RDFProtoStruct):
  protobuf = jobs_pb2.ExecuteRequest


class CopyPathToFileRequest(structs.RDFProtoStruct):
  protobuf = jobs_pb2.CopyPathToFile
  rdf_deps = [
      paths.PathSpec,
  ]


class ExecuteResponse(structs.RDFProtoStruct):
  protobuf = jobs_pb2.ExecuteResponse
  rdf_deps = [
      ExecuteRequest,
  ]


class Uname(structs.RDFProtoStruct):
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


class StartupInfo(structs.RDFProtoStruct):
  protobuf = jobs_pb2.StartupInfo
  rdf_deps = [
      ClientInformation,
      rdfvalue.RDFDatetime,
  ]


class SendFileRequest(structs.RDFProtoStruct):
  protobuf = jobs_pb2.SendFileRequest
  rdf_deps = [
      rdf_crypto.AES128Key,
      paths.PathSpec,
  ]

  def Validate(self):
    self.pathspec.Validate()

    if not self.host:
      raise ValueError("A host must be specified.")


class ListDirRequest(structs.RDFProtoStruct):
  protobuf = jobs_pb2.ListDirRequest
  rdf_deps = [
      Iterator,
      paths.PathSpec,
  ]


class GetFileStatRequest(structs.RDFProtoStruct):

  protobuf = jobs_pb2.GetFileStatRequest
  rdf_deps = [
      paths.PathSpec,
  ]


class FingerprintTuple(structs.RDFProtoStruct):
  protobuf = jobs_pb2.FingerprintTuple


class FingerprintRequest(structs.RDFProtoStruct):
  protobuf = jobs_pb2.FingerprintRequest
  rdf_deps = [
      FingerprintTuple,
      paths.PathSpec,
  ]

  def AddRequest(self, *args, **kw):
    self.tuples.Append(*args, **kw)


class FingerprintResponse(structs.RDFProtoStruct):
  """Proto containing dicts with hashes."""
  protobuf = jobs_pb2.FingerprintResponse
  rdf_deps = [
      protodict.Dict,
      rdf_crypto.Hash,
      paths.PathSpec,
  ]

  def GetFingerprint(self, name):
    """Gets the first fingerprint type from the protobuf."""
    for result in self.results:
      if result.GetItem("name") == name:
        return result


class GrepSpec(structs.RDFProtoStruct):
  protobuf = jobs_pb2.GrepSpec
  rdf_deps = [
      standard.LiteralExpression,
      paths.PathSpec,
      standard.RegularExpression,
  ]

  def Validate(self):
    self.target.Validate()


class BareGrepSpec(structs.RDFProtoStruct):
  """A GrepSpec without a target."""
  protobuf = flows_pb2.BareGrepSpec
  rdf_deps = [
      standard.LiteralExpression,
      standard.RegularExpression,
  ]


class WMIRequest(structs.RDFProtoStruct):
  protobuf = jobs_pb2.WmiRequest


class WindowsServiceInformation(structs.RDFProtoStruct):
  """Windows Service."""
  protobuf = sysinfo_pb2.WindowsServiceInformation
  rdf_deps = [
      protodict.Dict,
      StatEntry,
  ]


class OSXServiceInformation(structs.RDFProtoStruct):
  """OSX Service (launchagent/daemon)."""
  protobuf = sysinfo_pb2.OSXServiceInformation
  rdf_deps = [
      rdfvalue.RDFURN,
  ]


class LinuxServiceInformation(structs.RDFProtoStruct):
  """Linux Service (init/upstart/systemd)."""
  protobuf = sysinfo_pb2.LinuxServiceInformation
  rdf_deps = [
      protodict.AttributedDict,
      SoftwarePackage,
      StatEntry,
  ]


class ClientResources(structs.RDFProtoStruct):
  """An RDFValue class representing the client resource usage."""
  protobuf = jobs_pb2.ClientResources
  rdf_deps = [
      ClientURN,
      CpuSeconds,
      rdfvalue.SessionID,
  ]


class StatFSRequest(structs.RDFProtoStruct):
  protobuf = jobs_pb2.StatFSRequest


# Start of the Registry Specific Data types
class RunKey(structs.RDFProtoStruct):
  protobuf = sysinfo_pb2.RunKey


class RunKeyEntry(protodict.RDFValueArray):
  """Structure of a Run Key entry with keyname, filepath, and last written."""
  rdf_type = RunKey


class ClientCrash(structs.RDFProtoStruct):
  """Details of a client crash."""
  protobuf = jobs_pb2.ClientCrash
  rdf_deps = [
      ClientInformation,
      ClientURN,
      rdfvalue.RDFDatetime,
      rdfvalue.SessionID,
  ]


class ClientSummary(structs.RDFProtoStruct):
  """Object containing client's summary data."""
  protobuf = jobs_pb2.ClientSummary
  rdf_deps = [
      ClientInformation,
      ClientURN,
      Interface,
      rdfvalue.RDFDatetime,
      Uname,
      User,
  ]


class GetClientStatsRequest(structs.RDFProtoStruct):
  """Request for GetClientStats action."""
  protobuf = jobs_pb2.GetClientStatsRequest
  rdf_deps = [
      rdfvalue.RDFDatetime,
  ]


class VersionString(rdfvalue.RDFString):

  @property
  def versions(self):
    version = str(self)
    result = []
    for x in version.split("."):
      try:
        result.append(int(x))
      except ValueError:
        break

    return result


class ListNetworkConnectionsArgs(structs.RDFProtoStruct):
  """Args for the ListNetworkConnections client action."""
  protobuf = flows_pb2.ListNetworkConnectionsArgs


class BlobImageChunkDescriptor(structs.RDFProtoStruct):
  """A descriptor of a file chunk stored in VFS blob image."""

  protobuf = jobs_pb2.BlobImageChunkDescriptor
  rdf_deps = []


class BlobImageDescriptor(structs.RDFProtoStruct):
  """A descriptor of a file stored as VFS blob image."""

  protobuf = jobs_pb2.BlobImageDescriptor
  rdf_deps = [BlobImageChunkDescriptor]
