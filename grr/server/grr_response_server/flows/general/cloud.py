#!/usr/bin/env python
"""Flows for collection cloud information."""
import http.client
import io
import ipaddress
import re
import socket

from google.protobuf import any_pb2
from grr_response_core.lib.rdfvalues import cloud as rdf_cloud
from grr_response_core.lib.rdfvalues import mig_cloud
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import cloud_pb2
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import signed_commands_pb2
from grr_response_server import data_store
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import rrg_stubs
from grr_response_server import server_stubs
from grr_response_server.models import cloud as models_cloud
from grr_response_proto.rrg import os_pb2 as rrg_os_pb2
from grr_response_proto.rrg.action import execute_signed_command_pb2 as rrg_execute_signed_command_pb2
from grr_response_proto.rrg.action import get_tcp_response_pb2 as rrg_get_tcp_response_pb2
from grr_response_proto.rrg.action import query_wmi_pb2 as rrg_query_wmi_pb2


class CollectCloudVMMetadataResult(rdf_structs.RDFProtoStruct):
  """RDF wrapper for the `CollectCloudVMMetadataResult` message."""

  protobuf = cloud_pb2.CollectCloudVMMetadataResult
  rdf_deps = [rdf_cloud.CloudInstance]


class CollectCloudVMMetadata(
    flow_base.FlowBase[
        flows_pb2.EmptyFlowArgs,
        cloud_pb2.CollectCloudVMMetadataStore,
        flows_pb2.DefaultFlowProgress,
    ],
):
  """Flows that collects metadata about the endpoint's cloud VM."""

  category = "/Collectors/"
  behaviours = flow_base.BEHAVIOUR_DEBUG

  result_types = [CollectCloudVMMetadataResult]
  proto_result_types = [cloud_pb2.CollectCloudVMMetadataResult]

  proto_store_type = cloud_pb2.CollectCloudVMMetadataStore

  only_protos_allowed = True

  def Start(self) -> None:
    if self.rrg_support and self.rrg_os_type == rrg_os_pb2.LINUX:
      signed_command = data_store.REL_DB.ReadSignedCommand(
          "dmidecode_bios_version",
          operating_system=signed_commands_pb2.SignedCommand.OS.LINUX,
      )

      action = rrg_stubs.ExecuteSignedCommand()
      action.args.command = signed_command.command
      action.args.command_ed25519_signature = signed_command.ed25519_signature
      action.args.timeout.seconds = 10
      action.Call(self._ProcessRRGDmidecodeBIOSVersion)
    elif self.rrg_support and self.rrg_os_type == rrg_os_pb2.WINDOWS:
      action = rrg_stubs.QueryWmi()
      action.args.query = """
      SELECT Name
        FROM Win32_Service
       WHERE Name = 'GCEAgent'
          OR Name = 'AWSLiteAgent'
      """
      action.Call(self._ProcessRRGWin32Service)
    elif self.client_os in ["Linux", "Windows"]:
      args = mig_cloud.ToProtoCloudMetadataRequests(
          rdf_cloud.BuildCloudMetadataRequests()
      )

      self.CallClientProto(
          server_stubs.GetCloudVMMetadata,
          args,
          next_state=self._ProcessGetCloudVMMetadata.__name__,
      )
    else:
      raise flow_base.FlowError(f"Unsupported system: {self.client_os}")

  @flow_base.UseProto2AnyResponses
  def _ProcessRRGDmidecodeBIOSVersion(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      self.Log("Failed to collect BIOS version: %s", responses.status)
      return

    responses = list(responses)
    if len(responses) != 1:
      raise flow_base.FlowError(
          f"Unexpected number of `dmidecode` responses: {len(responses)}",
      )

    response = rrg_execute_signed_command_pb2.Result()
    response.ParseFromString(responses[0].value)

    bios_version = response.stdout.decode("utf-8", "backslashreplace").strip()

    if re.search("^Google$", bios_version) is not None:
      self._CollectGoogleMetadata()
    elif re.search("amazon", bios_version) is not None:
      self._CollectAmazonMetadata()
    else:
      self.Log("Non-cloud BIOS version string: %s", bios_version)

  @flow_base.UseProto2AnyResponses
  def _ProcessRRGWin32Service(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      raise flow_base.FlowError(
          f"Failed to query `Win32_Service`: {responses.status}",
      )

    # We queried for specific service names, so no results means no services
    # named `GCEAgent` or `AWSLiteAgent` were found.
    if not responses:
      self.Log("No cloud service found")

    for response_any in responses:
      response = rrg_query_wmi_pb2.Result()
      response.ParseFromString(response_any.value)

      if response.row["Name"].string == "GCEAgent":
        self._CollectGoogleMetadata()
      if response.row["Name"].string == "AWSLiteAgent":
        self._CollectAmazonMetadata()

  def _CollectGoogleMetadata(self) -> None:
    self.store.vm_metadata.cloud_type = jobs_pb2.CloudInstance.GOOGLE

    action = rrg_stubs.GetTcpResponse()
    action.args.address.ip_address.octets = _HTTP_SERVICE_IP_ADDRESS.packed
    action.args.address.port = _HTTP_SERVICE_PORT
    action.args.connect_timeout.seconds = 1
    action.args.write_timeout.seconds = 1
    action.args.read_timeout.seconds = 1

    action.args.data = _HTTPGoogle("/computeMetadata/v1/instance/id")
    action.Call(self._ProcessRRGGoogleInstanceID)

    action.args.data = _HTTPGoogle("/computeMetadata/v1/instance/zone")
    action.Call(self._ProcessRRGGoogleInstanceZone)

    action.args.data = _HTTPGoogle("/computeMetadata/v1/instance/hostname")
    action.Call(self._ProcessRRGGoogleInstanceHostname)

    action.args.data = _HTTPGoogle("/computeMetadata/v1/instance/machine-type")
    action.Call(self._ProcessRRGGoogleInstanceMachineType)

    action.args.data = _HTTPGoogle("/computeMetadata/v1/project/project-id")
    action.Call(self._ProcessRRGGoogleProjectID)

  def _CollectAmazonMetadata(self) -> None:
    self.store.vm_metadata.cloud_type = jobs_pb2.CloudInstance.AMAZON

    action = rrg_stubs.GetTcpResponse()
    action.args.address.ip_address.octets = _HTTP_SERVICE_IP_ADDRESS.packed
    action.args.address.port = _HTTP_SERVICE_PORT
    action.args.connect_timeout.seconds = 1
    action.args.write_timeout.seconds = 1
    action.args.read_timeout.seconds = 1
    action.args.data = "\r\n".join([
        "GET /latest/api/token",
        "HTTP/1.1",
        "X-aws-ec2-metadata-token-ttl-seconds: 21600",
        "",
        "",
    ]).encode("ascii")
    action.Call(self._ProcessRRGAmazonAPIToken)

  @flow_base.UseProto2AnyResponses
  def _ProcessRRGAmazonAPIToken(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      raise flow_base.FlowError(
          f"Failed to obtain Amazon API token: {responses.status}",
      )

    responses = list(responses)
    if len(responses) != 1:
      raise flow_base.FlowError(
          f"Unexpected number of Amazon API token responses: {len(responses)}"
      )

    response = rrg_get_tcp_response_pb2.Result()
    response.ParseFromString(responses[0].value)

    http_response = _HTTPResponse(response.data)
    if http_response.status != http.HTTPStatus.OK:
      raise flow_base.FlowError(
          f"Failed to obtain Amazon API token: {http_response.status}",
      )

    token = http_response.read().decode("ascii").strip()

    action = rrg_stubs.GetTcpResponse()
    action.args.address.ip_address.octets = _HTTP_SERVICE_IP_ADDRESS.packed
    action.args.address.port = _HTTP_SERVICE_PORT
    action.args.connect_timeout.seconds = 1
    action.args.write_timeout.seconds = 1
    action.args.read_timeout.seconds = 1

    action.args.data = _HTTPAmazon(
        "/latest/meta-data/instance-id",
        token=token,
    )
    action.Call(self._ProcessRRGAmazonInstanceID)

    action.args.data = _HTTPAmazon(
        "/latest/meta-data/instance-type",
        token=token,
    )
    action.Call(self._ProcessRRGAmazonInstanceType)

    action.args.data = _HTTPAmazon(
        "/latest/meta-data/ami-id",
        token=token,
    )
    action.Call(self._ProcessRRGAmazonAMIID)

    action.args.data = _HTTPAmazon(
        "/latest/meta-data/hostname",
        token=token,
    )
    action.Call(self._ProcessRRGAmazonHostname)

    action.args.data = _HTTPAmazon(
        "/latest/meta-data/public-hostname",
        token=token,
    )
    action.Call(self._ProcessRRGAmazonPublicHostname)

  @flow_base.UseProto2AnyResponses
  def _ProcessRRGGoogleInstanceID(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      raise flow_base.FlowError(
          f"Failed to collect Google instance ID: {responses.status}",
      )

    response = rrg_get_tcp_response_pb2.Result()
    response.ParseFromString(list(responses)[0].value)

    http_response = _HTTPResponse(response.data)
    if http_response.status != http.HTTPStatus.OK:
      raise flow_base.FlowError(
          f"Failed to collect Google instance ID: {http_response.status}",
      )

    self.store.vm_metadata.google.instance_id = (
        http_response.read().decode("ascii").strip()
    )

  @flow_base.UseProto2AnyResponses
  def _ProcessRRGGoogleInstanceZone(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      raise flow_base.FlowError(
          f"Failed to collect Google instance zone: {responses.status}",
      )

    response = rrg_get_tcp_response_pb2.Result()
    response.ParseFromString(list(responses)[0].value)

    http_response = _HTTPResponse(response.data)
    if http_response.status != http.HTTPStatus.OK:
      raise flow_base.FlowError(
          f"Failed to collect Google instance zone: {http_response.status}",
      )

    self.store.vm_metadata.google.zone = (
        http_response.read().decode("ascii").strip()
    )

  @flow_base.UseProto2AnyResponses
  def _ProcessRRGGoogleInstanceHostname(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      raise flow_base.FlowError(
          f"Failed to collect Google instance hostname: {responses.status}",
      )

    response = rrg_get_tcp_response_pb2.Result()
    response.ParseFromString(list(responses)[0].value)

    http_response = _HTTPResponse(response.data)
    if http_response.status != http.HTTPStatus.OK:
      raise flow_base.FlowError(
          f"Failed to collect Google instance hostname: {http_response.status}",
      )

    self.store.vm_metadata.google.hostname = (
        http_response.read().decode("ascii").strip()
    )

  @flow_base.UseProto2AnyResponses
  def _ProcessRRGGoogleInstanceMachineType(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      raise flow_base.FlowError(
          f"Failed to collect Google machine type: {responses.status}",
      )

    response = rrg_get_tcp_response_pb2.Result()
    response.ParseFromString(list(responses)[0].value)

    http_response = _HTTPResponse(response.data)
    if http_response.status != http.HTTPStatus.OK:
      raise flow_base.FlowError(
          f"Failed to collect Google machine type: {http_response.status}",
      )

    self.store.vm_metadata.google.machine_type = (
        http_response.read().decode("ascii").strip()
    )

  @flow_base.UseProto2AnyResponses
  def _ProcessRRGGoogleProjectID(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      raise flow_base.FlowError(
          f"Failed to collect Google project ID: {responses.status}",
      )

    response = rrg_get_tcp_response_pb2.Result()
    response.ParseFromString(list(responses)[0].value)

    http_response = _HTTPResponse(response.data)
    if http_response.status != http.HTTPStatus.OK:
      raise flow_base.FlowError(
          f"Failed to collect Google project ID: {http_response.status}",
      )

    self.store.vm_metadata.google.project_id = (
        http_response.read().decode("ascii").strip()
    )

  @flow_base.UseProto2AnyResponses
  def _ProcessRRGAmazonInstanceID(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      raise flow_base.FlowError(
          f"Failed to collect Amazon instance ID: {responses.status}",
      )

    response = rrg_get_tcp_response_pb2.Result()
    response.ParseFromString(list(responses)[0].value)

    http_response = _HTTPResponse(response.data)
    if http_response.status != http.HTTPStatus.OK:
      raise flow_base.FlowError(
          f"Failed to collect Amazon instance ID: {http_response.status}",
      )

    self.store.vm_metadata.amazon.instance_id = (
        http_response.read().decode("ascii").strip()
    )

  @flow_base.UseProto2AnyResponses
  def _ProcessRRGAmazonInstanceType(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      raise flow_base.FlowError(
          f"Failed to collect Amazon instance type: {responses.status}",
      )

    response = rrg_get_tcp_response_pb2.Result()
    response.ParseFromString(list(responses)[0].value)

    http_response = _HTTPResponse(response.data)
    if http_response.status != http.HTTPStatus.OK:
      raise flow_base.FlowError(
          f"Failed to collect Amazon instance type: {http_response.status}",
      )

    self.store.vm_metadata.amazon.instance_type = (
        http_response.read().decode("ascii").strip()
    )

  @flow_base.UseProto2AnyResponses
  def _ProcessRRGAmazonAMIID(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      raise flow_base.FlowError(
          f"Failed to collect Amazon AMI ID: {responses.status}",
      )

    response = rrg_get_tcp_response_pb2.Result()
    response.ParseFromString(list(responses)[0].value)

    http_response = _HTTPResponse(response.data)
    if http_response.status != http.HTTPStatus.OK:
      raise flow_base.FlowError(
          f"Failed to collect Amazon AMI ID: {http_response.status}",
      )

    self.store.vm_metadata.amazon.ami_id = (
        http_response.read().decode("ascii").strip()
    )

  @flow_base.UseProto2AnyResponses
  def _ProcessRRGAmazonHostname(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      raise flow_base.FlowError(
          f"Failed to collect Amazon hostname: {responses.status}",
      )

    response = rrg_get_tcp_response_pb2.Result()
    response.ParseFromString(list(responses)[0].value)

    http_response = _HTTPResponse(response.data)
    if http_response.status != http.HTTPStatus.OK:
      raise flow_base.FlowError(
          f"Failed to collect Amazon hostname: {http_response.status}",
      )

    self.store.vm_metadata.amazon.hostname = (
        http_response.read().decode("ascii").strip()
    )

  @flow_base.UseProto2AnyResponses
  def _ProcessRRGAmazonPublicHostname(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      raise flow_base.FlowError(
          f"Failed to collect Amazon public hostname: {responses.status}",
      )

    response = rrg_get_tcp_response_pb2.Result()
    response.ParseFromString(list(responses)[0].value)

    http_response = _HTTPResponse(response.data)
    if http_response.status != http.HTTPStatus.OK:
      # Per AWS documentation, `public-hostname` is available only on hosts with
      # public IPv4 addresses and `enableDnsHostnames` option set. Attempts to
      # query this property will result in HTTP 404 status, so we don't treat
      # these as fatal.
      #
      # https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-metadata.html
      self.Log("Amazon public hostname not available")
      return

    self.store.vm_metadata.amazon.public_hostname = (
        http_response.read().decode("ascii").strip()
    )

  @flow_base.UseProto2AnyResponses
  def _ProcessGetCloudVMMetadata(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      raise flow_base.FlowError(
          f"Failed to collect cloud VM metadata: {responses.status}",
      )

    for response in responses:
      metadata = flows_pb2.CloudMetadataResponses()
      metadata.ParseFromString(response.value)

      result = cloud_pb2.CollectCloudVMMetadataResult()
      result.vm_metadata.CopyFrom(
          models_cloud.ConvertCloudMetadataResponsesToCloudInstance(metadata),
      )
      self.SendReplyProto(result)

  def End(self) -> None:
    if not self.rrg_support:
      # Metadata has been already sent in the `_ProcessGetCloudVMMetadata` state
      # method, no need to send it again.
      return

    # TODO: Remove once `unique_id` is deprecated.
    if (
        self.store.vm_metadata.google.zone
        and self.store.vm_metadata.google.project_id
        and self.store.vm_metadata.google.instance_id
    ):
      self.store.vm_metadata.google.unique_id = models_cloud.MakeGoogleUniqueID(
          self.store.vm_metadata.google
      )

    result = cloud_pb2.CollectCloudVMMetadataResult()
    result.vm_metadata.CopyFrom(self.store.vm_metadata)

    self.SendReplyProto(result)


_HTTP_SERVICE_IP_ADDRESS = ipaddress.ip_address("169.254.169.254")
_HTTP_SERVICE_PORT = 80


def _HTTPGoogle(uri: str) -> bytes:
  """Returns an HTTP request for Google cloud VMs."""
  return "\r\n".join([
      f"GET {uri} HTTP/1.1",
      "Metadata-Flavor: Google",
      "",
      "",
  ]).encode("ascii")


def _HTTPAmazon(uri: str, token: str) -> bytes:
  """Returns an HTTP request for Amazon cloud VMs."""
  return "\r\n".join([
      f"GET {uri} HTTP/1.1",
      f"X-aws-ec2-metadata-token: {token}",
      "",
      "",
  ]).encode("ascii")


def _HTTPResponse(data: bytes) -> http.client.HTTPResponse:
  """Creates a standard HTTP response object for given raw response data."""

  class BytesIOSocket(socket.socket):

    def __init__(self):
      # By default, IPv4 socket is created. This won't work in IPv6-only envi-
      # ronments, so we force the socket to be IPv6. This on the other hand will
      # not work in IPv4-only environments but that should be rare nowadays.
      super().__init__(family=socket.AF_INET6)

    def makefile(self, *args, **kwargs):
      del args, kwargs  # Unused.
      return io.BytesIO(data)

  response = http.client.HTTPResponse(BytesIOSocket())
  response.begin()
  return response
