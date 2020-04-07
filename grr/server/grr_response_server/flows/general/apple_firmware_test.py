#!/usr/bin/env python
# Lint as: python3
"""Tests for eficheck flows."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl import app

from grr_response_client.client_actions import standard
from grr_response_client.client_actions import tempfiles
from grr_response_core.lib.rdfvalues import apple_firmware as rdf_apple_firmware
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_server.flows.general import apple_firmware
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class CollectEfiHashesMock(action_mocks.ActionMock):

  def EficheckCollectHashes(self, args):
    stdout = (
        b"01:00:00:00190048:00003c5f:"
        b"4d37da42-3a0c-4eda-b9eb-bc0e1db4713b:"
        b"03a3fb4ca9b65be048b04e44ab5d1dd8e1af1ca9d1f53a5e96e8ae0125a02bb2")
    exec_response = rdf_client_action.ExecuteBinaryResponse(
        stdout=stdout, exit_status=0)
    response = rdf_apple_firmware.CollectEfiHashesResponse(
        eficheck_version="1.9.6",
        boot_rom_version="MBP101.B00",
        response=exec_response)
    return [response]


class CollectEfiHashesFailMock(CollectEfiHashesMock):

  def EficheckCollectHashes(self, args):
    stderr = b"Unable to collect the hashes"
    exec_response = rdf_client_action.ExecuteBinaryResponse(
        stderr=stderr, exit_status=-1)
    response = rdf_apple_firmware.CollectEfiHashesResponse(
        response=exec_response)
    return [response]


class CollectEfiNoHashesMock(CollectEfiHashesMock):

  def EficheckCollectHashes(self, args):
    return []


class CollectEfiHashesTest(flow_test_lib.FlowTestsBaseclass):

  def setUp(self):
    super(CollectEfiHashesTest, self).setUp()
    self.client_id = self.SetupClient(0, system="Darwin")

  def testCollectHashes(self):
    """Tests Collect hashes."""
    client_mock = CollectEfiHashesMock()

    flow_id = flow_test_lib.TestFlowHelper(
        apple_firmware.CollectEfiHashes.__name__,
        client_mock,
        client_id=self.client_id,
        token=self.token)

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)

    self.assertLen(results, 1)
    efi, = results
    self.assertEqual(efi.boot_rom_version, "MBP101.B00")
    self.assertEqual(efi.eficheck_version, "1.9.6")
    self.assertLen(efi.entries, 1)
    self.assertEqual(efi.entries[0].guid,
                     "4d37da42-3a0c-4eda-b9eb-bc0e1db4713b")

  def testCollectHashesError(self):
    """Tests fail collection."""
    client_mock = CollectEfiHashesFailMock()

    with self.assertRaises(RuntimeError) as err:
      with test_lib.SuppressLogs():
        flow_test_lib.TestFlowHelper(
            apple_firmware.CollectEfiHashes.__name__,
            client_mock,
            client_id=self.client_id,
            token=self.token)

    self.assertIn("Unable to collect the hashes.", str(err.exception))

  def testCollectNoHashesError(self):
    """Tests exception when no results is returned."""
    client_mock = CollectEfiNoHashesMock()

    with self.assertRaises(RuntimeError) as err:
      with test_lib.SuppressLogs():
        flow_test_lib.TestFlowHelper(
            apple_firmware.CollectEfiHashes.__name__,
            client_mock,
            client_id=self.client_id,
            token=self.token)

    self.assertIn("No hash collected.", str(err.exception))


class DumpEfiImageMock(action_mocks.ActionMock):

  def __init__(self, *args, **kwargs):
    super().__init__(standard.HashBuffer, standard.HashFile,
                     standard.GetFileStat, standard.TransferBuffer,
                     tempfiles.DeleteGRRTempFiles)

  def EficheckDumpImage(self, args):
    flash_fd, flash_path = tempfiles.CreateGRRTempFileVFS()
    flash_fd.close()
    stdout = "Image successfully written to firmware.bin."
    exec_response = rdf_client_action.ExecuteBinaryResponse(
        stdout=stdout.encode("utf-8"), exit_status=0)
    response = rdf_apple_firmware.DumpEfiImageResponse(
        eficheck_version="1.9.6", response=exec_response, path=flash_path)
    return [response]


class DumpEfiImageFailMock(action_mocks.ActionMock):

  def EficheckDumpImage(self, args):
    stderr = "Unable to connect to the kernel driver."
    exec_response = rdf_client_action.ExecuteBinaryResponse(
        stderr=stderr.encode("utf-8"), exit_status=1)
    response = rdf_apple_firmware.DumpEfiImageResponse(
        eficheck_version="1.9.6", response=exec_response)
    return [response]


class DumpEfiImageTest(flow_test_lib.FlowTestsBaseclass):

  def setUp(self):
    super(DumpEfiImageTest, self).setUp()
    self.client_id = self.SetupClient(0, system="Darwin")

  def testDumpImage(self):
    """Tests EFI dump."""
    client_mock = DumpEfiImageMock()

    flow_id = flow_test_lib.TestFlowHelper(
        apple_firmware.DumpEfiImage.__name__,
        client_mock,
        client_id=self.client_id,
        token=self.token)

    # Check the output of the flow.
    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)

    self.assertLen(results, 1)
    dump_response, = results
    self.assertEqual(dump_response.eficheck_version, "1.9.6")
    self.assertEqual(dump_response.response.exit_status, 0)

  def testDumpImageFail(self):
    """Tests EFI Failed dump."""
    client_mock = DumpEfiImageFailMock()

    with self.assertRaises(RuntimeError) as err:
      with test_lib.SuppressLogs():
        flow_test_lib.TestFlowHelper(
            apple_firmware.DumpEfiImage.__name__,
            client_mock,
            client_id=self.client_id,
            token=self.token)

    self.assertIn("Unable to dump the flash image", str(err.exception))


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
