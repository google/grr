#!/usr/bin/env python
"""Flows for interacting with containers."""

import datetime
import json
from typing import List

from grr_response_core.lib.rdfvalues import containers as rdf_containers
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import containers_pb2
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import server_stubs


class ContainerLabel(rdf_structs.RDFProtoStruct):
  """An RDF wrapper class for the `ContainerLabel` proto."""

  protobuf = containers_pb2.ContainerLabel
  rdf_deps = []


class ContainerDetails(rdf_structs.RDFProtoStruct):
  """An RDF wrapper class for the `ContainerDetails` proto."""

  protobuf = containers_pb2.ContainerDetails
  rdf_deps = [ContainerLabel]


class ListContainersFlowArgs(rdf_structs.RDFProtoStruct):
  """Arguments for ListContainers Flow."""

  protobuf = containers_pb2.ListContainersFlowArgs
  rdf_deps = []


class ListContainersFlowResult(rdf_structs.RDFProtoStruct):
  """Result for ListContainers Flow."""

  protobuf = containers_pb2.ListContainersFlowResult
  rdf_deps = [ContainerDetails]


class ListContainers(flow_base.FlowBase):
  """Lists containers running on the client.

  Returns to parent flow:
    A ListContainersFlowResult with a list of ContainerDetails.
  """

  friendly_name = "List Containers"
  category = "/Processes/"
  behaviours = flow_base.BEHAVIOUR_BASIC

  args_type = ListContainersFlowArgs
  result_types = (ListContainersFlowResult,)

  def ParseContainerList(
      self, stdout: str, binary: str
  ) -> List[ContainerDetails]:
    """Parses a list of containers from the stdout of a container runtime."""
    json_decoder = json.JSONDecoder(object_pairs_hook=dict)
    containers = []
    if binary == "crictl":
      stdout = json_decoder.decode(stdout)
      for line in stdout["containers"]:
        container = ContainerDetails()
        container.container_id = line["id"]
        container.image_name = line["image"]["image"]
        container.created_at = int(line["createdAt"])
        if "io.kubernetes.container.ports" in line["annotations"].keys():
          container.ports = []
          for port in line["annotations"]["io.kubernetes.container.ports"]:
            container.ports.append(
                "{0:s}/{1:s}".format(port["containerPort"], port["protocol"])
            )
        container.names = []
        container.names.append(line["metadata"]["name"])
        if line["labels"] is not None:
          container.labels = []
          for key, value in line["labels"].items():
            container.labels.append(ContainerLabel(label=key, value=value))
        container.state = containers_pb2.ContainerDetails.ContainerState.Value(
            line["state"]
        )
        container.runtime = containers_pb2.ContainerDetails.ContainerCli.CRICTL
        containers.append(container)
    elif binary == "docker":
      for line in stdout.strip().splitlines():
        line = json_decoder.decode(line)
        container = ContainerDetails()
        for key, value in line.items():
          if key == "ID":
            container.container_id = value
          if key == "Image":
            container.image_name = value
          if key == "Command":
            container.command = value
          if key == "CreatedAt":
            container.created_at = (
                datetime.datetime.strptime(
                    value, "%Y-%m-%d %H:%M:%S %z %Z"
                ).timestamp()
                * 10**9
            )
          if key == "Status":
            container.status = value
          if key == "Ports":
            container.ports = []
            container.ports.extend(value.split(", "))
          if key == "Names":
            container.names = value.split(",")
          if key == "Labels":
            container.labels = []
            for label in value.split(","):
              if label:
                key, value = label.split("=")
                container.labels.append(ContainerLabel(label=key, value=value))
          if key == "LocalVolumes":
            container.local_volumes = value
          if key == "Mounts":
            container.mounts = []
            container.mounts.extend(value.split(","))
          if key == "Networks":
            container.networks = []
            container.networks.extend(value.split(","))
          if key == "RunningFor":
            container.running_since = value
          if key == "State":
            if value == "created":
              container.state = (
                  containers_pb2.ContainerDetails.ContainerState.CONTAINER_CREATED
              )
            elif value == "running":
              container.state = (
                  containers_pb2.ContainerDetails.ContainerState.CONTAINER_RUNNING
              )
            elif value == "paused":
              container.state = (
                  containers_pb2.ContainerDetails.ContainerState.CONTAINER_PAUSED
              )
            elif value == "exited":
              container.state = (
                  containers_pb2.ContainerDetails.ContainerState.CONTAINER_EXITED
              )
            else:
              container.state = (
                  containers_pb2.ContainerDetails.ContainerState.CONTAINER_UNKNOWN
              )
        container.runtime = containers_pb2.ContainerDetails.ContainerCli.DOCKER
        containers.append(container)
    return containers

  def Start(self):
    """Schedules the action in the client (ListContainers ClientAction)."""
    request = rdf_containers.ListContainersRequest(
        inspect_hostroot=self.args.inspect_hostroot
    )
    self.CallClient(
        server_stubs.ListContainers,
        request,
        next_state=self.ReceiveActionOutput.__name__,
    )

  def ReceiveActionOutput(
      self,
      responses: flow_responses.Responses[rdf_containers.ListContainersResult],
  ):
    """Receives the action output and processes it."""
    # Checks the "Status" of the action, attaching information to the flow.
    if not responses.success:
      raise flow_base.FlowError(responses.status)

    if len(responses) != 1:
      raise flow_base.FlowError(
          f"Expected a single response, but got {list(responses)}"
      )

    containers = []
    for response in responses:
      for output in response.cli_outputs:
        if output.exit_status == 0 and output.stdout:
          self.Log(
              "Container CLI (%s) output: %s", output.binary, output.stdout
          )
          containers.extend(
              self.ParseContainerList(output.stdout, output.binary)
          )
        else:
          self.Log(
              "Container CLI (%s) returned non-zero exit status: %s",
              output.binary,
              output.stderr,
          )

    result = ListContainersFlowResult(containers=containers)
    self.SendReply(result)
