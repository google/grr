#!/usr/bin/env python
import base64
import contextlib
import glob
import os
import platform
import subprocess
import sys
import tempfile
import time
from absl import flags
from absl.testing import absltest
import psutil

from grr_response_core import config
from grr_response_core.lib import config_lib
from grr_response_core.lib import utils
from grr_response_core.lib.util import temp

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
Client.executable_signing_public_key: |
  -----BEGIN PUBLIC KEY-----
  MFwwDQYJKoZIhvcNAQEBBQADSwAwSAJBAMQpeVjrxmf6nPmsjHjULWhLmquSgTDK
  GpJgTFkTIAgX0Ih5lxoFB5TUjUfJFbBkSmKQPRA/IyuLBtCLQgwkTNkCAwEAAQ==
  -----END PUBLIC KEY-----
"""

PFX_BASE64_FILE = """
MIIKAgIBAzCCCb4GCSqGSIb3DQEHAaCCCa8EggmrMIIJpzCCBggGCSqGSIb3DQEHAaCCBfkEggX1
MIIF8TCCBe0GCyqGSIb3DQEMCgECoIIE/jCCBPowHAYKKoZIhvcNAQwBAzAOBAicmEFkRyeAugIC
B9AEggTYsyEsLwinKGCjXD0LS+hsIHoW+aehDwKCS8hZKvCxNGDxhSxRDnWc4jpEdLShWos4qLe3
DTEE1EenOoZZaYiA1Oj9pmhVyltFxWfbXNeiJzMW17Wiz5Ol/ABch9ZTAM7WLLAUHh2BThcJniQf
hGCyowcfbQB59GpgLGSo4trjHZEVAj51amIEopBs69mERGH0rglfEtjpYsmSNFpfL+TIXI6FEK04
7QaJ5/J3IA++IPj5QyJ/o0qQmiAOoGlAcyV/VFpoUZgMSOGIt/pb1oD1Soikqvm+/XnUK0fZbgr9
lBi9sPkywtONTls/7tqpe0u4al9dd6oRH+uwMdFv/xDr3viqpfL7FOVaIJzuEhGlUPzYbkNZ9wJv
lGv8dBEB0CsV2djJ/ztjoomtuWWStf2LaYH3ZXCTpDxtdp6sVbXdlKMkWjacoyJFA8k5xrP+2r2E
W23kGPsREun5/lUbqL+ojrHdfrELDWvc+CT49T5nSabSoVDi3fIctU92sACDg4wP5t3SWqHtA4O3
u+7e+CzR7IN/dA+Cm8vzbUlDGPvVY/iZ/NczZyzA6IYyIyOSgUZXwA7UDnCEUF/oFEj1vS6Ge0ry
gWBFrwJ0+fepI9rLF7383FoBbEfnEy7R0cb8CEbfZM7x3v5xmntgFUiObV3Ik+xqO3uw2oEoSUen
6INhmBT84LdBD5Q53+flNDPCiXd1Ua3vAfvK7nwpc5+Y7Xy04IrAp9BEjqIAoecrLFKg7ia/3CrP
EBxTB8LiuLqfp5rW7DB2kMCFNMWPFPok0TzTrq+yYf1zMVwB2N5d4cLa/NG6vYZAmiXAJFAZD0B1
QqEtPSO+Lu6IIlzen/7EJm3TyZrdEuUp9lLf4/cL/7EtPQvufpO7267OMR3NVqZHVnX8Ysv6MYLN
EdIZsUYtUK6tAsrWkrFYWXBUJigK0N0xzDjrys+EsLppWNV8fgs4/vzZps8KCQpbMHMICtUVVdNT
LS5sNIu27nz6w+1Cw1SmXFX5wTsJ0WoLqfs6qX6AsIcFczTEPP/BKkRxL0yzDZtdYeVyGqh5mqXp
B0+ZuQSNQd7K51idGbnPqseauoXkk+wBpTaoz71XTdOAYaWbGtqsVAW6TEcbCD+z4edBhqMmgP/s
y0ISJBxnqSxBbgBnYbTUo0CkF6eAXZmmevVsWi5/EFCRSahrb7BmVENjyCzOELgwBI318wJjWCV3
a2Z6jq1Z0XedQ0n8eK3v6Z0mfnVqpgXiaUBcwBaWqJDDZFU1ffSrcZeYsdgOayzvUKYL8D/P4HVi
OqmO9b1pJNCNIkBDdyvDDEu9Hxvl4TO+R6i26nT1zGSzEPFVGx2wO8VhX76s8LQ2zXa9PhC66m8R
LlVir9XhP/NtMBnBG/jkyOPnjMSK36z1kvJyRE5DyRNQG9UTrLpLUu5Lsd/7D1jdRgHNPz1tI/1Q
DiEZT854fiponY2sHbxRRSL/HZp/lAHtRMwBKuQTrSgmWre7bdirpGRqWHIRkJNxbi0j92Pc42w6
fZRbZ8T1xov3PxXhpvxBmzoowUH5P6p2k77QTEhEA9yzLvw9Bt9A3Szt1NBHZJBsC8kaTwzSNID1
Q+pDVukiEunwrdQUtySBozvSbcgYDlwG0XZy+l+c7+JQUIGHbNreFt8Qv7xzCJrFLDGB2zATBgkq
hkiG9w0BCRUxBgQEAQAAADBdBgkrBgEEAYI3EQExUB5OAE0AaQBjAHIAbwBzAG8AZgB0ACAAUwB0
AHIAbwBuAGcAIABDAHIAeQBwAHQAbwBnAHIAYQBwAGgAaQBjACAAUAByAG8AdgBpAGQAZQByMGUG
CSqGSIb3DQEJFDFYHlYAUAB2AGsAVABtAHAAOgBlADcANAA3ADQAYwA4AGUALQAyADMAZAA4AC0A
NABiADIAYgAtADkAYgA0ADkALQAwAGIAYgAxADkAYQA1ADgAYwA5AGMANTCCA5cGCSqGSIb3DQEH
BqCCA4gwggOEAgEAMIIDfQYJKoZIhvcNAQcBMBwGCiqGSIb3DQEMAQMwDgQIc1G7AHN/uHACAgfQ
gIIDUPKyu4vqnyoM3XPN3l9M/js/vj3jtWXid5+xq0C5+Bw/Up4g/hvWr15s6kNqCu6xbsnMt+RY
HAXpSxCbcfsajO/ATVMccs6LI2LYsCw6BYzG1lr9Ge5PIj2dzOcpzG0542hbXd8RP0p8hGG1uQBQ
T3tz/RYUnX6XaVk1GGpcraewMjGpUH93Rpv/EiDy8R26f348HeGeMYfJW4Vfwd6otn+bV0EeusL+
4NQLpo/4Fqzvm6OzikD2zMfJDrQBYuyThwY2GUI2lS3OLgSNj54GRrqakMTzHDaU5X0hpj2lC6OT
KWt3F3YFG6mnC1WX4sYU3NDOYPEbWhdqH2ElhBlI9rsmXZZIGyI6JAQyqD1bHpI+izCNpU+4GtSz
EB7bXQapU/6KEXa6NMhNDz/nVW7A4w0N8YWlcu2A5ez1PyUhQyP3NqqCrHZ9CbuDbzUzY0CLCgtG
EnDPW9uwsFb8uVvO/pLYTMlJIlDLs5oa6jQUO2ispQ1CXIXR3ejCoozjeSpO2M941fS1+OUkY2Np
IIjYlUGJPg/kAx0czUhuVgu7TZeyessazqxGN0kFx2irb01jKOqxg6D9eeChbMdg5hpEBSQHr0qK
R7aFnJFO+nlJqGSWw+2zGjUID14seEyVjRulAQR2SodfW1qkYx1T301nM6rgBMD7l9aHOnfFMNan
kTpBcB4gRQRKc/KvMV2BHvFhCnO/FPRlkdYUZPt8vZfZ/ZSSikMcJaPJDVNVRdqOGe+wQoUkUIyn
IpOPSnVbuCOtlAM8uTxNYH745IwNj2glIbH6Z8yZAjs3WxvSTzY4ZYwQ8uyB1SAjurDw97aclJX/
vq1Pz/qi8FkevQpct6fXZh5LoILFyomfA8zrwkweEiD+9r18Mo/tbRD+VoErs6PAvy9sG+j9ZWDq
EoYQ0pSFp0S05hSd/N0pSC9B/MNCra/dai7Nsy/EVW5zCw0v6/Kg3F0RVNFox3lf6EBSOKeFxpHM
uLLPGUwzVHz1DARb2WjGtL8YeMg6AhRKtd2JCzKbv72t5tVWDOPpgGJI9yWDMxvPMhkkyDFTBb72
dv4+VCW2N2Th8lPQyNhVa2CTKtVunpb25FQoqS8MmwZH2Qa7PhJF7eOcm8z2VKJq+NUTmrnjMDsw
HzAHBgUrDgMCGgQUJpevdDvPAv2dkZTD9cVJipEz4xYEFDyDMZN4vqzZx0xni5vWlA85OQyfAgIH
0A==
"""


# This is effectively an integration test.
# The test will build and run the installer, then perform checks veryfing
# that installation artifacts are present.
@absltest.skipIf(platform.system() != "Windows", "Windows only test")
class WindowsMsiTest(absltest.TestCase):

  def setUp(self):
    super().setUp()

    stack = contextlib.ExitStack()
    self.addCleanup(stack.close)

    self._tmp_dir = stack.enter_context(utils.TempDirectory())
    # This file can't be located in self._tmp_dir, since self._tmp_dir is
    # created with secure permissions and unaccessible to the fake fleetspeak
    # service.
    self._fake_fleetspeak_service_log_file = os.path.join(
        tempfile.gettempdir(), "fake_fleetspeak_service_log_file.txt")
    stack.callback(os.unlink, self._fake_fleetspeak_service_log_file)

  def _TmpPath(self, *args) -> str:
    return os.path.join(self._tmp_dir, *args)

  def _WixToolsPath(self) -> str:
    matches = glob.glob("c:\\Program Files*\\WiX Toolset*")
    if not matches:
      raise Exception("Couldn't find WiX Toolset.")
    return matches[0]

  def _SignToolPath(self) -> str:
    patterns = [
        "C:\\Program Files*\\Windows Kits\\*\\bin\\*\\x86\\signtool.exe",
        "C:\\Program Files*\\Windows Kits\\*\\bin\\*\\x64\\signtool.exe",
        "C:\\Program Files*\\Windows Kits\\*\\bin\\x86\\signtool.exe",
        "C:\\Program Files*\\Windows Kits\\*\\bin\\x64\\signtool.exe",
    ]
    for pattern in patterns:
      matches = glob.glob(pattern)
      if matches:
        return matches[0]
    raise Exception("Couldn't find signtool.exe")

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

  def _AssertServiceExists(self, name: str) -> None:
    subprocess.check_call(["sc", "query", name])

  def _AssertServiceDoesNotExist(self, name: str) -> None:
    with self.assertRaises(Exception):
      self._AssertServiceExists(name)

  def _RunFakeFleestpeakServiceCommand(self, command: str) -> None:
    service_name = config.CONFIG["Client.fleetspeak_service_name"]
    subprocess.check_call([
        sys.executable,
        "-m",
        "grr_response_client_builder.fake_fleetspeak_windows_service",
        f"--command={command}",
        f"--service_name={service_name}",
        f"--logfile={self._fake_fleetspeak_service_log_file}",
    ])

  def testInstaller(self):
    self._BuildTemplate()

    with self.subTest("fleetspeak enabled"):
      self._RunFakeFleestpeakServiceCommand("install")
      self._RunFakeFleestpeakServiceCommand("start")
      installer_path = self._RepackTemplate("fs_enabled", False)
      self._Install(installer_path)
      time.sleep(5)
      self._AssertProcessNotRunning("foo.exe")
      self._AssertProcessNotRunning("bar.exe")

      self._Uninstall(installer_path)
      self._RunFakeFleestpeakServiceCommand("stop")
      self._RunFakeFleestpeakServiceCommand("remove")
      with open(self._fake_fleetspeak_service_log_file, "r") as f:
        # There should be 4 stare/stop events logged by the fake service:
        # - 1x from this script.
        # - 1x from the CustomAction in grr.wxs
        # - 2x from ServiceControl in grr.wxs (on install, on uninstall).
        lines = [line.strip("\r\n") for line in f.readlines()]
        self.assertEqual(lines.count("start"), 4)
        self.assertEqual(lines.count("stop"), 4)

    with self.subTest("fleetspeak bundled"):
      installer_path = self._RepackTemplate("fs_bundled", True)
      self._Install(installer_path)
      self._WaitForProcess("fleetspeak-client.exe")
      self._WaitForProcess("bar.exe")
      self._AssertProcessNotRunning("foo.exe")

      self._Uninstall(installer_path)
      time.sleep(5)
      self._AssertProcessNotRunning("foo.exe")
      self._AssertProcessNotRunning("fleetspeak-client.exe")
      self._AssertProcessNotRunning("bar.exe")
      self._AssertServiceDoesNotExist(
          config.CONFIG["Client.fleetspeak_service_name"])

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
    ]
    subprocess.check_call(args)

  def _RepackTemplate(self, directory: str, fleetspeak_bundled: bool) -> str:
    fs_config = self._TmpPath("fs_config.txt")
    with open(fs_config, "w") as f:
      f.write(FLEETSPEAK_CONFIG)

    grr_secondary_config = self._TmpPath("grr_secondary_config.yaml")
    with open(grr_secondary_config, "w") as f:
      f.write(GRR_SECONDARY_CONFIG)

    pfx_file = self._TmpPath("cert.pfx")
    with open(pfx_file, "wb") as f:
      f.write(base64.b64decode(PFX_BASE64_FILE))

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
        "--sign",
        "-p",
        f"ClientBuilder.fleetspeak_bundled={fleetspeak_bundled}",
        "-p",
        f"ClientBuilder.fleetspeak_client_config={fs_config}",
        "-p",
        "ClientBuilder.output_extension=.msi",
        "-p",
        "ClientBuilder.console=true",
        "-p",
        "Client.name=bar",
        "-p",
        (
            "ClientBuilder.signtool_signing_cmd=%{"
            + self._SignToolPath()
            + " sign /v /f "
            + pfx_file
            + ' /t "http://timestamp.digicert.com" }'
        ),
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
    log_file = self._TmpPath("installer.log")
    args = [
        "msiexec",
    ] + list(args) + [
        "/l*V",
        log_file,
    ]
    try:
      subprocess.check_call(args)
    except:
      with open(log_file, "rb") as f:
        print(f.read().decode("utf-16"))
      raise


def setUpModule() -> None:
  with temp.AutoTempFilePath(suffix="yaml") as dummy_config_path:
    flags.FLAGS.config = dummy_config_path
    config_lib.ParseConfigCommandLine()


if __name__ == "__main__":
  absltest.main()
