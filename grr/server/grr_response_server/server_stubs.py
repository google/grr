#!/usr/bin/env python
"""Stubs of client actions.

Client actions shouldn't be used on the server, stubs should be used instead.
This way we prevent loading effectively the whole client code into ours
server parts.
"""

from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib.rdfvalues import chipsec_types
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import cloud as rdf_cloud
from grr.lib.rdfvalues import file_finder as rdf_file_finder
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import plist as rdf_plist
from grr.lib.rdfvalues import protodict as rdf_protodict
from grr.lib.rdfvalues import rdf_yara
from grr.lib.rdfvalues import rekall_types as rdf_rekall_types


class ClientActionStub(object):
  """Stub for a client action. To be used in server code."""

  __metaclass__ = registry.MetaclassRegistry

  in_rdfvalue = None
  out_rdfvalues = [None]


# from windows/windows.py, osx/osx.py and linux/linux.py
class GetInstallDate(ClientActionStub):
  """Estimate the install date of this system."""

  # DataBlob is deprecated but might still be sent by old clients.
  out_rdfvalues = [rdf_protodict.DataBlob, rdfvalue.RDFDatetime]


class EnumerateInterfaces(ClientActionStub):
  """Enumerate all MAC addresses of all NICs."""

  out_rdfvalues = [rdf_client.Interface]


class EnumerateFilesystems(ClientActionStub):
  """Enumerate all unique filesystems local to the system."""

  out_rdfvalues = [rdf_client.Filesystem]


class Uninstall(ClientActionStub):
  """Remove the service that starts us at startup."""

  out_rdfvalues = [rdf_protodict.DataBlob]


class UpdateAgent(ClientActionStub):
  """Updates the GRR agent to a new version."""

  in_rdfvalue = rdf_client.ExecuteBinaryRequest
  out_rdfvalues = [rdf_client.ExecuteBinaryResponse]


# Windows-specific
class WmiQuery(ClientActionStub):
  """Runs a WMI query and returns the results to a server callback."""

  in_rdfvalue = rdf_client.WMIRequest
  out_rdfvalues = [rdf_protodict.Dict]


# OS X-specific
class OSXEnumerateRunningServices(ClientActionStub):
  """Enumerate all running launchd jobs."""

  in_rdfvalue = None
  out_rdfvalues = [rdf_client.OSXServiceInformation]


# Linux-specific
class EnumerateRunningServices(ClientActionStub):
  """List running daemons."""
  in_rdfvalue = None
  out_rdfvalues = [None]


class EnumerateUsers(ClientActionStub):
  """Enumerates all the users on this system."""

  # Client versions 3.0.7.1 and older used to return KnowledgeBaseUser.
  # KnowledgeBaseUser was renamed to User.
  out_rdfvalues = [rdf_client.User, rdf_client.KnowledgeBaseUser]


# from admin.py
class Echo(ClientActionStub):
  """Returns a message to the server."""

  in_rdfvalue = rdf_client.EchoRequest
  out_rdfvalues = [rdf_client.LogMessage]


class GetHostname(ClientActionStub):
  """Retrieves the host name of the client."""

  out_rdfvalues = [rdf_protodict.DataBlob]


class GetPlatformInfo(ClientActionStub):
  """Retrieves platform information."""

  out_rdfvalues = [rdf_client.Uname]


class Kill(ClientActionStub):
  """A client action for terminating (ClientActionStub) the client."""

  out_rdfvalues = [rdf_flows.GrrMessage]


class Hang(ClientActionStub):
  """A client action for simulating the client becoming unresponsive."""

  in_rdfvalue = rdf_protodict.DataBlob


class BusyHang(ClientActionStub):
  """A client action that burns cpu cycles. Used for testing cpu limits."""

  in_rdfvalue = rdf_protodict.DataBlob


class Bloat(ClientActionStub):
  """A client action that uses lots of memory for testing."""

  in_rdfvalue = rdf_protodict.DataBlob


class GetConfiguration(ClientActionStub):
  """Retrieves the running configuration parameters."""

  in_rdfvalue = None
  out_rdfvalues = [rdf_protodict.Dict]


class GetLibraryVersions(ClientActionStub):
  """Retrieves version information for installed libraries."""

  in_rdfvalue = None
  out_rdfvalues = [rdf_protodict.Dict]


class UpdateConfiguration(ClientActionStub):
  """Updates configuration parameters on the client."""

  in_rdfvalue = rdf_protodict.Dict


class GetClientInfo(ClientActionStub):
  """Obtains information about the GRR client installed."""

  out_rdfvalues = [rdf_client.ClientInformation]


class GetClientStats(ClientActionStub):
  """This retrieves some stats about the GRR process."""

  in_rdfvalue = rdf_client.GetClientStatsRequest
  out_rdfvalues = [rdf_client.ClientStats]


class GetClientStatsAuto(GetClientStats):
  """Action used to send the reply to a well known flow on the server."""


class SendStartupInfo(ClientActionStub):

  out_rdfvalues = [rdf_client.StartupInfo]


# from enrol.py
class SaveCert(ClientActionStub):
  """Accepts a signed certificate from the server and saves it to disk."""


# from plist.py
class PlistQuery(ClientActionStub):
  """Parses the plist request specified and returns the results."""

  in_rdfvalue = rdf_plist.PlistRequest
  out_rdfvalues = [rdf_protodict.RDFValueArray]


# from standard.py
class ReadBuffer(ClientActionStub):
  """Reads a buffer from a file and returns it to a server callback."""

  in_rdfvalue = rdf_client.BufferReference
  out_rdfvalues = [rdf_client.BufferReference]


class TransferBuffer(ClientActionStub):
  """Reads a buffer from a file and returns it to the server efficiently."""

  in_rdfvalue = rdf_client.BufferReference
  out_rdfvalues = [rdf_client.BufferReference]


class HashBuffer(ClientActionStub):
  """Hash a buffer from a file and returns it to the server efficiently."""

  in_rdfvalue = rdf_client.BufferReference
  out_rdfvalues = [rdf_client.BufferReference]


class HashFile(ClientActionStub):
  """Hash an entire file using multiple algorithms."""

  in_rdfvalue = rdf_client.FingerprintRequest
  out_rdfvalues = [rdf_client.FingerprintResponse]


class CopyPathToFile(ClientActionStub):
  """Copy contents of a pathspec to a file on disk."""

  in_rdfvalue = rdf_client.CopyPathToFileRequest
  out_rdfvalues = [rdf_client.CopyPathToFileRequest]


class ListDirectory(ClientActionStub):
  """Lists all the files in a directory."""

  in_rdfvalue = rdf_client.ListDirRequest
  out_rdfvalues = [rdf_client.StatEntry]


class IteratedListDirectory(ClientActionStub):
  """Lists a directory as an iterator."""

  in_rdfvalue = rdf_client.ListDirRequest
  out_rdfvalues = [rdf_client.StatEntry]


# DEPRECATED.
#
# This action was replaced by newer `GetFileStat` action. This stub is left for
# compatibility with old clients. After the transition period all clients should
# support new action and this class should be removed.
#
# TODO(hanuszczak): Remove this class after 2021-01-01.
class StatFile(ClientActionStub):
  """Sends a StatEntry for a single file."""

  in_rdfvalue = rdf_client.ListDirRequest
  out_rdfvalues = [rdf_client.StatEntry]


class GetFileStat(ClientActionStub):
  """A client action that yields stat of a given file."""

  in_rdfvalue = rdf_client.GetFileStatRequest
  out_rdfvalues = [rdf_client.StatEntry]


class ExecuteCommand(ClientActionStub):
  """Executes one of the predefined commands."""

  in_rdfvalue = rdf_client.ExecuteRequest
  out_rdfvalues = [rdf_client.ExecuteResponse]


class ExecuteBinaryCommand(ClientActionStub):
  """Executes a command from a passed in binary."""

  in_rdfvalue = rdf_client.ExecuteBinaryRequest
  out_rdfvalues = [rdf_client.ExecuteBinaryResponse]


class ExecutePython(ClientActionStub):
  """Executes python code with exec."""

  in_rdfvalue = rdf_client.ExecutePythonRequest
  out_rdfvalues = [rdf_client.ExecutePythonResponse]


class Segfault(ClientActionStub):
  """This action is just for debugging. It induces a segfault."""

  in_rdfvalue = None
  out_rdfvalues = [None]


class ListProcesses(ClientActionStub):
  """This action lists all the processes running on a machine."""

  in_rdfvalue = None
  out_rdfvalues = [rdf_client.Process]


class SendFile(ClientActionStub):
  """This action encrypts and sends a file to a remote listener."""

  in_rdfvalue = rdf_client.SendFileRequest
  out_rdfvalues = [rdf_client.StatEntry]


class StatFS(ClientActionStub):
  """Call os.statvfs for a given list of paths. OS X and Linux only."""

  in_rdfvalue = rdf_client.StatFSRequest
  out_rdfvalues = [rdf_client.Volume]


class GetMemorySize(ClientActionStub):

  out_rdfvalues = [rdfvalue.ByteSize]


# from tempfiles.py
class DeleteGRRTempFiles(ClientActionStub):
  """Delete all the GRR temp files in a directory."""

  in_rdfvalue = rdf_paths.PathSpec
  out_rdfvalues = [rdf_client.LogMessage]


class CheckFreeGRRTempSpace(ClientActionStub):

  in_rdfvalue = rdf_paths.PathSpec
  out_rdfvalues = [rdf_client.DiskUsage]


# from searching.py
class Find(ClientActionStub):
  """Recurses through a directory returning files which match conditions."""

  in_rdfvalue = rdf_client.FindSpec
  out_rdfvalues = [rdf_client.FindSpec]


class Grep(ClientActionStub):
  """Search a file for a pattern."""

  in_rdfvalue = rdf_client.GrepSpec
  out_rdfvalues = [rdf_client.BufferReference]


# from network.py
# Deprecated action, kept for outdated clients.
class Netstat(ClientActionStub):
  """Gather open network connection stats."""

  in_rdfvalue = None
  out_rdfvalues = [rdf_client.NetworkConnection]


class ListNetworkConnections(ClientActionStub):
  """Gather open network connection stats."""

  in_rdfvalue = rdf_client.ListNetworkConnectionsArgs
  out_rdfvalues = [rdf_client.NetworkConnection]


# from cloud.py
class GetCloudVMMetadata(ClientActionStub):
  """Get metadata for cloud VMs."""

  in_rdfvalue = rdf_cloud.CloudMetadataRequests
  out_rdfvalues = [rdf_cloud.CloudMetadataResponses]


# from file_finder.py
class FileFinderOS(ClientActionStub):
  """The file finder implementation using the OS file api."""

  in_rdfvalue = rdf_file_finder.FileFinderArgs
  out_rdfvalues = [rdf_file_finder.FileFinderResult]


# from file_fingerprint.py
class FingerprintFile(ClientActionStub):
  """Apply a set of fingerprinting methods to a file."""

  in_rdfvalue = rdf_client.FingerprintRequest
  out_rdfvalues = [rdf_client.FingerprintResponse]


# from components/chipsec_support
class DumpFlashImage(ClientActionStub):
  """A client action to collect the BIOS via SPI using Chipsec."""

  in_rdfvalue = chipsec_types.DumpFlashImageRequest
  out_rdfvalues = [chipsec_types.DumpFlashImageResponse]


class DumpACPITable(ClientActionStub):
  """A client action to collect the ACPI table(s)."""

  in_rdfvalue = chipsec_types.DumpACPITableRequest
  out_rdfvalues = [chipsec_types.DumpACPITableResponse]


# from components/rekall_support
class WriteRekallProfile(ClientActionStub):
  """A client action to write a Rekall profile to the local cache."""

  in_rdfvalue = rdf_rekall_types.RekallProfile


class RekallAction(ClientActionStub):
  """Runs a Rekall command on live memory."""

  in_rdfvalue = rdf_rekall_types.RekallRequest
  out_rdfvalues = [rdf_rekall_types.RekallResponse]


# from yara_actions.py
class YaraProcessScan(ClientActionStub):
  """Scans the memory of a number of processes using Yara."""

  in_rdfvalue = rdf_yara.YaraProcessScanRequest
  out_rdfvalues = [rdf_yara.YaraProcessScanResponse]


class YaraProcessDump(ClientActionStub):
  """Dumps a process to disk and returns pathspecs for GRR to pick up."""

  in_rdfvalue = rdf_yara.YaraProcessDumpArgs
  out_rdfvalues = [rdf_yara.YaraProcessDumpResponse]


# Rekall constants as defined in rekall/constants.py.
REKALL_PROFILE_REPOSITORY_VERSION = "v1.0"
