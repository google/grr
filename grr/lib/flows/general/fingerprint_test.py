#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Tests for the Fingerprint flow."""



import os

from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import flags
from grr.lib import flow
from grr.lib import test_lib
from grr.lib.aff4_objects import aff4_grr
from grr.lib.flows.general import fingerprint as flows_fingerprint
from grr.lib.rdfvalues import paths as rdf_paths


class TestFingerprintFlow(test_lib.FlowTestsBaseclass):
  """Test the Fingerprint flow."""

  def testFingerprintPresence(self):
    path = os.path.join(self.base_path, "winexec_img.dd")
    pathspec = rdf_paths.PathSpec(pathtype=rdf_paths.PathSpec.PathType.OS,
                                  path=path)

    pathspec.Append(path="/winpmem-amd64.sys",
                    pathtype=rdf_paths.PathSpec.PathType.TSK)

    client_mock = action_mocks.ActionMock("FingerprintFile")
    with test_lib.Instrument(flow.GRRFlow, "SendReply") as send_reply:
      for _ in test_lib.TestFlowHelper("FingerprintFile",
                                       client_mock,
                                       token=self.token,
                                       client_id=self.client_id,
                                       pathspec=pathspec):
        pass

      self.assertEqual(len(send_reply.args), 1)
      for _, reply in send_reply.args:
        self.assertTrue(isinstance(reply,
                                   flows_fingerprint.FingerprintFileResult))
        self.assertTrue(str(reply.file_urn).endswith(
            "test_data/winexec_img.dd/winpmem-amd64.sys"))

        self.assertEqual(
            str(reply.hash_entry.sha256),
            "40ac571d6d85d669a9a19d498d9f926525481430056ff65746f"
            "baf36bee8855f")
        self.assertEqual(
            str(reply.hash_entry.sha1),
            "6e17df1a1020a152f2bf4445d1004b192ae8e42d")
        self.assertEqual(
            str(reply.hash_entry.md5), "12be1109aa3d3b46c9398972af2008e1")

    urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(pathspec, self.client_id)
    fd = aff4.FACTORY.Open(urn, token=self.token)
    self.assertEqual(fd.__class__, aff4_grr.VFSFile)

    hash_obj = fd.Get(fd.Schema.HASH)
    self.assertEqual(hash_obj.pecoff_sha1,
                     "1f32fa4eedfba023653c094143d90999f6b9bc4f")

    self.assertEqual(hash_obj.signed_data[0].revision, 512)


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
