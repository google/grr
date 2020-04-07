#!/usr/bin/env python
# Lint as: python3
"""A flow to collect eficheck output."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib.parsers import eficheck_parser
from grr_response_core.lib.rdfvalues import apple_firmware as rdf_apple_firmware
from grr_response_core.lib.util import compatibility
from grr_response_server import flow_base
from grr_response_server import server_stubs
from grr_response_server.flows.general import transfer


class CollectEfiHashes(flow_base.FlowBase):
  """Collect the hashes of the EFI volumes (MacOS only).

  This flow will run the eficheck binary on the host to extract a list of
  hashes for each volume on the flash. This flow provides a fast method
  to verify the system firmware. However, it does not provide further data
  should some hashes not match. In this case, please use the DumpEfiImage
  flow to retrieve the full firmware image and perform further investigation.
  """

  category = "/Collectors/"
  args_type = rdf_apple_firmware.EficheckFlowArgs
  result_types = (rdf_apple_firmware.EfiCollection,)
  behaviours = flow_base.BEHAVIOUR_BASIC

  def Start(self):
    """Call the CollectEfiHash client action."""
    self.CallClient(
        server_stubs.EficheckCollectHashes,
        cmd_path=self.args.cmd_path,
        next_state=compatibility.GetName(self.CollectedHashes))

  def CollectedHashes(self, responses):
    """Process the output of eficheck."""
    if not responses.success:
      raise flow_base.FlowError("Unable to collect the hashes: %s" %
                                responses.status)
    elif not responses:
      raise flow_base.FlowError("No hash collected.")
    else:
      for collect_response in responses:
        exec_response = collect_response.response
        if exec_response.exit_status:
          self.Log(exec_response.stdout)
          self.Log(exec_response.stderr)
          err_msg = ("Unable to collect the hashes. "
                     "Exit status = %d") % exec_response.exit_status
          raise flow_base.FlowError(err_msg)
        parser = eficheck_parser.EficheckCmdParser()
        for result in parser.Parse("eficheck", ["--show-hashes"],
                                   exec_response.stdout, exec_response.stderr,
                                   exec_response.exit_status, None):
          result.boot_rom_version = collect_response.boot_rom_version
          result.eficheck_version = collect_response.eficheck_version
          self.SendReply(result)


class DumpEfiImage(flow_base.FlowBase):
  """Dump the Flash Image (MacOS only).

  This flow will use eficheck to extract a copy of the flash image from the
  host. For a quick verification, consider using the CollectEfiHashes flow
  first.
  """

  category = "/Collectors/"
  args_type = rdf_apple_firmware.EficheckFlowArgs
  result_types = (rdf_apple_firmware.DumpEfiImageResponse,)
  behaviours = flow_base.BEHAVIOUR_BASIC

  def Start(self):
    """Call the DumpEficheckImage client action."""
    self.CallClient(
        server_stubs.EficheckDumpImage,
        cmd_path=self.args.cmd_path,
        next_state=compatibility.GetName(self.CollectedImage))

  def CollectedImage(self, responses):
    """Process the output of eficheck."""
    if not responses.success:
      raise flow_base.FlowError("Unable to create the flash image: %s" %
                                responses.status)
    for img_response in responses:
      exec_response = img_response.response
      if exec_response.stdout:
        self.Log("stdout = %s" % exec_response.stdout)
      if exec_response.stderr:
        self.Log("stderr = %s" % exec_response.stderr)
      if exec_response.exit_status:
        err_msg = ("Unable to dump the flash image. "
                   "Exit status = %d") % exec_response.exit_status
        raise flow_base.FlowError(err_msg)
      if img_response.path:
        image_path = img_response.path
        self.SendReply(img_response)
        self.CallFlow(
            transfer.MultiGetFile.__name__,
            pathspecs=[image_path],
            next_state=compatibility.GetName(self.DeleteTemporaryDir))

  def DeleteTemporaryDir(self, responses):
    """Remove the temporary image from the client."""
    if not responses.success:
      raise flow_base.FlowError("Unable to collect the flash image: %s" %
                                responses.status)
    response = responses.First()
    if not response.pathspec:
      raise flow_base.FlowError("Empty pathspec: %s" % str(response))

    # Clean up the temporary image from the client.
    self.CallClient(
        server_stubs.DeleteGRRTempFiles,
        response.pathspec,
        next_state=compatibility.GetName(self.TemporaryImageRemoved))

  def TemporaryImageRemoved(self, responses):
    """Verify that the temporary image has been removed successfully."""
    if not responses.success:
      raise flow_base.FlowError("Unable to delete the temporary flash image: "
                                "%s" % responses.status)
