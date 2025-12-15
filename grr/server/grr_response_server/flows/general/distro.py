#!/usr/bin/env python
"""Flows for collecting Linux distribution information."""

import itertools
import re

from google.protobuf import any_pb2
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import distro_pb2
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_server import data_store
from grr_response_server import file_store
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import rrg_stubs
from grr_response_server import server_stubs
from grr_response_server.models import blobs as models_blobs
from grr_response_proto.rrg.action import get_file_contents_pb2 as rrg_get_file_contents_pb2


class CollectDistroInfoResult(rdf_structs.RDFProtoStruct):
  """RDF wrapper for the `CollectDistroInfoResult` message."""

  protobuf = distro_pb2.CollectDistroInfoResult
  rdf_deps = []


class CollectDistroInfo(flow_base.FlowBase):
  """Flow that collects information about the endpoint Linux distribution."""

  category = "/Collectors/"
  behaviours = flow_base.BEHAVIOUR_DEBUG

  result_types = [CollectDistroInfoResult]
  proto_result_types = [distro_pb2.CollectDistroInfoResult]

  proto_store_type = distro_pb2.CollectDistroInfoStore

  only_protos_allowed = True

  def Start(self) -> None:
    if self.client_os != "Linux":
      raise flow_base.FlowError(f"Unsupported system: {self.client_os}")

    if self.rrg_support:
      action = rrg_stubs.GetFileContents()
      # TODO: Use a single RRG call for collecting these (this is
      # now possible since https://github.com/google/rrg/pull/128).
      action.args.paths.add()

      action.args.paths[0].raw_bytes = "/etc/enterprise-release".encode("utf-8")
      action.Call(self._ProcessRRGEnterpriseRelease)

      action.args.paths[0].raw_bytes = "/etc/oracle-release".encode("utf-8")
      action.Call(self._ProcessRRGOracleRelease)

      action.args.paths[0].raw_bytes = "/etc/redhat-release".encode("utf-8")
      action.Call(self._ProcessRRGRedHatRelease)

      action.args.paths[0].raw_bytes = "/etc/rocky-release".encode("utf-8")
      action.Call(self._ProcessRRGRockyRelease)

      action.args.paths[0].raw_bytes = "/etc/system-release".encode("utf-8")
      action.Call(self._ProcessRRGSystemRelease)

      action.args.paths[0].raw_bytes = "/etc/lsb-release".encode("utf-8")
      action.Call(self._ProcessRRGLSBRelease)

      action.args.paths[0].raw_bytes = "/etc/os-release".encode("utf-8")
      action.Call(self._ProcessRRGOSRelease)

      action.args.paths[0].raw_bytes = "/usr/lib/os-release".encode("utf-8")
      action.Call(self._ProcessRRGOSRelease)

      return

    ff_args = flows_pb2.FileFinderArgs()
    ff_args.action.action_type = flows_pb2.FileFinderAction.Action.DOWNLOAD
    ff_args.pathtype = jobs_pb2.PathSpec.PathType.OS
    ff_args.paths.extend([
        # Non-LSB compliant systems.
        "/etc/enterprise-release",
        "/etc/oracle-release",
        "/etc/redhat-release",
        "/etc/rocky-release",
        "/etc/system-release",
        # LSB compliant systems.
        "/etc/lsb-release",
        # systemd-enabled systems.
        "/etc/os-release",
        "/usr/lib/os-release",
    ])

    self.CallClientProto(
        server_stubs.FileFinderOS,
        ff_args,
        next_state=self._ProcessRelease.__name__,
    )

  @flow_base.UseProto2AnyResponses
  def _ProcessRRGLSBRelease(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      return

    for response in responses:
      result = rrg_get_file_contents_pb2.Result()
      result.ParseFromString(response.value)

      if result.error:
        return

    self.Log("Received content from `/etc/lsb-release`")

    content = _GetFileContentResponsesToContent(responses)
    _ParseLSBRelease(content, self.store.result)

  @flow_base.UseProto2AnyResponses
  def _ProcessRRGSystemRelease(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      return

    for response in responses:
      result = rrg_get_file_contents_pb2.Result()
      result.ParseFromString(response.value)

      if result.error:
        return

    self.Log("Received content from `/etc/system-release`")

    content = _GetFileContentResponsesToContent(responses)
    if not self.store.result.release:
      self.store.result.release = content.strip()

  @flow_base.UseProto2AnyResponses
  def _ProcessRRGOracleRelease(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      return

    for response in responses:
      result = rrg_get_file_contents_pb2.Result()
      result.ParseFromString(response.value)

      if result.error:
        return

    self.Log("Received content from `/etc/oracle-release`")

    if not self.store.result.name:
      self.store.result.name = "OracleLinux"

    content = _GetFileContentResponsesToContent(responses)
    _ParseRedHatRelease(content, self.store.result)

  @flow_base.UseProto2AnyResponses
  def _ProcessRRGEnterpriseRelease(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      return

    for response in responses:
      result = rrg_get_file_contents_pb2.Result()
      result.ParseFromString(response.value)

      if result.error:
        return

    self.Log("Received content from `/etc/enterprise-release`")

    if not self.store.result.name:
      self.store.result.name = "OEL"

    content = _GetFileContentResponsesToContent(responses)
    _ParseRedHatRelease(content, self.store.result)

  @flow_base.UseProto2AnyResponses
  def _ProcessRRGRockyRelease(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      return

    for response in responses:
      result = rrg_get_file_contents_pb2.Result()
      result.ParseFromString(response.value)

      if result.error:
        return

    self.Log("Received content from `/etc/rocky-release`")

    if not self.store.result.name:
      self.store.result.name = "Rocky"

    content = _GetFileContentResponsesToContent(responses)
    _ParseRedHatRelease(content, self.store.result)

  @flow_base.UseProto2AnyResponses
  def _ProcessRRGRedHatRelease(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      return

    for response in responses:
      result = rrg_get_file_contents_pb2.Result()
      result.ParseFromString(response.value)

      if result.error:
        return

    self.Log("Received content from `/etc/redhat-release`")

    if not self.store.result.name:
      self.store.result.name = "RedHat"

    content = _GetFileContentResponsesToContent(responses)
    _ParseRedHatRelease(content, self.store.result)

  @flow_base.UseProto2AnyResponses
  def _ProcessRRGOSRelease(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      return

    for response in responses:
      result = rrg_get_file_contents_pb2.Result()
      result.ParseFromString(response.value)

      if result.error:
        return

    self.Log("Received content from systemd `os-release` file")

    content = _GetFileContentResponsesToContent(responses)
    _ParseOSRelease(content, self.store.result)

  def End(self) -> None:
    if not self.rrg_support:
      # The distro information has been already sent in the `_ProcessRelease`
      # state method, no need to send it again.
      return

    self.SendReplyProto(self.store.result)

  @flow_base.UseProto2AnyResponses
  def _ProcessRelease(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      raise flow_base.FlowError(
          f"Failed to collect release files: {responses.status}",
      )

    blob_ids_by_path: dict[str, set[models_blobs.BlobID]] = dict()

    for response_any in responses:
      if not response_any.Is(flows_pb2.FileFinderResult.DESCRIPTOR):
        raise flow_base.FlowError(
            f"Unexpected file-finder response type: {response_any.type_url}",
        )
      response = flows_pb2.FileFinderResult()
      response_any.Unpack(response)

      path = response.stat_entry.pathspec.path

      for chunk in response.transferred_file.chunks:
        path_blob_ids = blob_ids_by_path.setdefault(path, set())
        path_blob_ids.add(models_blobs.BlobID(chunk.digest))

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

    # fmt: off
    if ((os_release := contents_by_path.get("/etc/os-release")) or
        (os_release := contents_by_path.get("/usr/lib/os-release"))):
    # fmt: on
      _ParseOSRelease(os_release, result)

    self.SendReplyProto(result)


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


def _GetFileContentResponsesToContent(
    responses: flow_responses.Responses[any_pb2.Any],
) -> str:
  """Retrieves file content from `GET_FILE_CONTENTS` action responses."""
  blob_ids: list[models_blobs.BlobID] = list()

  for response in responses:
    result = rrg_get_file_contents_pb2.Result()
    result.ParseFromString(response.value)

    blob_ids.append(models_blobs.BlobID(result.blob_sha256))

  blobs_by_blob_id = data_store.BLOBS.ReadAndWaitForBlobs(
      blob_ids,
      timeout=rdfvalue.Duration.From(30, rdfvalue.SECONDS),
  )

  content = b"".join(blobs_by_blob_id[blob_id] for blob_id in blob_ids)
  return content.decode("utf-8")
