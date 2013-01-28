#!/usr/bin/env python
# Copyright 2012 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""AFF4 RDFValue implementations for client information.

This module contains the RDFValue implementations used to communicate with the
client.
"""

import hashlib

from M2Crypto import BIO
from M2Crypto import RSA
from M2Crypto import util
from M2Crypto import X509

import logging

from grr.lib import rdfvalue
from grr.lib.rdfvalues import paths
from grr.lib.rdfvalues import protodict
from grr.proto import analysis_pb2
from grr.proto import jobs_pb2
from grr.proto import sysinfo_pb2

DIGEST_ALGORITHM = hashlib.sha256
DIGEST_ALGORITHM_STR = "sha256"


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


class Interface(rdfvalue.RDFProto):
  """A network interface on the client system."""
  _proto = jobs_pb2.Interface

  rdf_map = dict(addresses=NetworkAddress)


class Interfaces(protodict.RDFValueArray):
  """The list of interfaces on a host."""
  rdf_type = Interface


class GRRConfig(rdfvalue.RDFProto):
  """The configuration of a GRR Client."""
  _proto = jobs_pb2.GRRConfig


class Certificate(rdfvalue.RDFProto):
  _proto = jobs_pb2.Certificate


class RDFX509Cert(rdfvalue.RDFString):
  """X509 certificates used to communicate with this client."""

  def _GetCN(self, x509cert):
    subject = x509cert.get_subject()
    try:
      cn_id = subject.nid["CN"]
      cn = subject.get_entries_by_nid(cn_id)[0]
    except IndexError:
      raise IOError("Cert has no CN")

    self.common_name = cn.get_data().as_text()

  def GetX509Cert(self):
    return X509.load_cert_string(str(self))

  def GetPubKey(self):
    return self.GetX509Cert().get_pubkey().get_rsa()

  def ParseFromString(self, string):
    super(RDFX509Cert, self).ParseFromString(string)
    try:
      self._GetCN(self.GetX509Cert())
    except X509.X509Error:
      raise IOError("Cert invalid")


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


class SignedBlob(rdfvalue.RDFProto):
  """A signed blob.

  The client can receive and verify a signed blob (e.g. driver or executable
  binary). Once verified, the client may execute this.
  """
  _proto = jobs_pb2.SignedBlob

  def Verify(self, pub_key):
    """Verify the data in this blob.

    Args:
      pub_key: The public key to use for verification.

    Returns:
      True if the data is verified, else False.
    """
    if self.digest_type != self.SHA256:
      logging.warn("Unsupported digest.")
      return False

    bio = BIO.MemoryBuffer(pub_key)
    rsa = RSA.load_pub_key_bio(bio)
    result = 0
    try:
      result = rsa.verify(self.digest, self.signature,
                          DIGEST_ALGORITHM_STR)
      if result != 1:
        logging.warn("Could not verify blob.")
        return False

    except RSA.RSAError, e:
      logging.warn("Could not verify blob. Error: %s", e)
      return False

    digest = hashlib.sha256(self._data.data).digest()
    if digest != self.digest:
      logging.warn("SignedBlob: Digest did not match actual data.")
      return False

    return result == 1

  def Sign(self, data, signing_key, verify_key=None, prompt=False):
    """Use the data to sign this blob.

    Args:
      data: String containing the blob data.
      signing_key: A key that can be loaded to sign the data as a string.
      verify_key: Key to verify with. If None we assume the signing key also
        contains the public key.
      prompt: If True we allow a password prompt to be presented.

    Raises:
      IOError: On bad key.
    """
    callback = None
    if prompt:
      callback = util.passphrase_callback
    else:
      callback = lambda x: ""

    digest = DIGEST_ALGORITHM(data).digest()
    rsa = RSA.load_key_string(signing_key, callback=callback)
    if len(rsa) < 2048:
      logging.warn("signing key is too short.")

    sig = rsa.sign(digest, DIGEST_ALGORITHM_STR)
    self.signature = sig
    self.signature_type = self.RSA_2048

    self.digest = digest
    self.digest_type = self.SHA256
    self._data.data = data

    # Test we can verify before we send it off.
    if verify_key is None:
      m = BIO.MemoryBuffer()
      rsa.save_pub_key_bio(m)
      verify_key = m.read_all()
    if not self.Verify(verify_key):
      raise IOError("Failed to verify our own signed blob")


class DriverInstallTemplate(rdfvalue.RDFProto):
  """Driver specific information controlling default installation.

  This is sent to the client to instruct the client how to install this driver.
  """
  _proto = jobs_pb2.InstallDriverRequest

  rdf_map = dict(driver=SignedBlob)


class BufferReference(rdfvalue.RDFProto):
  """Stores information about a buffer in a file on the client."""
  _proto = jobs_pb2.BufferReadMessage

  def __eq__(self, other):
    return self._data.data == other

  rdf_map = dict(pathspec=rdfvalue.RDFPathSpec)


class Process(rdfvalue.RDFProto):
  """Represent a process on the client."""
  _proto = sysinfo_pb2.Process


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


class ExecuteBinaryResponse(rdfvalue.RDFProto):
  _proto = jobs_pb2.ExecuteBinaryResponse


class ExecutePythonRequest(rdfvalue.RDFProto):
  _proto = jobs_pb2.ExecutePythonRequest

  rdf_map = dict(python_code=SignedBlob,
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

  rdf_map = dict(fingerprint_results=rdfvalue.RDFProtoDict)

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
