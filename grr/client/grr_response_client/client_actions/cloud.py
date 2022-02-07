#!/usr/bin/env python
"""Client actions for cloud VMs."""

import os
import platform
import re
import subprocess

import requests

from grr_response_client import actions
from grr_response_core.lib.rdfvalues import cloud as rdf_cloud


class GetCloudVMMetadata(actions.ActionPlugin):
  """Get metadata for cloud VMs.

  To avoid waiting on dns timeouts, causing unnecessary network traffic, and
  getting unreliable data back we first attempt to determine if we are running
  on a cloud VM. There isn't a reliable way to do so, but we make do by
  inspecting BIOS strings on linux and looking at running services on windows.

  We make the regexes used to check that data customizable from the server side
  so we can adapt to minor changes without updating the client.
  """
  in_rdfvalue = rdf_cloud.CloudMetadataRequests
  out_rdfvalues = [rdf_cloud.CloudMetadataResponses]

  LINUX_BIOS_VERSION_COMMAND = ["/usr/sbin/dmidecode", "-s", "bios-version"]
  WINDOWS_SERVICES_COMMAND = [
      "%s\\System32\\sc.exe" % os.environ.get("SYSTEMROOT", r"C:\Windows"),
      "query",
      # Make sure that stopped services are included into the list.
      # A particular cloud service doesn't have to actually be running to
      # be an indicator of a cloud machine.
      "state=",
      "all",
  ]

  AMAZON_TOKEN_URL = "http://169.254.169.254/latest/api/token"
  AMAZON_TOKEN_REQUEST_HEADERS = {
      "X-aws-ec2-metadata-token-ttl-seconds": "21600",
  }
  AMAZON_TOKEN_HEADER = "X-aws-ec2-metadata-token"

  def IsCloud(self, request, bios_version, services):
    """Test to see if we're on a cloud machine."""
    if request.bios_version_regex and bios_version:
      if re.match(request.bios_version_regex, bios_version):
        return True
    if request.service_name_regex and services:
      if re.search(request.service_name_regex, services):
        return True
    return False

  def GetMetaData(self, request):
    """Get metadata from local metadata server.

    Any failed URL check will fail the whole action since our bios/service
    checks may not always correctly identify cloud machines. We don't want to
    wait on multiple DNS timeouts.

    Args:
      request: CloudMetadataRequest object
    Returns:
      rdf_cloud.CloudMetadataResponse object
    Raises:
      ValueError: if request has a timeout of 0. This is a defensive
      check (we pass 1.0) because the requests library just times out and it's
      not obvious why.
    """
    if request.timeout == 0:
      raise ValueError("Requests library can't handle timeout of 0")
    result = requests.request(
        "GET", request.url, headers=request.headers, timeout=request.timeout)
    # By default requests doesn't raise on HTTP error codes.
    result.raise_for_status()

    # Requests does not always raise an exception when an incorrect response
    # is received. This fixes that behaviour.
    if not result.ok:
      raise requests.RequestException(response=result)

    return rdf_cloud.CloudMetadataResponse(
        label=request.label or request.url, text=result.text)

  def GetAWSMetadataToken(self) -> str:
    """Get the session token for IMDSv2."""
    result = requests.put(
        self.AMAZON_TOKEN_URL,
        headers=self.AMAZON_TOKEN_REQUEST_HEADERS,
        timeout=1.0)
    result.raise_for_status()

    # Requests does not always raise an exception when an incorrect response
    # is received. This fixes that behaviour.
    if not result.ok:
      raise requests.RequestException(response=result)

    return result.text

  def Run(self, args: rdf_cloud.CloudMetadataRequests):
    bios_version = None
    services = None

    # The output of commands is not guaranteed to contain valid Unicode text but
    # it should most of the time. Since we are just searching for a particular
    # pattern it is safe to replace spurious bytes with '�' as they simply have
    # no significance for search results.
    if platform.system() == "Linux":
      bios_version = subprocess.check_output(self.LINUX_BIOS_VERSION_COMMAND)
      bios_version = bios_version.decode("utf-8", "replace")
    elif platform.system() == "Windows":
      services = subprocess.check_output(self.WINDOWS_SERVICES_COMMAND)
      services = services.decode("utf-8", "replace")
    else:
      # Interrogate shouldn't call this client action on OS X machines at all,
      # so raise.
      raise RuntimeError("Only linux and windows cloud vms supported.")

    result_list = []
    instance_type = None
    aws_metadata_token = ""
    for request in args.requests:
      if self.IsCloud(request, bios_version, services):
        instance_type = request.instance_type
        if instance_type == rdf_cloud.CloudInstance.InstanceType.AMAZON:
          if not aws_metadata_token:
            aws_metadata_token = self.GetAWSMetadataToken()
          request.headers[self.AMAZON_TOKEN_HEADER] = aws_metadata_token
        result_list.append(self.GetMetaData(request))
    if result_list:
      self.SendReply(
          rdf_cloud.CloudMetadataResponses(
              responses=result_list, instance_type=instance_type))
