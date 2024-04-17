#!/usr/bin/env python
"""Stubs of client actions.

Client actions shouldn't be used on the server, stubs should be used instead.
This way we prevent loading effectively the whole client code into ours
server parts.
"""

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_core.lib.rdfvalues import cloud as rdf_cloud
from grr_response_core.lib.rdfvalues import dummy as rdf_dummy
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import large_file as rdf_large_file
from grr_response_core.lib.rdfvalues import memory as rdf_memory
from grr_response_core.lib.rdfvalues import osquery as rdf_osquery
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import read_low_level as rdf_read_low_level
from grr_response_core.lib.rdfvalues import timeline as rdf_timeline


class ClientActionStub:
  """Stub for a client action. To be used in server code."""

  in_rdfvalue = None
  out_rdfvalues = [None]


# from windows/windows.py, osx/osx.py and linux/linux.py
class GetInstallDate(ClientActionStub):
  """Estimate the install date of this system."""

  # DataBlob is deprecated but might still be sent by old clients.
  out_rdfvalues = [rdf_protodict.DataBlob, rdfvalue.RDFDatetime]


class EnumerateInterfaces(ClientActionStub):
  """Enumerate all MAC addresses of all NICs."""

  out_rdfvalues = [rdf_client_network.Interface]


class EnumerateFilesystems(ClientActionStub):
  """Enumerate all unique filesystems local to the system."""

  out_rdfvalues = [rdf_client_fs.Filesystem]


class UpdateAgent(ClientActionStub):
  """Updates the GRR agent to a new version."""

  in_rdfvalue = rdf_client_action.ExecuteBinaryRequest
  out_rdfvalues = [rdf_client_action.ExecuteBinaryResponse]


# Windows-specific
class WmiQuery(ClientActionStub):
  """Runs a WMI query and returns the results to a server callback."""

  in_rdfvalue = rdf_client_action.WMIRequest
  out_rdfvalues = [rdf_protodict.Dict]


class ListNamedPipes(ClientActionStub):
  """Lists named pipes available on the system."""

  in_rdfvalue = None
  out_rdfvalues = [rdf_client.NamedPipe]


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

  in_rdfvalue = rdf_client_action.EchoRequest
  out_rdfvalues = [rdf_client_action.EchoRequest]


class GetHostname(ClientActionStub):
  """Retrieves the host name of the client."""

  out_rdfvalues = [rdf_protodict.DataBlob]


class GetPlatformInfo(ClientActionStub):
  """Retrieves platform information."""

  out_rdfvalues = [rdf_client.Uname]


class Kill(ClientActionStub):
  """A client action for terminating (ClientActionStub) the client."""

  out_rdfvalues = [rdf_flows.GrrMessage]


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


class SendStartupInfo(ClientActionStub):

  out_rdfvalues = [rdf_client.StartupInfo]


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

  in_rdfvalue = rdf_client_action.FingerprintRequest
  out_rdfvalues = [rdf_client_action.FingerprintResponse]


class ListDirectory(ClientActionStub):
  """Lists all the files in a directory."""

  in_rdfvalue = rdf_client_action.ListDirRequest
  out_rdfvalues = [rdf_client_fs.StatEntry]


class GetFileStat(ClientActionStub):
  """A client action that yields stat of a given file."""

  in_rdfvalue = rdf_client_action.GetFileStatRequest
  out_rdfvalues = [rdf_client_fs.StatEntry]


class ExecuteCommand(ClientActionStub):
  """Executes one of the predefined commands."""

  in_rdfvalue = rdf_client_action.ExecuteRequest
  out_rdfvalues = [rdf_client_action.ExecuteResponse]


class ExecuteBinaryCommand(ClientActionStub):
  """Executes a command from a passed in binary."""

  in_rdfvalue = rdf_client_action.ExecuteBinaryRequest
  out_rdfvalues = [rdf_client_action.ExecuteBinaryResponse]


class ExecutePython(ClientActionStub):
  """Executes python code with exec."""

  in_rdfvalue = rdf_client_action.ExecutePythonRequest
  out_rdfvalues = [rdf_client_action.ExecutePythonResponse]


class Segfault(ClientActionStub):
  """This action is just for debugging. It induces a segfault."""

  in_rdfvalue = None
  out_rdfvalues = [None]


class ListProcesses(ClientActionStub):
  """This action lists all the processes running on a machine."""

  in_rdfvalue = None
  out_rdfvalues = [rdf_client.Process]


class StatFS(ClientActionStub):
  """Call os.statvfs for a given list of paths. OS X and Linux only."""

  in_rdfvalue = rdf_client_action.StatFSRequest
  out_rdfvalues = [rdf_client_fs.Volume]


class GetMemorySize(ClientActionStub):

  out_rdfvalues = [rdfvalue.ByteSize]


# from tempfiles.py
class DeleteGRRTempFiles(ClientActionStub):
  """Delete all the GRR temp files in a directory."""

  in_rdfvalue = rdf_paths.PathSpec
  out_rdfvalues = [rdf_client.LogMessage]


class CheckFreeGRRTempSpace(ClientActionStub):

  in_rdfvalue = rdf_paths.PathSpec
  out_rdfvalues = [rdf_client_fs.DiskUsage]


# from searching.py
class Find(ClientActionStub):
  """Recurses through a directory returning files which match conditions."""

  in_rdfvalue = rdf_client_fs.FindSpec
  out_rdfvalues = [rdf_client_fs.FindSpec, rdf_client_fs.StatEntry]


class Grep(ClientActionStub):
  """Search a file for a pattern."""

  in_rdfvalue = rdf_client_fs.GrepSpec
  out_rdfvalues = [rdf_client.BufferReference]


class ListNetworkConnections(ClientActionStub):
  """Gather open network connection stats."""

  in_rdfvalue = rdf_client_action.ListNetworkConnectionsArgs
  out_rdfvalues = [rdf_client_network.NetworkConnection]


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


# from file_finder.py
class VfsFileFinder(ClientActionStub):
  """The client file finder implementation using the VFS file api."""

  in_rdfvalue = rdf_file_finder.FileFinderArgs
  out_rdfvalues = [rdf_file_finder.FileFinderResult]


# from file_fingerprint.py
class FingerprintFile(ClientActionStub):
  """Apply a set of fingerprinting methods to a file."""

  in_rdfvalue = rdf_client_action.FingerprintRequest
  out_rdfvalues = [rdf_client_action.FingerprintResponse]


# from memory.py
class YaraProcessScan(ClientActionStub):
  """Scans the memory of a number of processes using Yara."""

  in_rdfvalue = rdf_memory.YaraProcessScanRequest
  out_rdfvalues = [rdf_memory.YaraProcessScanResponse]


class YaraProcessDump(ClientActionStub):
  """Dumps a process to disk and returns pathspecs for GRR to pick up."""

  in_rdfvalue = rdf_memory.YaraProcessDumpArgs
  out_rdfvalues = [rdf_memory.YaraProcessDumpResponse]


class CollectLargeFile(ClientActionStub):
  """A stub class for the large file collection action."""

  in_rdfvalue = rdf_large_file.CollectLargeFileArgs
  out_rdfvalues = [rdf_large_file.CollectLargeFileResult]


class Osquery(ClientActionStub):
  """A stub class for the osquery action plugin."""

  in_rdfvalue = rdf_osquery.OsqueryArgs
  out_rdfvalues = [rdf_osquery.OsqueryResult]


class Timeline(ClientActionStub):
  """A stub class for the timeline client action."""

  in_rdfvalue = rdf_timeline.TimelineArgs
  out_rdfvalues = [rdf_timeline.TimelineResult]


class ReadLowLevel(ClientActionStub):
  """Reads `length` bytes from `path` starting at `offset` and returns it."""

  in_rdfvalue = rdf_read_low_level.ReadLowLevelRequest
  out_rdfvalues = [rdf_read_low_level.ReadLowLevelResult]


class Dummy(ClientActionStub):
  """Dummy example. Reads a message and sends it back."""

  in_rdfvalue = rdf_dummy.DummyRequest
  out_rdfvalues = [rdf_dummy.DummyResult]
