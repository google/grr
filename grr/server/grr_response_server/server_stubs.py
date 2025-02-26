#!/usr/bin/env python
"""Stubs of client actions.

Client actions shouldn't be used on the server, stubs should be used instead.
This way we prevent loading effectively the whole client code into ours
server parts.
"""

from typing import Optional, Type

from google.protobuf import message as pb_message
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_core.lib.rdfvalues import cloud as rdf_cloud
from grr_response_core.lib.rdfvalues import containers as rdf_containers
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
from grr_response_proto import containers_pb2
from grr_response_proto import dummy_pb2
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import large_file_pb2
from grr_response_proto import osquery_pb2
from grr_response_proto import read_low_level_pb2
from grr_response_proto import timeline_pb2
# pylint: disable=g-bad-import-order
# pylint: enable=g-bad-import-order


class ClientActionStub:
  """Stub for a client action. To be used in server code."""

  in_rdfvalue = None
  in_proto: Optional[Type[pb_message.Message]] = None
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
  in_proto = jobs_pb2.ExecuteBinaryRequest
  out_rdfvalues = [rdf_client_action.ExecuteBinaryResponse]


# Windows-specific
class WmiQuery(ClientActionStub):
  """Runs a WMI query and returns the results to a server callback."""

  in_rdfvalue = rdf_client_action.WMIRequest
  in_proto = jobs_pb2.WMIRequest
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
  in_proto = jobs_pb2.EchoRequest
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


class GetClientInfo(ClientActionStub):
  """Obtains information about the GRR client installed."""

  out_rdfvalues = [rdf_client.ClientInformation]


class SendStartupInfo(ClientActionStub):

  out_rdfvalues = [rdf_client.StartupInfo]


# from standard.py
class ReadBuffer(ClientActionStub):
  """Reads a buffer from a file and returns it to a server callback."""

  in_rdfvalue = rdf_client.BufferReference
  in_proto = jobs_pb2.BufferReference
  out_rdfvalues = [rdf_client.BufferReference]


class TransferBuffer(ClientActionStub):
  """Reads a buffer from a file and returns it to the server efficiently."""

  in_rdfvalue = rdf_client.BufferReference
  in_proto = jobs_pb2.BufferReference
  out_rdfvalues = [rdf_client.BufferReference]


class HashBuffer(ClientActionStub):
  """Hash a buffer from a file and returns it to the server efficiently."""

  in_rdfvalue = rdf_client.BufferReference
  in_proto = jobs_pb2.BufferReference
  out_rdfvalues = [rdf_client.BufferReference]


class HashFile(ClientActionStub):
  """Hash an entire file using multiple algorithms."""

  in_rdfvalue = rdf_client_action.FingerprintRequest
  in_proto = jobs_pb2.FingerprintRequest
  out_rdfvalues = [rdf_client_action.FingerprintResponse]


class ListDirectory(ClientActionStub):
  """Lists all the files in a directory."""

  in_rdfvalue = rdf_client_action.ListDirRequest
  in_proto = jobs_pb2.ListDirRequest
  out_rdfvalues = [rdf_client_fs.StatEntry]


class GetFileStat(ClientActionStub):
  """A client action that yields stat of a given file."""

  in_rdfvalue = rdf_client_action.GetFileStatRequest
  in_proto = jobs_pb2.GetFileStatRequest
  out_rdfvalues = [rdf_client_fs.StatEntry]


class ExecuteCommand(ClientActionStub):
  """Executes one of the predefined commands."""

  in_rdfvalue = rdf_client_action.ExecuteRequest
  in_proto = jobs_pb2.ExecuteRequest
  out_rdfvalues = [rdf_client_action.ExecuteResponse]


class ExecuteBinaryCommand(ClientActionStub):
  """Executes a command from a passed in binary."""

  in_rdfvalue = rdf_client_action.ExecuteBinaryRequest
  in_proto = jobs_pb2.ExecuteBinaryRequest
  out_rdfvalues = [rdf_client_action.ExecuteBinaryResponse]


class ExecutePython(ClientActionStub):
  """Executes python code with exec."""

  in_rdfvalue = rdf_client_action.ExecutePythonRequest
  in_proto = jobs_pb2.ExecutePythonRequest
  out_rdfvalues = [rdf_client_action.ExecutePythonResponse]


class ListProcesses(ClientActionStub):
  """This action lists all the processes running on a machine."""

  in_rdfvalue = None
  out_rdfvalues = [rdf_client.Process]


class StatFS(ClientActionStub):
  """Call os.statvfs for a given list of paths. OS X and Linux only."""

  in_rdfvalue = rdf_client_action.StatFSRequest
  in_proto = jobs_pb2.StatFSRequest
  out_rdfvalues = [rdf_client_fs.Volume]


class GetMemorySize(ClientActionStub):

  out_rdfvalues = [rdfvalue.ByteSize]


# from tempfiles.py
class DeleteGRRTempFiles(ClientActionStub):
  """Delete all the GRR temp files in a directory."""

  in_rdfvalue = rdf_paths.PathSpec
  in_proto = jobs_pb2.PathSpec
  out_rdfvalues = [rdf_client.LogMessage]


class CheckFreeGRRTempSpace(ClientActionStub):

  in_rdfvalue = rdf_paths.PathSpec
  in_proto = jobs_pb2.PathSpec
  out_rdfvalues = [rdf_client_fs.DiskUsage]


# from searching.py
class Find(ClientActionStub):
  """Recurses through a directory returning files which match conditions."""

  in_rdfvalue = rdf_client_fs.FindSpec
  in_proto = jobs_pb2.FindSpec
  out_rdfvalues = [rdf_client_fs.FindSpec, rdf_client_fs.StatEntry]


class Grep(ClientActionStub):
  """Search a file for a pattern."""

  in_rdfvalue = rdf_client_fs.GrepSpec
  in_proto = jobs_pb2.GrepSpec
  out_rdfvalues = [rdf_client.BufferReference]


class ListNetworkConnections(ClientActionStub):
  """Gather open network connection stats."""

  in_rdfvalue = rdf_client_action.ListNetworkConnectionsArgs
  in_proto = flows_pb2.ListNetworkConnectionsArgs
  out_rdfvalues = [rdf_client_network.NetworkConnection]


# from cloud.py
class GetCloudVMMetadata(ClientActionStub):
  """Get metadata for cloud VMs."""

  in_rdfvalue = rdf_cloud.CloudMetadataRequests
  in_proto = flows_pb2.CloudMetadataRequests
  out_rdfvalues = [rdf_cloud.CloudMetadataResponses]


# from file_finder.py
class FileFinderOS(ClientActionStub):
  """The file finder implementation using the OS file api."""

  in_rdfvalue = rdf_file_finder.FileFinderArgs
  in_proto = flows_pb2.FileFinderArgs
  out_rdfvalues = [rdf_file_finder.FileFinderResult]


# from file_finder.py
class VfsFileFinder(ClientActionStub):
  """The client file finder implementation using the VFS file api."""

  in_rdfvalue = rdf_file_finder.FileFinderArgs
  in_proto = flows_pb2.FileFinderArgs
  out_rdfvalues = [rdf_file_finder.FileFinderResult]


# from file_fingerprint.py
class FingerprintFile(ClientActionStub):
  """Apply a set of fingerprinting methods to a file."""

  in_rdfvalue = rdf_client_action.FingerprintRequest
  in_proto = jobs_pb2.FingerprintRequest
  out_rdfvalues = [rdf_client_action.FingerprintResponse]


# from memory.py
class YaraProcessScan(ClientActionStub):
  """Scans the memory of a number of processes using Yara."""

  in_rdfvalue = rdf_memory.YaraProcessScanRequest
  in_proto = flows_pb2.YaraProcessScanRequest
  out_rdfvalues = [rdf_memory.YaraProcessScanResponse]


class YaraProcessDump(ClientActionStub):
  """Dumps a process to disk and returns pathspecs for GRR to pick up."""

  in_rdfvalue = rdf_memory.YaraProcessDumpArgs
  in_proto = flows_pb2.YaraProcessDumpArgs
  out_rdfvalues = [rdf_memory.YaraProcessDumpResponse]


class CollectLargeFile(ClientActionStub):
  """A stub class for the large file collection action."""

  in_rdfvalue = rdf_large_file.CollectLargeFileArgs
  in_proto = large_file_pb2.CollectLargeFileArgs
  out_rdfvalues = [rdf_large_file.CollectLargeFileResult]


class Osquery(ClientActionStub):
  """A stub class for the osquery action plugin."""

  in_rdfvalue = rdf_osquery.OsqueryArgs
  in_proto = osquery_pb2.OsqueryArgs
  out_rdfvalues = [rdf_osquery.OsqueryResult]


class Timeline(ClientActionStub):
  """A stub class for the timeline client action."""

  in_rdfvalue = rdf_timeline.TimelineArgs
  in_proto = timeline_pb2.TimelineArgs
  out_rdfvalues = [rdf_timeline.TimelineResult]


class ReadLowLevel(ClientActionStub):
  """Reads `length` bytes from `path` starting at `offset` and returns it."""

  in_rdfvalue = rdf_read_low_level.ReadLowLevelRequest
  in_proto = read_low_level_pb2.ReadLowLevelRequest
  out_rdfvalues = [rdf_read_low_level.ReadLowLevelResult]


class ListContainers(ClientActionStub):
  """Lists containers running on the client."""

  in_rdfvalue = rdf_containers.ListContainersRequest
  in_proto = containers_pb2.ListContainersRequest
  out_rdfvalues = [rdf_containers.ListContainersResult]


class Dummy(ClientActionStub):
  """Dummy example. Reads a message and sends it back."""

  in_rdfvalue = rdf_dummy.DummyRequest
  in_proto = dummy_pb2.DummyRequest
  out_rdfvalues = [rdf_dummy.DummyResult]
