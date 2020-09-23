#!/usr/bin/env python
# Lint as: python3
"""Execute eficheck on the client."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import glob
import os
import re

from grr_response_client import actions
from grr_response_client import client_utils_common
from grr_response_client.client_actions import tempfiles
from grr_response_core.lib.rdfvalues import apple_firmware as rdf_apple_firmware
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import paths as rdf_paths


class EficheckActionPlugin(actions.ActionPlugin):
  """Base class for Eficheck Client Action.

  Generic method(s) to be used by eficheck-related client actions.
  """

  def _GetVersion(self, args):
    """Call eficheck to find out its version."""
    res = client_utils_common.Execute(args.cmd_path, ["--version"])
    stdout, stderr, exit_status, time_used = res

    # If something went wrong, forward the output directly.
    if exit_status:
      binary_response = rdf_client_action.ExecuteBinaryResponse(
          stdout=stdout,
          stderr=stderr,
          exit_status=exit_status,
          time_used=time_used)
      self.SendReply(self.out_rdfvalues[0](response=binary_response))
      return
    return stdout


class EficheckCollectHashes(EficheckActionPlugin):
  """A client action to collect the EFI hashes via Apple eficheck."""

  in_rdfvalue = rdf_apple_firmware.EficheckConfig
  out_rdfvalues = [rdf_apple_firmware.CollectEfiHashesResponse]

  # The filename of the generated allowlist is passed as argument to the next
  # command. Make sure it matches a specific format to avoid any command
  # injection.
  _FILENAME_RE = re.compile(r"^[a-zA-Z0-9_.]+$")

  def Run(self, args):
    """Use eficheck to extract hash files in plaintext.

    Args:
      args: EficheckConfig
    Returns:
      CollectEfiHashesResponse

    This action executes eficheck multiple times:
      * First to get the binary version, using --version.
      * Then with the --generate-hashes option. This will create one or more
        .ealf files. Each file contains a binary representation of the hashes
        extracted from a part of the flash image (e.g, EFI, SEC).
      * For each file generated, we use the --show-hashes option to get a
        plaintext representation of the hashes. This raw output is sent to the
        server which will perform further parsing.
    """

    eficheck_version = self._GetVersion(args)
    if not eficheck_version:
      return False

    with tempfiles.TemporaryDirectory() as tmp_dir:
      res = client_utils_common.Execute(
          args.cmd_path, ["--generate-hashes"], cwd=tmp_dir.path)
      stdout, stderr, exit_status, time_used = res
      # If something went wrong, forward the output directly.
      if exit_status:
        binary_response = rdf_client_action.ExecuteBinaryResponse(
            stdout=stdout,
            stderr=stderr,
            exit_status=exit_status,
            time_used=time_used)
        self.SendReply(
            rdf_apple_firmware.CollectEfiHashesResponse(
                response=binary_response))
        return
      # Otherwise, convert all the files generated and forward the output.

      for filename in glob.glob(os.path.join(tmp_dir.path, "*.ealf")):
        cmd_args = ["--show-hashes", "-h", filename]
        # Get the boot rom version from the filename.
        basename = os.path.basename(filename)
        if not self._FILENAME_RE.match(basename):
          continue
        boot_rom_version, _ = os.path.splitext(basename)
        stdout, stderr, exit_status, time_used = client_utils_common.Execute(
            args.cmd_path, cmd_args, bypass_allowlist=True)

        binary_response = rdf_client_action.ExecuteBinaryResponse(
            stdout=stdout,
            stderr=stderr,
            exit_status=exit_status,
            time_used=time_used)
        self.SendReply(
            rdf_apple_firmware.CollectEfiHashesResponse(
                eficheck_version=eficheck_version,
                boot_rom_version=boot_rom_version,
                response=binary_response))

        tempfiles.DeleteGRRTempFile(filename)


class EficheckDumpImage(EficheckActionPlugin):
  """A client action to collect the full EFI image via Apple eficheck."""

  in_rdfvalue = rdf_apple_firmware.EficheckConfig
  out_rdfvalues = [rdf_apple_firmware.DumpEfiImageResponse]

  def Run(self, args):
    """Use eficheck to extract the binary image of the flash.

    Args:
      args: EficheckConfig
    Returns:
      DumpEfiImageResponse

    This action executes eficheck multiple times:
      * First to get the binary version, using --version.
      * Use --save -b firmware.bin to save the image.
    """

    eficheck_version = self._GetVersion(args)
    if not eficheck_version:
      return False

    with tempfiles.TemporaryDirectory(cleanup=False) as tmp_dir:
      res = client_utils_common.Execute(
          args.cmd_path, ["--save", "-b", "firmware.bin"], cwd=tmp_dir.path)
      stdout, stderr, exit_status, time_used = res
      binary_response = rdf_client_action.ExecuteBinaryResponse(
          stdout=stdout,
          stderr=stderr,
          exit_status=exit_status,
          time_used=time_used)
      response = rdf_apple_firmware.DumpEfiImageResponse(
          eficheck_version=eficheck_version, response=binary_response)
      if exit_status:
        tmp_dir.cleanup = True
      else:
        response.path = rdf_paths.PathSpec(
            path=os.path.join(tmp_dir.path, "firmware.bin"),
            pathtype=rdf_paths.PathSpec.PathType.TMPFILE)
      self.SendReply(response)
