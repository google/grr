#!/usr/bin/env python
# Lint as: python3
"""Tests for grr_response_client.client_actions.cloud."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io
import os
import platform
import subprocess
import unittest
from unittest import mock

from absl import app
import requests

from grr_response_client.client_actions import cloud
from grr_response_core import config
from grr_response_core.lib.rdfvalues import cloud as rdf_cloud
from grr.test_lib import client_test_lib
from grr.test_lib import test_lib


@unittest.skipIf(platform.system() == "Darwin",
                 "OS X cloud machines unsupported.")
class GetCloudVMMetadataTest(client_test_lib.EmptyActionTest):
  ZONE_URL = "http://metadata.google.internal/computeMetadata/v1/instance/zone"
  PROJ_URL = ("http://metadata.google.internal/computeMetadata/"
              "v1/project/project-id")

  def testBIOSCommandRaises(self):
    with mock.patch.multiple(
        cloud.GetCloudVMMetadata,
        LINUX_BIOS_VERSION_COMMAND="/bin/false",
        WINDOWS_SERVICES_COMMAND=["cmd", "/C", "exit 1"]):
      with self.assertRaises(subprocess.CalledProcessError):
        self.RunAction(
            cloud.GetCloudVMMetadata, arg=rdf_cloud.CloudMetadataRequests())

  def testNonMatchingBIOS(self):
    zone = mock.Mock(text="projects/123456789733/zones/us-central1-a")
    arg = rdf_cloud.CloudMetadataRequests(requests=[
        rdf_cloud.CloudMetadataRequest(
            bios_version_regex="Google",
            instance_type="GOOGLE",
            url=self.ZONE_URL,
            label="zone",
            headers={"Metadata-Flavor": "Google"})
    ])
    with mock.patch.object(
        cloud.GetCloudVMMetadata,
        "LINUX_BIOS_VERSION_COMMAND",
        new=["/bin/echo", "Gaagle"]):
      with mock.patch.object(requests, "request") as mock_requests:
        mock_requests.side_effect = [zone]
        results = self.RunAction(cloud.GetCloudVMMetadata, arg=arg)

      self.assertFalse(results)

  def testWindowsServiceQuery(self):
    project = mock.Mock(text="myproject")

    scquery_output_path = os.path.join(config.CONFIG["Test.data_dir"],
                                       "scquery_output.txt")
    with io.open(scquery_output_path, "rb") as filedesc:
      sc_query_output = filedesc.read()

    arg = rdf_cloud.CloudMetadataRequests(requests=[
        rdf_cloud.CloudMetadataRequest(
            bios_version_regex=".*amazon",
            instance_type="AMAZON",
            service_name_regex="SERVICE_NAME: AWSLiteAgent",
            url="http://169.254.169.254/latest/meta-data/ami-id",
            label="amazon-ami"),
        rdf_cloud.CloudMetadataRequest(
            bios_version_regex="Google",
            instance_type="GOOGLE",
            service_name_regex="SERVICE_NAME: GCEAgent",
            url=self.PROJ_URL,
            label="Google-project-id",
            headers={"Metadata-Flavor": "Google"})
    ])

    with mock.patch.object(platform, "system", return_value="Windows"):
      with mock.patch.object(
          subprocess, "check_output", return_value=sc_query_output):
        with mock.patch.object(requests, "request") as mock_requests:
          mock_requests.side_effect = [project]
          results = self.RunAction(cloud.GetCloudVMMetadata, arg=arg)

    responses = list(results[0].responses)
    self.assertLen(responses, 1)
    self.assertEqual(results[0].instance_type, "GOOGLE")
    for response in responses:
      if response.label == "Google-project-id":
        self.assertEqual(response.text, project.text)
      else:
        self.fail("Bad response.label: %s" % response.label)

  def testMultipleBIOSMultipleURLs(self):
    ami = mock.Mock(text="ami-12345678")
    arg = rdf_cloud.CloudMetadataRequests(requests=[
        rdf_cloud.CloudMetadataRequest(
            bios_version_regex=".*amazon",
            service_name_regex="SERVICE_NAME: AWSLiteAgent",
            instance_type="AMAZON",
            url="http://169.254.169.254/latest/meta-data/ami-id",
            label="amazon-ami"),
        rdf_cloud.CloudMetadataRequest(
            bios_version_regex="Google",
            service_name_regex="SERVICE_NAME: GCEAgent",
            instance_type="GOOGLE",
            url=self.PROJ_URL,
            label="Google-project-id",
            headers={"Metadata-Flavor": "Google"})
    ])
    with mock.patch.multiple(
        cloud.GetCloudVMMetadata,
        LINUX_BIOS_VERSION_COMMAND=["/bin/echo", "4.2.amazon"],
        WINDOWS_SERVICES_COMMAND=[
            "cmd.exe", "/C", "echo SERVICE_NAME: AWSLiteAgent"
        ]):
      with mock.patch.object(requests, "request") as mock_requests:
        mock_requests.side_effect = [ami]
        results = self.RunAction(cloud.GetCloudVMMetadata, arg=arg)

    responses = list(results[0].responses)
    self.assertLen(responses, 1)
    self.assertEqual(results[0].instance_type, "AMAZON")
    for response in responses:
      if response.label == "amazon-ami":
        self.assertEqual(response.text, ami.text)
      else:
        self.fail("Bad response.label: %s" % response.label)

  def testMatchingBIOSMultipleURLs(self):
    zone = mock.Mock(text="projects/123456789733/zones/us-central1-a")
    project = mock.Mock(text="myproject")
    arg = rdf_cloud.CloudMetadataRequests(requests=[
        rdf_cloud.CloudMetadataRequest(
            bios_version_regex="Google",
            service_name_regex="SERVICE_NAME: GCEAgent",
            instance_type="GOOGLE",
            url=self.ZONE_URL,
            label="zone",
            headers={"Metadata-Flavor": "Google"}),
        rdf_cloud.CloudMetadataRequest(
            bios_version_regex="Google",
            service_name_regex="SERVICE_NAME: GCEAgent",
            instance_type="GOOGLE",
            url=self.PROJ_URL,
            label="project-id",
            headers={"Metadata-Flavor": "Google"})
    ])

    with mock.patch.multiple(
        cloud.GetCloudVMMetadata,
        LINUX_BIOS_VERSION_COMMAND=["/bin/echo", "Google"],
        WINDOWS_SERVICES_COMMAND=[
            "cmd.exe", "/C", "echo SERVICE_NAME: GCEAgent"
        ]):
      with mock.patch.object(requests, "request") as mock_requests:
        mock_requests.side_effect = [zone, project]
        results = self.RunAction(cloud.GetCloudVMMetadata, arg=arg)

      responses = list(results[0].responses)
      self.assertLen(responses, 2)
      self.assertEqual(results[0].instance_type, "GOOGLE")
      for response in responses:
        if response.label == "zone":
          self.assertEqual(response.text, zone.text)
        elif response.label == "project-id":
          self.assertEqual(response.text, project.text)
        else:
          self.fail("Bad response.label: %s" % response.label)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
