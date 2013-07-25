#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.
# -*- mode: python; encoding: utf-8 -*-

"""Tests for artifacts."""



import os
import subprocess

from grr.lib import aff4
from grr.lib import artifact
from grr.lib import flags
from grr.lib import parsers
from grr.lib import rdfvalue
from grr.lib import test_lib


# Shorcut to make things cleaner.
Artifact = artifact.GenericArtifact   # pylint: disable=g-bad-name
Collector = artifact.Collector        # pylint: disable=g-bad-name


class ArtifactTest(test_lib.GRRBaseTest):

  def testArtifactsValidate(self):
    """Check each artifact we have passes validation."""

    for a_cls in artifact.Artifact.classes:
      if a_cls == "Artifact":
        continue    # Skip the base object.
      art = artifact.Artifact.classes[a_cls]
      art_obj = art()
      art_obj.Validate()

    art_cls = artifact.Artifact.classes["ApplicationEventLog"]
    art_obj = art_cls()
    art_obj.LABELS.append("BadLabel")

    self.assertRaises(artifact.ArtifactDefinitionError, art_obj.Validate)

  def testRDFMaps(self):
    """Validate the RDFMaps."""
    for rdf_name, dat in artifact.GRRArtifactMappings.rdf_map.items():
      # "info/software", "InstalledSoftwarePackages", "INSTALLED_PACKAGES",
      # "Append"
      _, aff4_type, aff4_attribute, operator = dat

      if operator not in ["Set", "Append"]:
        raise artifact.ArtifactDefinitionError(
            "Bad RDFMapping, unknown operator %s in %s" %
            (operator, rdf_name))

      if aff4_type not in aff4.AFF4Object.classes:
        raise artifact.ArtifactDefinitionError(
            "Bad RDFMapping, invalid AFF4 Object %s in %s" %
            (aff4_type, rdf_name))

      attr = getattr(aff4.AFF4Object.classes[aff4_type].SchemaCls,
                     aff4_attribute)()
      if not isinstance(attr, rdfvalue.RDFValue):
        raise artifact.ArtifactDefinitionError(
            "Bad RDFMapping, bad attribute %s for %s" %
            (aff4_attribute, rdf_name))


WMI_SAMPLE = [
    rdfvalue.Dict({u"Version": u"65.61.49216", u"InstallDate2": u"",
                   u"Name": u"Google Chrome", u"Vendor": u"Google, Inc.",
                   u"Description": u"Google Chrome", u"IdentifyingNumber":
                   u"{35790B21-ACFE-33F5-B320-9DA320D96682}",
                   u"InstallDate": u"20130710"}),
    rdfvalue.Dict({u"Version": u"7.0.1", u"InstallDate2": u"",
                   u"Name": u"Parity Agent", u"Vendor": u"Bit9, Inc.",
                   u"Description": u"Parity Agent", u"IdentifyingNumber":
                   u"{ADC7EB41-4CC2-4FBA-8FBE-9338A9FB7666}",
                   u"InstallDate": u"20130710"}),
    rdfvalue.Dict({u"Version": u"8.0.61000", u"InstallDate2": u"",
                   u"Name": u"Microsoft Visual C++ 2005 Redistributable (x64)",
                   u"Vendor": u"Microsoft Corporation", u"Description":
                   u"Microsoft Visual C++ 2005 Redistributable (x64)",
                   u"IdentifyingNumber":
                   u"{ad8a2fa1-06e7-4b0d-927d-6e54b3d3102}",
                   u"InstallDate": u"20130710"})]


class TestCmdProcessor(parsers.CommandParser):

  out_type = "SoftwarePackage"

  def Parse(self, cmd, args, stdout, stderr, return_val, time_taken):
    _ = cmd, args, stdout, stderr, return_val, time_taken
    installed = rdfvalue.SoftwarePackage.InstallState.INSTALLED
    soft = rdfvalue.SoftwarePackage(name="Package1", description="Desc1",
                                    version="1", architecture="amd64",
                                    install_state=installed)
    yield soft
    soft = rdfvalue.SoftwarePackage(name="Package2", description="Desc2",
                                    version="1", architecture="i386",
                                    install_state=installed)
    yield soft


class TestCmdArtifact(Artifact):
  """Test command artifact for dpkg."""
  SUPPORTED_OS = ["Linux"]
  LABELS = ["Software"]

  COLLECTORS = [
      Collector(action="RunCommand",
                args={"cmd": "/usr/bin/dpkg", "args": ["--list"]},
               )
  ]
  PROCESSOR = "TestCmdProcessor"


class TestFileArtifact(Artifact):
  """Linux auth log file."""
  SUPPORTED_OS = ["Linux"]
  LABELS = ["Logs", "Auth"]
  COLLECTORS = [
      Collector(action="GetFile",
                args={"path": "/var/log/auth.log"})
  ]


class ArtifactFlowTest(test_lib.FlowTestsBaseclass):

  class MockClient(test_lib.ActionMock):

    def WmiQuery(self, _):
      return WMI_SAMPLE

  def testCmdArtifact(self):
    """Check we can run command based artifacts."""

    fd = aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw")
    fd.Set(fd.Schema.SYSTEM("Linux"))
    fd.Flush()

    class Popen(object):
      """A mock object for subprocess.Popen."""

      def __init__(self, run, stdout, stderr):
        Popen.running_args = run
        Popen.stdout = stdout
        Popen.stderr = stderr
        Popen.returncode = 0

      def communicate(self):  # pylint: disable=g-bad-name
        return "stdout here", "stderr here"

    client_mock = self.MockClient("ExecuteCommand")
    with test_lib.Stubber(subprocess, "Popen", Popen):
      for _ in test_lib.TestFlowHelper(
          "ArtifactCollectorFlow", client_mock, client_id=self.client_id,
          use_tsk=False, artifact_list=["TestCmdArtifact"], token=self.token):
        pass
    urn = self.client_id.Add("info/software")
    fd = aff4.FACTORY.Open(urn, token=self.token)
    packages = fd.Get(fd.Schema.INSTALLED_PACKAGES)
    self.assertEquals(len(packages), 2)

  def testWMIQueryArtifact(self):
    """Check we can run command based artifacts."""

    fd = aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw")
    fd.Set(fd.Schema.SYSTEM("Windows"))
    fd.Flush()

    for _ in test_lib.TestFlowHelper(
        "ArtifactCollectorFlow", self.MockClient(),
        client_id=self.client_id,
        artifact_list=["WindowsInstalledSoftware"], token=self.token):
      pass

    urn = self.client_id.Add("info/software")
    fd = aff4.FACTORY.Open(urn, token=self.token)
    packages = fd.Get(fd.Schema.INSTALLED_PACKAGES)
    self.assertEquals(len(packages), 3)
    self.assertEquals(packages[0].description, "Google Chrome")

  def testFileArtifact(self):
    """Check we can run command based artifacts."""
    fd = aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw")
    fd.Set(fd.Schema.SYSTEM("Linux"))
    fd.Flush()

    # Update the artifact path to point to the test directory.
    TestFileArtifact.COLLECTORS[0].args["path"] = (
        os.path.join(self.base_path, "auth.log"))

    client_mock = test_lib.ActionMock("TransferBuffer", "StatFile",
                                      "HashBuffer", "ListDirectory")
    for _ in test_lib.TestFlowHelper(
        "ArtifactCollectorFlow", client_mock, client_id=self.client_id,
        artifact_list=["TestFileArtifact"], use_tsk=False, token=self.token):
      pass
    urn = self.client_id.Add("fs/os/").Add(self.base_path).Add("auth.log")
    fd = aff4.FACTORY.Open(urn, aff4_type="HashImage", token=self.token)


def main(argv):
  test_lib.main(argv)

if __name__ == "__main__":
  flags.StartMain(main)
