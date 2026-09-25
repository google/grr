#!/usr/bin/env python
"""The ListContainers client action."""

from grr_response_client import actions
from grr_response_client import client_utils_common
from grr_response_core.lib.rdfvalues import containers as rdf_containers


class ListContainers(actions.ActionPlugin):
  """Returns a list of containers running on the client."""

  in_rdfvalue = rdf_containers.ListContainersRequest
  out_rdfvalues = [rdf_containers.ListContainersResult]

  commands = (
      ("/home/kubernetes/bin/crictl", ["ps", "-a", "-o", "json"]),
      ("/usr/bin/crictl", ["ps", "-a", "-o", "json"]),
      ("/usr/bin/docker", ["ps", "-a", "--format", "json", "--no-trunc"]),
  )

  def Run(self, args: rdf_containers.ListContainersRequest) -> None:
    """Returns a list of container CLI outputs back to the server."""
    outputs = []
    for cmd, cmdargs in self.commands:
      output = rdf_containers.ListContainersOutput()
      output.binary = cmd.split("/")[-1]  # pyrefly: ignore[missing-attribute]
      if args.inspect_hostroot:  # pyrefly: ignore[missing-attribute]
        cmdargs = ["/hostroot", cmd] + cmdargs
        cmd = "/usr/sbin/chroot"
      try:
        stdout, stderr, exit_status, time_taken = client_utils_common.Execute(
            cmd, cmdargs
        )
        output.stdout = stdout  # pyrefly: ignore[missing-attribute]
        output.stderr = stderr  # pyrefly: ignore[missing-attribute]
        output.exit_status = exit_status  # pyrefly: ignore[missing-attribute]
        output.seconds_taken = time_taken  # pyrefly: ignore[missing-attribute]
        outputs.append(output)
      except FileNotFoundError as e:
        output.stderr = "Container CLI not found: {0!s}".format(e)  # pyrefly: ignore[missing-attribute]
        output.exit_status = 2  # pyrefly: ignore[missing-attribute]
        outputs.append(output)
        continue

    self.SendReply(rdf_containers.ListContainersResult(cli_outputs=outputs))
