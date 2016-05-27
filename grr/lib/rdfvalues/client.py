#!/usr/bin/env python
"""AFF4 RDFValue implementations for client information.

This module contains the RDFValue implementations used to communicate with the
client.
"""

from hashlib import sha256

import platform
import re
import socket
import stat

from grr.lib import ipv6_utils
from grr.lib import rdfvalue
from grr.lib import type_info
from grr.lib import utils

from grr.lib.rdfvalues import protodict
from grr.lib.rdfvalues import standard
from grr.lib.rdfvalues import structs

from grr.proto import flows_pb2
from grr.proto import jobs_pb2
from grr.proto import knowledge_base_pb2
from grr.proto import sysinfo_pb2

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
  def FromPublicKey(cls, public_key):
    """An alternate constructor which generates a new client id."""
    return cls("C.%s" % (sha256(public_key).digest()[:8].encode("hex")))

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


class PwEntry(structs.RDFProtoStruct):
  """Information about password structures."""
  protobuf = knowledge_base_pb2.PwEntry


class Group(structs.RDFProtoStruct):
  """Information about system posix groups."""
  protobuf = knowledge_base_pb2.Group


class KnowledgeBase(structs.RDFProtoStruct):
  """Information about the system and users."""
  protobuf = knowledge_base_pb2.KnowledgeBase

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

    user = self.GetUser(sid=kb_user.sid,
                        uid=kb_user.uid,
                        username=kb_user.username)
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

    fields.remove("users")
    for field in self.users.type_descriptor.type.type_infos.descriptor_names:
      fields.add("users.%s" % field)
    return sorted(fields)


class User(structs.RDFProtoStruct):
  """Information about the users."""
  protobuf = knowledge_base_pb2.User

  def __init__(self, initializer=None, age=None, **kwargs):
    if isinstance(initializer, KnowledgeBaseUser):
      # KnowledgeBaseUser was renamed to User, the protos are identical. This
      # allows for backwards compatibility with clients returning KBUser
      # objects.
      # TODO(user): remove once all clients are newer than 3.0.7.1.
      super(User, self).__init__(initializer=initializer.SerializeToString(),
                                 age=age,
                                 **kwargs)
    else:
      super(User, self).__init__(initializer=initializer, age=age, **kwargs)


class KnowledgeBaseUser(User):
  """Backwards compatibility for old clients.

  Linux client action EnumerateUsers previously returned KnowledgeBaseUser
  objects.
  """


class NetworkEndpoint(structs.RDFProtoStruct):
  protobuf = sysinfo_pb2.NetworkEndpoint


class NetworkConnection(structs.RDFProtoStruct):
  """Information about a single network connection."""
  protobuf = sysinfo_pb2.NetworkConnection


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

  @property
  def human_readable_address(self):
    if self.human_readable:
      return self.human_readable
    else:
      try:
        if self.address_type == NetworkAddress.Family.INET:
          return socket.inet_ntoa(str(self.packed_bytes))
        else:
          return ipv6_utils.InetNtoA(str(self.packed_bytes))
      except ValueError as e:
        return str(e)

  @human_readable_address.setter
  def human_readable_address(self, value):
    if ":" in value:
      # IPv6
      self.address_type = NetworkAddress.Family.INET6
      self.packed_bytes = ipv6_utils.InetAtoN(value)
    else:
      # IPv4
      self.address_type = NetworkAddress.Family.INET
      self.packed_bytes = socket.inet_aton(value)


class DNSClientConfiguration(structs.RDFProtoStruct):
  """DNS client config."""
  protobuf = sysinfo_pb2.DNSClientConfiguration


class MacAddress(rdfvalue.RDFBytes):
  """A MAC address."""

  @property
  def human_readable_address(self):
    return self._value.encode("hex")


class Interface(structs.RDFProtoStruct):
  """A network interface on the client system."""
  protobuf = jobs_pb2.Interface

  def GetIPAddresses(self):
    """Return a list of IP addresses."""
    results = []
    for address in self.addresses:
      if address.human_readable:
        results.append(address.human_readable)
      else:
        if address.address_type == NetworkAddress.Family.INET:
          results.append(socket.inet_ntop(socket.AF_INET, str(
              address.packed_bytes)))
        else:
          results.append(socket.inet_ntop(socket.AF_INET6, str(
              address.packed_bytes)))
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


class Volume(structs.RDFProtoStruct):
  """A disk volume on the client."""
  protobuf = sysinfo_pb2.Volume

  def FreeSpacePercent(self):
    try:
      return (self.actual_available_allocation_units /
              float(self.total_allocation_units)) * 100.0
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


class WindowsVolume(structs.RDFProtoStruct):
  """A disk volume on a windows client."""
  protobuf = sysinfo_pb2.WindowsVolume


class UnixVolume(structs.RDFProtoStruct):
  """A disk volume on a unix client."""
  protobuf = sysinfo_pb2.UnixVolume


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
  protobuf = jobs_pb2.CpuSample

  # The total number of samples this sample represents - used for running
  # averages.
  _total_samples = 1

  def Average(self, sample):
    """Updates this sample from the new sample."""
    # For now we only average the cpu_percent
    self.timestamp = sample.timestamp
    self.user_cpu_time = sample.user_cpu_time
    self.system_cpu_time = sample.system_cpu_time

    # Update the average from the new sample point.
    self.cpu_percent = (
        self.cpu_percent * self._total_samples + sample.cpu_percent) / (
            self._total_samples + 1)

    self._total_samples += 1


class IOSample(structs.RDFProtoStruct):
  protobuf = jobs_pb2.IOSample

  def Average(self, sample):
    """Updates this sample from the new sample."""
    # For now we just copy the new sample to ourselves.
    self.timestamp = sample.timestamp
    self.read_bytes = sample.read_bytes
    self.write_bytes = sample.write_bytes


class ClientStats(structs.RDFProtoStruct):
  """A client stat object."""
  protobuf = jobs_pb2.ClientStats

  def DownsampleList(self, samples, interval):
    """Reduces samples at different timestamps into interval time bins."""
    # The current bin we are calculating (initializes to the first bin).
    current_bin = None

    # The last sample we see in the current bin. We always emit the last sample
    # in the current bin.
    last_sample_seen = None

    for sample in samples:
      timestamp = sample.timestamp.AsSecondsFromEpoch()

      # The time bin this sample belongs to.
      time_bin = timestamp - (timestamp % interval)

      # Initialize to the first bin, but do not emit anything yet until we
      # switch bins.
      if current_bin is None:
        current_bin = time_bin
        last_sample_seen = sample

      # If the current sample is not in the current bin we switch bins.
      elif current_bin != time_bin and last_sample_seen:
        # Emit the last seen bin.
        yield last_sample_seen

        # Move to the next bin.
        current_bin = time_bin
        last_sample_seen = sample

      else:
        # Update the last_sample_seen with the new sample taking averages if
        # needed.
        last_sample_seen.Average(sample)

    # Emit the last sample especially as part of the last bin.
    if last_sample_seen:
      yield last_sample_seen

  def DownSample(self, sampling_interval=60):
    """Downsamples the data to save space.

    Args:
      sampling_interval: The sampling interval in seconds.
    Returns:
      New ClientStats object with cpu and IO samples downsampled.
    """
    result = ClientStats(self)
    result.cpu_samples = self.DownsampleList(self.cpu_samples,
                                             sampling_interval)
    result.io_samples = self.DownsampleList(self.io_samples, sampling_interval)
    return result


class BufferReference(structs.RDFProtoStruct):
  """Stores information about a buffer in a file on the client."""
  protobuf = jobs_pb2.BufferReference

  def __eq__(self, other):
    return self.data == other


class Process(structs.RDFProtoStruct):
  """Represent a process on the client."""
  protobuf = sysinfo_pb2.Process


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


class Iterator(structs.RDFProtoStruct):
  """An Iterated client action is one which can be resumed on the client."""
  protobuf = jobs_pb2.Iterator


class StatEntry(structs.RDFProtoStruct):
  """Represent an extended stat response."""
  protobuf = jobs_pb2.StatEntry


class FindSpec(structs.RDFProtoStruct):
  """A find specification."""
  protobuf = jobs_pb2.FindSpec

  dependencies = dict(RegularExpression=standard.RegularExpression)

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


class ExecuteBinaryResponse(structs.RDFProtoStruct):
  protobuf = jobs_pb2.ExecuteBinaryResponse


class ExecutePythonRequest(structs.RDFProtoStruct):
  protobuf = jobs_pb2.ExecutePythonRequest


class ExecutePythonResponse(structs.RDFProtoStruct):
  protobuf = jobs_pb2.ExecutePythonResponse


class ExecuteRequest(structs.RDFProtoStruct):
  protobuf = jobs_pb2.ExecuteRequest


class CopyPathToFileRequest(structs.RDFProtoStruct):
  protobuf = jobs_pb2.CopyPathToFile


class ExecuteResponse(structs.RDFProtoStruct):
  protobuf = jobs_pb2.ExecuteResponse


class Uname(structs.RDFProtoStruct):
  """A protobuf to represent the current system."""
  protobuf = jobs_pb2.Uname

  @property
  def arch(self):
    """Return a more standard representation of the architecture."""
    if self.machine in ["x86_64", "AMD64", "i686"]:
      # 32 bit binaries running on AMD64 will still have a i386 arch.
      if self.architecture == "32bit":
        return "i386"

      return "amd64"
    elif self.machine in "x86":
      return "i386"

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
      pep425tag = "%s%s-%s-%s" % (pep425tags.get_abbr_impl(),
                                  pep425tags.get_impl_ver(),
                                  str(pep425tags.get_abi_tag()).lower(),
                                  pep425tags.get_platform())
    else:
      # For example: windows_7_amd64
      pep425tag = "%s_%s_%s" % (system, release, architecture)

    return cls(system=system,
               architecture=architecture,
               node=uname[1],
               release=release,
               version=version,
               machine=uname[4],              # x86, x86_64
               kernel=kernel,
               fqdn=fqdn,
               pep425tag=pep425tag,
              )


class StartupInfo(structs.RDFProtoStruct):
  protobuf = jobs_pb2.StartupInfo


class SendFileRequest(structs.RDFProtoStruct):
  protobuf = jobs_pb2.SendFileRequest

  def Validate(self):
    self.pathspec.Validate()

    if not self.host:
      raise ValueError("A host must be specified.")


class ListDirRequest(structs.RDFProtoStruct):
  protobuf = jobs_pb2.ListDirRequest


class DumpProcessMemoryRequest(structs.RDFProtoStruct):
  protobuf = jobs_pb2.DumpProcessMemoryRequest


class FingerprintTuple(structs.RDFProtoStruct):
  protobuf = jobs_pb2.FingerprintTuple


class FingerprintRequest(structs.RDFProtoStruct):
  protobuf = jobs_pb2.FingerprintRequest

  def AddRequest(self, *args, **kw):
    self.tuples.Append(*args, **kw)


class FingerprintResponse(structs.RDFProtoStruct):
  """Proto containing dicts with hashes."""
  protobuf = jobs_pb2.FingerprintResponse

  def GetFingerprint(self, name):
    """Gets the first fingerprint type from the protobuf."""
    for result in self.results:
      if result.GetItem("name") == name:
        return result


class GrepSpec(structs.RDFProtoStruct):
  protobuf = jobs_pb2.GrepSpec

  def Validate(self):
    self.target.Validate()


class BareGrepSpec(structs.RDFProtoStruct):
  """A GrepSpec without a target."""
  protobuf = flows_pb2.BareGrepSpec


class WMIRequest(structs.RDFProtoStruct):
  protobuf = jobs_pb2.WmiRequest


class WindowsServiceInformation(structs.RDFProtoStruct):
  """Windows Service."""
  protobuf = sysinfo_pb2.WindowsServiceInformation


class OSXServiceInformation(structs.RDFProtoStruct):
  """OSX Service (launchagent/daemon)."""
  protobuf = sysinfo_pb2.OSXServiceInformation


class LinuxServiceInformation(structs.RDFProtoStruct):
  """Linux Service (init/upstart/systemd)."""
  protobuf = sysinfo_pb2.LinuxServiceInformation


class ClientResources(structs.RDFProtoStruct):
  """An RDFValue class representing the client resource usage."""
  protobuf = jobs_pb2.ClientResources

  dependencies = dict(ClientURN=ClientURN, RDFURN=rdfvalue.RDFURN)


class StatFSRequest(structs.RDFProtoStruct):
  protobuf = jobs_pb2.StatFSRequest


# Start of the Registry Specific Data types
class RunKey(structs.RDFProtoStruct):
  protobuf = sysinfo_pb2.RunKey


class RunKeyEntry(protodict.RDFValueArray):
  """Structure of a Run Key entry with keyname, filepath, and last written."""
  rdf_type = RunKey


class MRUFile(structs.RDFProtoStruct):
  protobuf = sysinfo_pb2.MRUFile


class MRUFolder(protodict.RDFValueArray):
  """Structure describing Most Recently Used (MRU) files."""
  rdf_type = MRUFile


class AFF4ObjectSummary(structs.RDFProtoStruct):
  """A summary of an AFF4 object.

  AFF4Collection objects maintain a list of AFF4 objects. To make it easier to
  filter and search these collections, we need to store a summary of each AFF4
  object inside the collection (so we do not need to open every object for
  filtering).

  This summary is maintained in the RDFProto instance.
  """
  protobuf = jobs_pb2.AFF4ObjectSummary


class ClientCrash(structs.RDFProtoStruct):
  """Details of a client crash."""
  protobuf = jobs_pb2.ClientCrash


class ClientSummary(structs.RDFProtoStruct):
  """Object containing client's summary data."""
  protobuf = jobs_pb2.ClientSummary


class GetClientStatsRequest(structs.RDFProtoStruct):
  """Request for GetClientStats action."""
  protobuf = jobs_pb2.GetClientStatsRequest


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


class LoadComponent(structs.RDFProtoStruct):
  """Request to launch a client action through a component."""
  protobuf = jobs_pb2.LoadComponent


class ClientComponentSummary(structs.RDFProtoStruct):
  """A client component summary."""
  protobuf = jobs_pb2.ClientComponentSummary


class ClientComponent(structs.RDFProtoStruct):
  """A client component."""
  protobuf = jobs_pb2.ClientComponent
