#!/usr/bin/env python
import contextlib
import glob
import os
import platform
import subprocess
import sys
import time
from absl.testing import absltest
import psutil

from grr_response_core.lib import utils

FLEETSPEAK_CONFIG = """
trusted_certs: "-----BEGIN CERTIFICATE-----\\n"
  "MIIBaDCCAQ6gAwIBAgIRAMh5eU+BV10PgrXCIHyRF9QwCgYIKoZIzj0EAwIwIzEh\\n"
  "MB8GA1UEAxMYRmxlZXRzcGVhayBGbGVldHNwZWFrIENBMB4XDTIwMTIxMTE3MTMy\\n"
  "M1oXDTMwMTIwOTE3MTMyM1owIzEhMB8GA1UEAxMYRmxlZXRzcGVhayBGbGVldHNw\\n"
  "ZWFrIENBMFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEfm7Y3Nn9iOltYPVDw32Q\\n"
  "oWZCo5NB9uRNodzB21+c1vyzFTOv061g9xEfo3JXP2lKDqYqgFaH2/07K57kCDys\\n"
  "WKMjMCEwDgYDVR0PAQH/BAQDAgKEMA8GA1UdEwEB/wQFMAMBAf8wCgYIKoZIzj0E\\n"
  "AwIDSAAwRQIhANQPZ725sitHJftnJdvNZCow/35ircFSVOaWkpr8ukPPAiAbJg3b\\n"
  "EdvBx6IAv9ItS+ebbfytekgNIyoWD2uM31MEFA==\\n"
  "-----END CERTIFICATE-----\\n"
server: "127.0.0.1:4443"
client_label: ""
registry_handler: <
  configuration_key: "HKEY_LOCAL_MACHINE\\\\SOFTWARE\\\\FleetspeakClient"
>
"""

GRR_SECONDARY_CONFIG = """
Client.server_urls: ["http://localhost:8000/"]
Client.executable_signing_public_key: |
  -----BEGIN PUBLIC KEY-----
  MFwwDQYJKoZIhvcNAQEBBQADSwAwSAJBAMQpeVjrxmf6nPmsjHjULWhLmquSgTDK
  GpJgTFkTIAgX0Ih5lxoFB5TUjUfJFbBkSmKQPRA/IyuLBtCLQgwkTNkCAwEAAQ==
  -----END PUBLIC KEY-----
CA.certificate: |
  -----BEGIN CERTIFICATE-----
  MIIC2zCCAcOgAwIBAgIBATANBgkqhkiG9w0BAQsFADAgMREwDwYDVQQDDAhncnJf
  dGVzdDELMAkGA1UEBhMCVVMwHhcNMjEwMTE5MjAwNjQ1WhcNMzEwMTE4MjAwNjQ1
  WjAOMQwwCgYDVQQDDANncnIwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIB
  AQDCYKqomwMxTPsipJtYpzxIbb0okr+NdKZipqLVjqt+LTtHBFuMwRxtX2ZG7l+6
  EiadZjh4tk+PNk9Lq5ZFfGjpJ/mLLpPXkdcZnjToseCTYdM0dsnQ0q1hIA6chRwU
  mvTU81rlexNsslthjGUHfNdeWwIPtfvEW9/GtV8f3eeIo7e5h4Nco97N2bj6alPZ
  5ASThtCUK0GAm9qfTwi+UZaLNZlUPbj7OSdbc/5ieosF9CAuAXNHAqQY5IfkLYun
  w+Ma6oDYbfSB0EV450tJATwNprNLgg9fyABz3sDEFWJ7+H0eRQ0nOQLCHHvhduEP
  hdX6LzsaUH0WBiqgyq2prCenAgMBAAGjMjAwMA8GA1UdEwEB/wQFMAMBAf8wHQYD
  VR0OBBYEFH2xv8xuBK6Vxarntzu5WwqowKbxMA0GCSqGSIb3DQEBCwUAA4IBAQB1
  JKXAglrc4ZYY04ZRyodpKzVXext7grpbRpen1+NigObYQb1ZGuaYXvpr8HiB6yGm
  wx8BUrO0n5wzJi7ZRktwrBWdTseYRX6ztHF0+2pBnzkCF06zM597wwv49aUaySVV
  BfHLR7TqF7QrQNeUMMjprADM3yNuuUGhLtlDZszgUTMLowxK3WM0A4niKhLaeGRb
  E+i02f9gjMQBdhkFxZ/r3LhgXvwtb7xy+1JuvJlTmWpPWDivLScODtTq+/US6lnw
  d7yf65zi20ufC5fh4oxc2stFLYlI0+MvTfj9f0sJbfJLSYj+8/jvRub0nAJQEyl7
  6H+n8+lmRu0iE0dFPB+z
  -----END CERTIFICATE-----
"""


# This is effectively an integration test.
# The test will build and run the installer, then perform checks veryfing
# that installation artifacts are present.
@absltest.skipIf(platform.system() != "Windows", "Windows only test")
class WindowsMsiTest(absltest.TestCase):

  def setUp(self):
    super(WindowsMsiTest, self).setUp()

    stack = contextlib.ExitStack()
    self.addCleanup(stack.close)

    self._tmp_dir = stack.enter_context(utils.TempDirectory())

  def _TmpPath(self, *args) -> str:
    return os.path.join(self._tmp_dir, *args)

  def _WixToolsPath(self) -> str:
    for program_files in ["C:\\Program Files", "C:\\Program Files (x86)"]:
      for candidate in os.listdir(program_files):
        if candidate.startswith("WiX Toolset"):
          return os.path.join(program_files, candidate)
    raise Exception("Couldn't find WiX Toolset.")

  def _WaitForProcess(self, name: str) -> None:
    for _ in range(5):
      processes = sorted([p.name() for p in psutil.process_iter()])
      if name in processes:
        return
      time.sleep(1)
    self.assertIn(name, processes)

  def _AssertProcessNotRunning(self, name: str) -> None:
    processes = sorted([p.name() for p in psutil.process_iter()])
    self.assertNotIn(name, processes)

  def testInstaller(self):
    self._BuildTemplate()

    installer_path = self._RepackTemplate("legacy", False, False)
    self._Install(installer_path)
    self._WaitForProcess("foo.exe")
    self._WaitForProcess("bar.exe")

    self._Uninstall(installer_path)
    time.sleep(5)
    self._AssertProcessNotRunning("foo.exe")
    self._AssertProcessNotRunning("bar.exe")

    installer_path = self._RepackTemplate("fs_enabled", True, False)
    self._Install(installer_path)
    time.sleep(5)
    self._AssertProcessNotRunning("foo.exe")
    self._AssertProcessNotRunning("bar.exe")

    self._Uninstall(installer_path)

    installer_path = self._RepackTemplate("fs_bundled", True, True)
    self._Install(installer_path)
    self._WaitForProcess("fleetspeak-client.exe")
    self._WaitForProcess("bar.exe")
    self._AssertProcessNotRunning("foo.exe")

    self._Uninstall(installer_path)
    time.sleep(5)
    self._AssertProcessNotRunning("foo.exe")
    self._AssertProcessNotRunning("fleetspeak-client.exe")
    self._AssertProcessNotRunning("bar.exe")

  def _BuildTemplate(self) -> None:
    wix_tools_path = self._WixToolsPath()
    args = [
        sys.executable,
        "-m",
        "grr_response_client_builder.client_build",
        "build",
        "--output",
        self._TmpPath(),
        "-p",
        "ClientBuilder.wix_tools_path=%{" + wix_tools_path + "}",
        "-p",
        "ClientBuilder.build_msi=true",
        "-p",
        "ClientBuilder.use_prebuilt_nanny=true",
    ]
    subprocess.check_call(args)

  def _RepackTemplate(self, directory: str, fleetspeak_enabled: bool,
                      fleetspeak_bundled: bool) -> str:
    fs_config = self._TmpPath("fs_config.txt")
    with open(fs_config, "w") as f:
      f.write(FLEETSPEAK_CONFIG)

    grr_secondary_config = self._TmpPath("grr_secondary_config.yaml")
    with open(grr_secondary_config, "w") as f:
      f.write(GRR_SECONDARY_CONFIG)

    os.mkdir(self._TmpPath(directory))

    args = [
        sys.executable,
        "-m",
        "grr_response_client_builder.client_build",
        "--verbose",
        "--secondary_configs",
        grr_secondary_config,
        "repack",
        "--template",
        glob.glob(self._TmpPath("*.zip"))[0],
        "-p",
        f"Client.fleetspeak_enabled={fleetspeak_enabled}",
        "-p",
        f"ClientBuilder.fleetspeak_bundled={fleetspeak_bundled}",
        "-p",
        f"ClientBuilder.fleetspeak_client_config={fs_config}",
        "-p",
        "ClientBuilder.output_extension=.msi",
        "-p",
        "ClientBuilder.console=true",
        "-p",
        "Nanny.service_binary_name=foo.exe",
        "-p",
        "Client.name=bar",
        "--output_dir",
        self._TmpPath(directory),
    ]
    subprocess.check_call(args)

    return glob.glob(self._TmpPath(directory, "*.msi"))[0]

  def _Install(self, path: str) -> None:
    self._MsiExec("/i", path)

  def _Uninstall(self, path: str) -> None:
    self._MsiExec("/q", "/x", path)

  def _MsiExec(self, *args: str) -> None:
    log_file = self._TmpPath("insaller.log")
    args = [
        "msiexec",
    ] + list(args) + [
        "/l*",
        log_file,
    ]
    try:
      subprocess.check_call(args)
    except:
      with open(log_file, "rb") as f:
        print(f.read().decode("utf-16"))
      raise


if __name__ == "__main__":
  absltest.main()
