#!/usr/bin/env python
"""Windows client repackers."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import io
import logging
import os
import re
import struct
import zipfile

from google.protobuf import text_format

from fleetspeak.src.client.daemonservice.proto.fleetspeak_daemonservice import config_pb2 as fs_config_pb2
from fleetspeak.src.common.proto.fleetspeak import system_pb2 as fs_system_pb2

from grr_response_client_builder import build
from grr_response_client_builder import build_helpers

from grr_response_core import config
from grr_response_core.lib import utils
from grr_response_core.lib.util import temp


def _CopyFileInZip(from_zip, from_name, to_zip, to_name=None):
  """Read a file from a ZipFile and write it to a new ZipFile."""
  data = from_zip.read(from_name)
  if to_name is None:
    to_name = from_name
  to_zip.writestr(to_name, data)


class WindowsClientRepacker(build.ClientRepacker):
  """Repackages windows installers."""

  def _ValidateEndConfig(self, config_str, errors_fatal=True):
    """Windows specific config validations."""
    config_obj = config.CONFIG.MakeNewConfig()
    with temp.AutoTempFilePath(suffix=".yaml") as filepath:
      with io.open(filepath, "w") as fd:
        fd.write(config_str)

      config_obj.Initialize(filename=filepath, process_includes=False)

    errors = []

    install_dir = config_obj["Client.install_path"]
    for path in config_obj["Client.tempdir_roots"]:
      if path.startswith("/"):
        errors.append(
            "Client.tempdir_root %s starts with /, probably has Unix path." %
            path)
      if not path.startswith(install_dir):
        errors.append(
            "Client.tempdir_root %s is not inside the install_dir %s, this is "
            "a security risk" % ((path, install_dir)))

    if config_obj.Get("Logging.path").startswith("/"):
      errors.append("Logging.path starts with /, probably has Unix path. %s" %
                    config_obj["Logging.path"])

    if "Windows\\" in config_obj.GetRaw("Logging.path"):
      errors.append("Windows in Logging.path, you probably want "
                    "%(WINDIR|env) instead")

    if not config_obj["Client.binary_name"].endswith(".exe"):
      errors.append("Missing .exe extension on binary_name %s" %
                    config_obj["Client.binary_name"])

    if not config_obj["Nanny.binary"].endswith(".exe"):
      errors.append("Missing .exe extension on nanny_binary")

    if errors_fatal and errors:
      for error in errors:
        logging.error("Build Config Error: %s", error)
      raise RuntimeError("Bad configuration generated. Terminating.")
    else:
      return errors

  def _GenerateFleetspeakServiceConfig(self, zip_file):
    orig_fs_config_path = config.CONFIG.Get(
        "ClientBuilder.fleetspeak_config_path", context=self.context)
    final_fs_config_fname = config.CONFIG.Get(
        "Client.fleetspeak_unsigned_config_fname", context=self.context)
    if orig_fs_config_path.endswith(".in"):
      logging.info("Interpolating %s", orig_fs_config_path)
      logging.warning("Backslashes will be naively re-escaped after "
                      "interpolation. If this is not desired, use a Fleetspeak "
                      "config file without the '.in' extension.")
      with utils.TempDirectory() as temp_dir:
        temp_fs_config_path = os.path.join(temp_dir, final_fs_config_fname)
        with io.open(orig_fs_config_path, "r") as source:
          with io.open(temp_fs_config_path, "w") as dest:
            interpolated = config.CONFIG.InterpolateValue(
                source.read(), context=self.context)
            dest.write(re.sub(r"\\", r"\\\\", interpolated))
        self._ValidateFleetspeakServiceConfig(temp_fs_config_path)
        zip_file.write(temp_fs_config_path, final_fs_config_fname)
    else:
      self._ValidateFleetspeakServiceConfig(orig_fs_config_path)
      zip_file.write(orig_fs_config_path, final_fs_config_fname)

  def _ValidateFleetspeakServiceConfig(self, config_path):
    """Validates a Fleetspeak service config.

    Checks that the given file is a valid TextFormat representation of
    a Fleetspeak service config proto.

    Args:
      config_path: Path to the config file.

    Raises:
      BuildError: If the config is not valid.
    """
    with open(config_path, "rb") as f:
      parsed_config = text_format.Parse(
          f.read(),
          fs_system_pb2.ClientServiceConfig(),
          descriptor_pool=fs_config_pb2.DESCRIPTOR.pool)
      if parsed_config.factory != "Daemon":
        raise build.BuildError(
            "Fleetspeak config does not have the expected factory type.")
      daemon_cfg = fs_config_pb2.Config()
      parsed_config.config.Unpack(daemon_cfg)
      if not daemon_cfg.argv:
        raise build.BuildError(
            "Fleetspeak daemon service config does not specify command line "
            "args.")

  def _MakeSelfExtractingZip(self, payload_data, output_path):
    """Repack the installer into the payload.

    Args:
      payload_data: data payload for zip file
      output_path: filename for the zip output

    Raises:
      RuntimeError: if the ClientBuilder.unzipsfx_stub doesn't require admin.
    Returns:
      output_path: filename string of zip output file
    """
    context = self.context + ["Client Context"]

    src_zip = zipfile.ZipFile(io.BytesIO(payload_data), mode="r")
    zip_data = io.BytesIO()
    output_zip = zipfile.ZipFile(
        zip_data, mode="w", compression=zipfile.ZIP_DEFLATED)

    config_file_name = config.CONFIG.Get(
        "ClientBuilder.config_filename", context=context)
    # Copy the rest of the files from the package to the new zip.
    for template_file in src_zip.namelist():
      if template_file != config_file_name:
        # Avoid writing the config file twice if we're repacking a binary that
        # has already been run through deployment. We write it in the next step,
        # so no need to copy over from the original here.
        _CopyFileInZip(src_zip, template_file, output_zip)

    client_config_content = build_helpers.GetClientConfig(context)
    self._ValidateEndConfig(client_config_content)

    output_zip.writestr(
        config_file_name,
        client_config_content.encode("utf-8"),  # pytype: disable=attribute-error
        compress_type=zipfile.ZIP_STORED)

    # The zip file comment is used by the self extractor to run the installation
    # script. Comment has to be `bytes` object because `zipfile` module is not
    # smart enough to properly handle `unicode` objects.
    output_zip.comment = b"$AUTORUN$>%s" % config.CONFIG.Get(
        "ClientBuilder.autorun_command_line", context=context).encode("utf-8")

    output_zip.close()

    utils.EnsureDirExists(os.path.dirname(output_path))
    with io.open(output_path, "wb") as fd:
      # First write the installer stub
      stub_data = io.BytesIO()
      unzipsfx_stub = config.CONFIG.Get(
          "ClientBuilder.unzipsfx_stub", context=context)
      stub_raw = io.open(unzipsfx_stub, "rb").read()

      # Check stub has been compiled with the requireAdministrator manifest.
      if b"level=\"requireAdministrator" not in stub_raw:
        raise RuntimeError("Bad unzip binary in use. Not compiled with the"
                           "requireAdministrator manifest option.")

      stub_data.write(stub_raw)

      # If in verbose mode, modify the unzip bins PE header to run in console
      # mode for easier debugging.
      build_helpers.SetPeSubsystem(
          stub_data,
          console=config.CONFIG.Get("ClientBuilder.console", context=context))

      # Now patch up the .rsrc section to contain the payload.
      end_of_file = zip_data.tell() + stub_data.tell()

      # This is the IMAGE_SECTION_HEADER.Name which is also the start of
      # IMAGE_SECTION_HEADER.
      offset_to_rsrc = stub_data.getvalue().find(b".rsrc")

      # IMAGE_SECTION_HEADER.PointerToRawData is a 32 bit int.
      stub_data.seek(offset_to_rsrc + 20)
      start_of_rsrc_section = struct.unpack("<I", stub_data.read(4))[0]

      # Adjust IMAGE_SECTION_HEADER.SizeOfRawData to span from the old start to
      # the end of file.
      stub_data.seek(offset_to_rsrc + 16)
      stub_data.write(struct.pack("<I", end_of_file - start_of_rsrc_section))

      # Concatenate stub and zip file.
      out_data = io.BytesIO()
      out_data.write(stub_data.getvalue())
      out_data.write(zip_data.getvalue())

      # Then write the actual output file.
      fd.write(out_data.getvalue())

    if self.signer:
      self.signer.SignFile(output_path)

    logging.info("Deployable binary generated at %s", output_path)

    return output_path

  def MakeDeployableBinary(self, template_path, output_path):
    """Repackage the template zip with the installer."""
    context = self.context + ["Client Context"]

    zip_data = io.BytesIO()
    output_zip = zipfile.ZipFile(
        zip_data, mode="w", compression=zipfile.ZIP_DEFLATED)

    z_template = zipfile.ZipFile(open(template_path, "rb"))

    # Track which files we've copied already.
    completed_files = [
        "grr-client.exe", "GRRservice.exe", "dbg_grr-client.exe",
        "dbg_GRRservice.exe"
    ]

    # Change the name of the main binary to the configured name.
    client_bin_name = config.CONFIG.Get("Client.binary_name", context=context)

    console_build = config.CONFIG.Get("ClientBuilder.console", context=context)
    if console_build:
      client_filename = "dbg_grr-client.exe"
      service_filename = "dbg_GRRservice.exe"
    else:
      client_filename = "grr-client.exe"
      service_filename = "GRRservice.exe"

    bin_name = z_template.getinfo(client_filename)
    output_zip.writestr(client_bin_name, z_template.read(bin_name))

    _CopyFileInZip(z_template, "grr-client.exe.manifest", output_zip,
                   "%s.manifest" % client_bin_name)
    completed_files.append("grr-client.exe.manifest")

    # Change the name of the service binary to the configured name.
    service_template = z_template.getinfo(service_filename)

    if config.CONFIG["Client.fleetspeak_enabled"]:
      self._GenerateFleetspeakServiceConfig(output_zip)
    else:
      # Only copy the nanny if Fleetspeak is disabled.
      service_bin_name = config.CONFIG.Get(
          "Nanny.service_binary_name", context=context)
      output_zip.writestr(service_bin_name, z_template.read(service_template))

    if self.signed_template:
      # If the template libs were already signed we can skip signing
      build_helpers.CreateNewZipWithSignedLibs(
          z_template, output_zip, ignore_files=completed_files)
    else:
      build_helpers.CreateNewZipWithSignedLibs(
          z_template,
          output_zip,
          ignore_files=completed_files,
          signer=self.signer)
    output_zip.close()

    return self._MakeSelfExtractingZip(zip_data.getvalue(), output_path)
