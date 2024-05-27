#!/usr/bin/env python
"""Flows for collecting Linux distribution information."""

import itertools
import re

from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import mig_file_finder
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import distro_pb2
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_server import data_store
from grr_response_server import file_store
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import server_stubs
from grr_response_server.models import blobs


class CollectDistroInfoResult(rdf_structs.RDFProtoStruct):
  """RDF wrapper for the `CollectDistroInfoResult` message."""

  protobuf = distro_pb2.CollectDistroInfoResult
  rdf_deps = []


class CollectDistroInfo(flow_base.FlowBase):
  """Flow that collects information about the endpoint Linux distribution."""

  category = "/Collectors/"
  behaviours = flow_base.BEHAVIOUR_DEBUG

  result_types = [CollectDistroInfoResult]

  def Start(self) -> None:
    if self.client_os != "Linux":
      raise flow_base.FlowError(f"Unsupported system: {self.client_os}")

    ff_args = flows_pb2.FileFinderArgs()
    ff_args.action.action_type = flows_pb2.FileFinderAction.Action.DOWNLOAD
    ff_args.pathtype = jobs_pb2.PathSpec.PathType.OS
    ff_args.paths.extend([
        # Non-LSB compliant systems.
        "/etc/centos-release",
        "/etc/enterprise-release",
        "/etc/oracle-release",
        "/etc/redhat-release",
        "/etc/rocky-release",
        "/etc/SuSE-release",
        "/etc/system-release",
        # LSB compliant systems.
        "/etc/lsb-release",
        # systemd-enabled systems.
        "/etc/os-release",
        "/usr/lib/os-release",
    ])

    self.CallClient(
        server_stubs.FileFinderOS,
        mig_file_finder.ToRDFFileFinderArgs(ff_args),
        next_state=self._ProcessRelease.__name__,
    )

  def _ProcessRelease(
      self,
      responses: flow_responses.Responses[rdf_file_finder.FileFinderResult],
  ) -> None:
    if not responses.success:
      raise flow_base.FlowError(
          f"Failed to collect release files: {responses.status}",
      )

    blob_ids_by_path: dict[str, set[blobs.BlobID]] = dict()

    for response in responses:
      path = response.stat_entry.pathspec.path

      for chunk in response.transferred_file.chunks:
        path_blob_ids = blob_ids_by_path.setdefault(path, set())
        path_blob_ids.add(blobs.BlobID(chunk.digest))

    blobs_by_blob_id = data_store.BLOBS.ReadAndWaitForBlobs(
        set(itertools.chain.from_iterable(blob_ids_by_path.values())),
        timeout=file_store.BLOBS_READ_TIMEOUT,
    )

    blobs_by_path: dict[str, bytes] = {
        path: b"".join(blobs_by_blob_id[blob_id] for blob_id in blob_ids)
        for path, blob_ids in blob_ids_by_path.items()
    }

    contents_by_path: dict[str, str] = {
        path: blob.decode("utf-8") for path, blob in blobs_by_path.items()
    }

    result = distro_pb2.CollectDistroInfoResult()

    if lsb_release := contents_by_path.get("/etc/lsb-release"):
      _ParseLSBRelease(lsb_release, result)

    if system_release := contents_by_path.get("/etc/system-release"):
      if not result.release:
        result.release = system_release.strip()

    if oracle_release := contents_by_path.get("/etc/oracle-release"):
      if not result.name:
        result.name = "OracleLinux"

      _ParseRedHatRelease(oracle_release, result)

    if oel_release := contents_by_path.get("/etc/enterprise-release"):
      if not result.name:
        result.name = "OEL"

      _ParseRedHatRelease(oel_release, result)

    if rocky_release := contents_by_path.get("/etc/rocky-release"):
      if not result.name:
        result.name = "Rocky"

      _ParseRedHatRelease(rocky_release, result)

    if redhat_release := contents_by_path.get("/etc/redhat-release"):
      if not result.name:
        result.name = "RedHat"

      _ParseRedHatRelease(redhat_release, result)

    # pyformat: disable
    if ((os_release := contents_by_path.get("/etc/os-release")) or
        (os_release := contents_by_path.get("/usr/lib/os-release"))):
    # pyformat: enable
      _ParseOSRelease(os_release, result)

    result = CollectDistroInfoResult.FromSerializedBytes(
        result.SerializeToString()
    )
    self.SendReply(result)


def _ParseLSBRelease(
    content: str,
    result: distro_pb2.CollectDistroInfoResult,
) -> None:
  """Parses `/etc/lsb-release`-like files."""
  for line in content.splitlines():
    line = line.strip()
    if not line:
      continue
    if line.startswith("#"):
      continue

    try:
      key, value = line.split("=", 1)
    except ValueError:
      continue

    value = value.strip()

    if key == "DISTRIB_ID":
      if not result.name:
        result.name = value

    if key == "DISTRIB_RELEASE":
      if not result.release:
        result.release = value

      if match := re.search(r"(?P<major>\d+)(\.(?P<minor>\d+))?", value):
        if not result.version_major:
          result.version_major = int(match["major"])
        if not result.version_minor and match["minor"]:
          result.version_minor = int(match["minor"])


def _ParseRedHatRelease(
    content: str,
    result: distro_pb2.CollectDistroInfoResult,
) -> None:
  """Parses `/etc/redhat-release`-like files."""
  if not result.release:
    result.release = content.strip()

  if match := re.search(r"release (?P<major>\d+)(\.(?P<minor>\d+))?", content):
    if not result.version_major:
      result.version_major = int(match["major"])
    if not result.version_minor and match["minor"]:
      result.version_minor = int(match["minor"])


def _ParseOSRelease(
    content: str,
    result: distro_pb2.CollectDistroInfoResult,
) -> None:
  """Parses `/etc/os-release`-like files."""
  for line in content.splitlines():
    line = line.strip()
    if not line:
      continue

    try:
      key, value = line.split("=", 1)
    except ValueError:
      continue

    # Values may or may not be quoted, so we need to strip these.
    value = value.strip().strip("\"'")

    if key == "NAME":
      if not result.name:
        result.name = value

    if key == "VERSION":
      if not result.release:
        result.release = value

    if key == "VERSION_ID":
      if match := re.search(r"(?P<major>\d+)(\.(?P<minor>\d+))?", value):
        if not result.version_major:
          result.version_major = int(match["major"])
        if not result.version_minor and match["minor"]:
          result.version_minor = int(match["minor"])
