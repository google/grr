#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.

"""Tests for grr.lib.flows.general.services."""


import os

from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib import test_lib


class ServicesTest(test_lib.FlowTestsBaseclass):

  def testEnumerateRunningServices(self):

    class ClientMock(object):
      def EnumerateRunningServices(self, _):
        service = rdfvalue.Service(label="org.openbsd.ssh-agent",
                                   args="/usr/bin/ssh-agent -l")
        service.osx_launchd.sessiontype = "Aqua"
        service.osx_launchd.lastexitstatus = 0
        service.osx_launchd.timeout = 30
        service.osx_launchd.ondemand = 1

        return [service]

    # Run the flow in the emulated way.
    for _ in test_lib.TestFlowHelper(
        "EnumerateServices", ClientMock(), client_id=self.client_id,
        token=self.token, output="analysis/Services"):
      pass

    # Check the output file is created
    fd = aff4.FACTORY.Open(rdfvalue.RDFURN(self.client_id)
                           .Add("analysis/Services"),
                           token=self.token)

    self.assertEqual(fd.__class__.__name__, "RDFValueCollection")
    jobs = list(fd)

    self.assertEqual(len(fd), 1)
    self.assertEqual(jobs[0].label, "org.openbsd.ssh-agent")
    self.assertEqual(jobs[0].args, "/usr/bin/ssh-agent -l")
    self.assertIsInstance(jobs[0], rdfvalue.Service)

  SAMPLE_WMI_RESPONSE = {
      "AcceptPause": "False",
      "AcceptStop": "False",
      "Caption": "1394 OHCI Compliant Host Controller",
      "Description": "1394 OHCI Compliant Host Controller",
      "DesktopInteract": "False",
      "DisplayName": "1394 OHCI Compliant Host Controller",
      "ErrorControl": "Normal",
      "ExitCode": "1077",
      "InstallDate": "",
      "Name": "1394ohci",
      "PathName": "C:\\Windows\\system32\\drivers\\1394ohci.sys",
      "ServiceSpecificExitCode": "0",
      "ServiceType": "Kernel Driver",
      "StartMode": "Manual",
      "StartName": "",
      "Started": "False",
      "State": "Stopped",
      "Status": "OK",
      "SystemCreationClassName": "Win32_ComputerSystem",
      "SystemName": "TEST-PC",
      "TagId": "0"}

  def testEnumerateServices(self):
    """Test the EnumerateServices flow."""
    test_obj = self

    # This is a windows client.
    with aff4.FACTORY.Create(self.client_id, "VFSGRRClient",
                             token=self.token) as client:
      client.Set(client.Schema.SYSTEM("Windows"))

    # Swap this file for the driver binary.
    pathspec = rdfvalue.PathSpec(
        pathtype=rdfvalue.PathSpec.PathType.OS,
        path=os.path.join(self.base_path, "hello.exe"))

    output = "analysis/TestCollection"

    class ClientMock(test_lib.ActionMock):

      def WmiQuery(self, args):
        test_obj.assertTrue("SystemDriver" in args.query)

        return [rdfvalue.Dict(**test_obj.SAMPLE_WMI_RESPONSE)]

      def StatFile(self, args):
        # Make sure the flow wants to download the same file mentioned in the
        # WMI response.
        test_obj.assertTrue(args.pathspec.path,
                            test_obj.SAMPLE_WMI_RESPONSE["PathName"])

        # Return a pathspec for a file in our test_data which we can verify..
        return [rdfvalue.StatEntry(pathspec=pathspec,
                                   st_mode=33261, st_size=20746)]

      def Find(self, args):
        # Make sure the flow wants to download the same file mentioned in the
        # WMI response.
        driver_name = test_obj.SAMPLE_WMI_RESPONSE["PathName"]
        driver_basename = driver_name.split("\\")[-1]

        test_obj.assertTrue(args.path_regex.Search(driver_basename))

        # Return a pathspec for a file in our test_data which we can verify..
        return [rdfvalue.StatEntry(pathspec=pathspec,
                                   st_mode=33261, st_size=20746)]

    # Run the flow in the emulated way.
    client_mock = ClientMock("HashBuffer", "HashFile", "TransferBuffer")

    for _ in test_lib.TestFlowHelper(
        "EnumerateServices", client_mock,
        client_id=self.client_id, output=output, token=self.token):
      pass

    urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(pathspec, self.client_id)
    fd1 = aff4.FACTORY.Open(urn, token=self.token)
    fd2 = open(pathspec.path)
    fd2.seek(0, 2)

    self.assertEqual(fd2.tell(), int(fd1.Get(fd1.Schema.SIZE)))

    fd1.seek(0, 0)
    fd2.seek(0, 0)

    # Ensure the data is the same
    self.assertEqual(fd1.read(1000000), fd2.read(1000000))

    # Now check the collection was written properly.
    fd = aff4.FACTORY.Open(self.client_id.Add(output), token=self.token)
    self.assertEqual(fd.__class__.__name__, "RDFValueCollection")

    self.assertEqual(len(fd), 1)
    for x in fd:
      self.assertEqual(x.name, self.SAMPLE_WMI_RESPONSE["Name"])
      self.assertEqual(x.description, self.SAMPLE_WMI_RESPONSE["Description"])
      self.assertEqual(x.wmi_information.ToDict(), self.SAMPLE_WMI_RESPONSE)
