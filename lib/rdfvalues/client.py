#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.
"""AFF4 RDFValue implementations for client information.

This module contains the RDFValue implementations used to communicate with the
client.
"""

import re
import socket

from grr.lib import rdfvalue
from grr.lib import type_info
from grr.lib.rdfvalues import crypto
from grr.lib.rdfvalues import paths
from grr.lib.rdfvalues import protodict
from grr.proto import analysis_pb2
from grr.proto import jobs_pb2
from grr.proto import sysinfo_pb2


# These are objects we store as attributes of the client.
class Filesystem(rdfvalue.RDFProto):
  """A filesystem on the client.

  This class describes a filesystem mounted on the client.
  """
  _proto = sysinfo_pb2.Filesystem


class Filesystems(protodict.RDFValueArray):
  """An array of client filesystems.

  This is used to represent the list of valid filesystems on the client.
  """
  rdf_type = Filesystem


class FolderInformation(rdfvalue.RDFProto):
  """Representation of Window's special folders information for a User.

  Windows maintains a list of "Special Folders" which are used to organize a
  user's home directory. Knowledge about these is required in order to resolve
  the location of user specific items, e.g. the Temporary folder, or the
  Internet cache.
  """
  _proto = jobs_pb2.FolderInformation


class User(rdfvalue.RDFProto):
  """A user of the client system.

  This stores information related to a specific user of the client system.
  """
  _proto = jobs_pb2.UserAccount

  rdf_map = dict(special_folders=FolderInformation,
                 last_logon=rdfvalue.RDFDatetime)


class Users(protodict.RDFValueArray):
  """A list of user account on the client system."""
  rdf_type = User


class NetworkEndpoint(rdfvalue.RDFProto):
  _proto = sysinfo_pb2.NetworkEndpoint


class NetworkConnection(rdfvalue.RDFProto):
  """Information about a single network connection."""
  _proto = sysinfo_pb2.NetworkConnection

  rdf_map = dict(local_address=NetworkEndpoint,
                 remote_address=NetworkEndpoint)


class Connections(protodict.RDFValueArray):
  """A list of connections on the host."""
  rdf_type = NetworkConnection


class NetworkAddress(rdfvalue.RDFProto):
  """A network address."""
  _proto = jobs_pb2.NetworkAddress

  def HumanReadableAddress(self):
    if self.human_readable:
      return self.human_readable
    else:
      if self.address_type == rdfvalue.NetworkAddress.Enum("INET"):
        return socket.inet_ntop(socket.AF_INET, self.packed_bytes)
      else:
        return socket.inet_ntop(socket.AF_INET6, self.packed_bytes)


class Interface(rdfvalue.RDFProto):
  """A network interface on the client system."""
  _proto = jobs_pb2.Interface

  rdf_map = dict(addresses=NetworkAddress)

  def GetIPAddresses(self):
    """Return a list of IP addresses."""
    results = []
    for address in self.addresses:
      if address.human_readable:
        results.append(address.human_readable)
      else:
        if address.address_type == rdfvalue.NetworkAddress.Enum("INET"):
          results.append(socket.inet_ntop(socket.AF_INET,
                                          address.packed_bytes))
        else:
          results.append(socket.inet_ntop(socket.AF_INET6,
                                          address.packed_bytes))
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


# DEPRECATED - do not use.
class GRRConfig(rdfvalue.RDFProto):
  """The configuration of a GRR Client."""
  _proto = jobs_pb2.GRRConfig


class ClientInformation(rdfvalue.RDFProto):
  """The GRR client information."""
  _proto = jobs_pb2.ClientInformation


class CpuSeconds(rdfvalue.RDFProto):
  """CPU usage is reported as both a system and user components."""
  _proto = jobs_pb2.CpuSeconds


class CpuSample(rdfvalue.RDFProto):
  _proto = jobs_pb2.CpuSample

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
        self.cpu_percent * self._total_samples + sample.cpu_percent)/(
            self._total_samples + 1)

    self._total_samples += 1


class IOSample(rdfvalue.RDFProto):
  _proto = jobs_pb2.IOSample

  def Average(self, sample):
    """Updates this sample from the new sample."""
    # For now we just copy the new sample to ourselves.
    self.timestamp = sample.timestamp
    self.read_bytes = sample.read_bytes
    self.write_bytes = sample.write_bytes


class ClientStats(rdfvalue.RDFProto):
  """A client stat object."""
  _proto = jobs_pb2.ClientStats

  rdf_map = dict(cpu_samples=CpuSample,
                 io_samples=IOSample)

  def DownsampleList(self, samples, interval):
    """Reduces samples at different timestamps into interval time bins."""
    # The current bin we are calculating (initializes to the first bin).
    current_bin = None

    # The last sample we see in the current bin. We always emit the last sample
    # in the current bin.
    last_sample_seen = None

    for sample in samples:
      # The time bin this sample belongs to.
      time_bin = sample.timestamp - (sample.timestamp % interval)

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

  def DownSample(self, sampling_interval=int(60 * 1e6)):
    """Downsamples the data to save space."""
    self.cpu_samples = self.DownsampleList(self.cpu_samples, sampling_interval)
    self.io_samples = self.DownsampleList(self.io_samples, sampling_interval)


class DriverInstallTemplate(rdfvalue.RDFProto):
  """Driver specific information controlling default installation.

  This is sent to the client to instruct the client how to install this driver.
  """
  _proto = jobs_pb2.InstallDriverRequest

  rdf_map = dict(driver=crypto.SignedBlob)


class BufferReference(rdfvalue.RDFProto):
  """Stores information about a buffer in a file on the client."""
  _proto = jobs_pb2.BufferReadMessage

  def __eq__(self, other):
    return self._data.data == other

  rdf_map = dict(pathspec=rdfvalue.RDFPathSpec)


class Process(rdfvalue.RDFProto):
  """Represent a process on the client."""
  _proto = sysinfo_pb2.Process

  rdf_map = dict(connections=NetworkConnection)


class Processes(protodict.RDFValueArray):
  """A list of processes on the system."""
  rdf_type = Process


class StatMode(rdfvalue.RDFInteger):
  """The mode of a file."""

  def __unicode__(self):
    """Pretty print the file mode."""
    mode_template = "rwx" * 3
    mode = bin(int(self))[-9:]

    bits = []
    for i in range(len(mode_template)):
      if mode[i] == "1":
        bit = mode_template[i]
      else:
        bit = "-"

      bits.append(bit)

    return "".join(bits)


class Iterator(rdfvalue.RDFProto):
  """An Iterated client action is one which can be resumed on the client."""
  _proto = jobs_pb2.Iterator

  rdf_map = dict(client_state=rdfvalue.RDFProtoDict)


class StatEntry(rdfvalue.RDFProto):
  """Represent an extended stat response."""
  _proto = jobs_pb2.StatResponse

  # Translate these fields as RDFValue objects.
  rdf_map = dict(st_mtime=rdfvalue.RDFDatetimeSeconds,
                 st_atime=rdfvalue.RDFDatetimeSeconds,
                 st_ctime=rdfvalue.RDFDatetimeSeconds,
                 st_inode=rdfvalue.RDFInteger,
                 st_mode=StatMode,
                 st_dev=rdfvalue.RDFInteger,
                 st_nlink=rdfvalue.RDFInteger,
                 st_size=rdfvalue.RDFInteger,
                 pathspec=paths.RDFPathSpec,
                 registry_data=rdfvalue.DataBlob)


class RDFFindSpec(rdfvalue.RDFProto):
  """A find specification."""
  _proto = jobs_pb2.Find

  rdf_map = dict(pathspec=rdfvalue.RDFPathSpec,
                 hit=StatEntry,
                 iterator=Iterator)


class LogMessage(rdfvalue.RDFProto):
  """A log message sent from the client to the server."""
  _proto = jobs_pb2.PrintStr


class EchoRequest(rdfvalue.RDFProto):
  _proto = jobs_pb2.PrintStr


class ExecuteBinaryRequest(rdfvalue.RDFProto):
  _proto = jobs_pb2.ExecuteBinaryRequest

  rdf_map = dict(executable=crypto.SignedBlob)


class ExecuteBinaryResponse(rdfvalue.RDFProto):
  _proto = jobs_pb2.ExecuteBinaryResponse


class ExecutePythonRequest(rdfvalue.RDFProto):
  _proto = jobs_pb2.ExecutePythonRequest

  rdf_map = dict(python_code=crypto.SignedBlob,
                 py_args=rdfvalue.RDFProtoDict)


class ExecutePythonResponse(rdfvalue.RDFProto):
  _proto = jobs_pb2.ExecutePythonResponse


class ExecuteRequest(rdfvalue.RDFProto):
  _proto = jobs_pb2.ExecuteRequest


class ExecuteResponse(rdfvalue.RDFProto):
  _proto = jobs_pb2.ExecuteResponse


class Uname(rdfvalue.RDFProto):
  _proto = jobs_pb2.Uname


class StartupInfo(rdfvalue.RDFProto):
  _proto = jobs_pb2.StartupInfo

  rdf_map = dict(client_info=ClientInformation)


class SendFileRequest(rdfvalue.RDFProto):
  _proto = jobs_pb2.SendFileRequest

  rdf_map = dict(pathspec=rdfvalue.RDFPathSpec)


class ListDirRequest(rdfvalue.RDFProto):
  _proto = jobs_pb2.ListDirRequest

  rdf_map = dict(pathspec=rdfvalue.RDFPathSpec,
                 iterator=Iterator)


class FingerprintTuple(rdfvalue.RDFProto):
  _proto = jobs_pb2.FingerprintTuple


class FingerprintRequest(rdfvalue.RDFProto):
  _proto = jobs_pb2.FingerprintRequest

  rdf_map = dict(pathspec=rdfvalue.RDFPathSpec,
                 tuples=FingerprintTuple)

  def AddRequest(self, *args, **kw):
    self.tuples.Append(*args, **kw)


class FingerprintResponse(rdfvalue.RDFProto):
  """Proto containing dicts with hashes."""
  _proto = jobs_pb2.FingerprintResponse

  rdf_map = dict(fingerprint_results=rdfvalue.RDFProtoDict,
                 pathspec=rdfvalue.RDFPathSpec)

  # TODO(user): Add reasonable accessors for UI/console integration.
  # This includes parsing out the SignatureBlob for windows binaries.

  def Get(self, name):
    """Gets the first fingerprint type from the protobuf."""
    for result in self.fingerprint_results:
      if result.Get("name") == name:
        return result


class GrepSpec(rdfvalue.RDFProto):
  _proto = jobs_pb2.GrepRequest

  rdf_map = dict(target=rdfvalue.RDFPathSpec)


class WMIRequest(rdfvalue.RDFProto):
  _proto = jobs_pb2.WmiRequest


class LaunchdJob(rdfvalue.RDFProto):
  _proto = sysinfo_pb2.LaunchdJob


class Service(rdfvalue.RDFProto):
  """Structure of a running service."""
  _proto = sysinfo_pb2.Service

  rdf_map = dict(osx_launchd=LaunchdJob)


class Services(protodict.RDFValueArray):
  """Structure of a running service."""
  rdf_type = Service


class ClientResources(rdfvalue.RDFProto):
  """An RDFValue class representing the client resource usage."""
  _proto = jobs_pb2.ClientResources


# Start of the Registry Specific Data types
class RunKey(rdfvalue.RDFProto):
  _proto = sysinfo_pb2.RunKey


class RunKeyEntry(protodict.RDFValueArray):
  """Structure of a Run Key entry with keyname, filepath, and last written."""
  rdf_type = RunKey


class MRUFile(rdfvalue.RDFProto):
  _proto = sysinfo_pb2.MRUFile


class MRUFolder(protodict.RDFValueArray):
  """Structure describing Most Recently Used (MRU) files."""
  rdf_type = MRUFile


class Event(rdfvalue.RDFProto):
  _proto = analysis_pb2.Event

  rdf_type = dict(stat=StatEntry)


class AFF4ObjectSummary(rdfvalue.RDFProto):
  """A summary of an AFF4 object.

  AFF4Collection objects maintain a list of AFF4 objects. To make it easier to
  filter and search these collections, we need to store a summary of each AFF4
  object inside the collection (so we do not need to open every object for
  filtering).

  This summary is maintained in the RDFProto instance.
  """
  _proto = jobs_pb2.AFF4ObjectSummary

  rdf_map = dict(urn=rdfvalue.RDFURN,
                 stat=rdfvalue.StatEntry)


class ClientCrash(rdfvalue.RDFProto):
  """Details of a client crash."""
  _proto = jobs_pb2.ClientCrash

  rdf_map = dict(client_info=ClientInformation,
                 timestamp=rdfvalue.RDFDatetime)


class NoTargetGrepspecType(type_info.RDFValueType):
  """A Grep spec with no target."""

  child_descriptor = type_info.TypeDescriptorSet(
      type_info.String(
          description="Search for this regular expression.",
          name="regex",
          friendly_name="Regular Expression",
          default=""),
      type_info.Bytes(
          description="Search for this literal expression.",
          name="literal",
          friendly_name="Literal Match",
          default=""),
      type_info.Integer(
          description="Offset to start searching from.",
          name="start_offset",
          friendly_name="Start",
          default=0),
      type_info.Integer(
          description="Length to search.",
          name="length",
          friendly_name="Length",
          default=10737418240),
      type_info.RDFEnum(
          description="How many results should be returned?",
          name="mode",
          friendly_name="Search Mode",
          rdfclass=rdfvalue.GrepSpec,
          enum_name="Mode",
          default=rdfvalue.GrepSpec.Enum("FIRST_HIT")),
      type_info.Integer(
          description="Snippet returns these many bytes before the hit.",
          name="bytes_before",
          friendly_name="Preamble",
          default=0),
      type_info.Integer(
          description="Snippet returns these many bytes after the hit.",
          name="bytes_after",
          friendly_name="Context",
          default=0),
      )

  def __init__(self, **kwargs):
    defaults = dict(name="grepspec",
                    rdfclass=rdfvalue.GrepSpec)

    defaults.update(kwargs)
    super(NoTargetGrepspecType, self).__init__(**defaults)


class GrepspecType(NoTargetGrepspecType):
  """A Type for handling Grep specifications."""

  child_descriptor = (
      NoTargetGrepspecType.child_descriptor +
      type_info.TypeDescriptorSet(
          type_info.PathspecType(name="target")
          )
      )

  def Validate(self, value):
    if value.target.pathtype < 0:
      raise type_info.TypeValueError("GrepSpec has an invalid target PathSpec.")

    return super(GrepspecType, self).Validate(value)


class FindSpecType(type_info.RDFValueType):
  """A Find spec type."""

  child_descriptor = type_info.TypeDescriptorSet(
      type_info.PathspecType(),
      type_info.String(
          description="Search for this regular expression.",
          name="path_regex",
          friendly_name="Path Regular Expression",
          default=""),
      type_info.String(
          description="Search for this regular expression in the data.",
          name="data_regex",
          friendly_name="Data Regular Expression",
          default=""),
      type_info.Bool(
          description="Should we cross devices?",
          name="cross_devs",
          friendly_name="Cross Devices",
          default=False),
      type_info.Integer(
          description="Maximum recursion depth.",
          name="max_depth",
          friendly_name="Depth",
          default=5),
      )

  def __init__(self, **kwargs):
    defaults = dict(name="findspec",
                    rdfclass=rdfvalue.RDFFindSpec)

    defaults.update(kwargs)
    super(FindSpecType, self).__init__(**defaults)

  def Validate(self, value):
    """Validates the passed in protobuf for sanity."""
    value = super(FindSpecType, self).Validate(value)

    # Check the regexes are valid.
    try:
      if value.data_regex:
        re.compile(value.data_regex)

      if value.path_regex:
        re.compile(value.path_regex)
    except re.error, e:
      raise type_info.TypeValueError(
          "Invalid regex for FindFiles. Err: {0}".format(e))

    return value
