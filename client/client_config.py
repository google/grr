#!/usr/bin/env python

# Copyright 2010 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Various configuration related things."""



import os
import platform
import re

from M2Crypto import BIO
from M2Crypto import RSA
from M2Crypto import X509

from grr.client import conf as flags

from grr.lib import registry

# Windows service name
SERVICE_NAME = "GRR Monitor"
SERVICE_DISPLAY_NAME = "GRR Enterprise System Monitor"

# Client Information
GRR_CLIENT_NAME = "GRR Monitor"
# Version 0.1
GRR_CLIENT_VERSION = 1
GRR_CLIENT_REVISION = 0
GRR_CLIENT_BUILDTIME = "unknown"

# MacOS-X launchctl plist
LAUNCHCTL_PLIST = "/System/Library/LaunchDaemons/com.google.code.grrd.plist"

# The key we store our config in windows
REGISTRY_KEY = "HKEY_LOCAL_MACHINE\\SOFTWARE\\GRR"

LOCATION = "http://grr-server/control"

# Config file for linux/osx
CONFIG_FILE = "/etc/grr.ini"

# Nanny control
NANNY_LOGFILE = "/var/run/grr.log"
UNRESPONSIVE_KILL_PERIOD = 60

# The GRR client performs some proxy detection. However, it cannot
# handle proxy autoconfig settings. Here, additional proxy servers
# can be given as a list of strings of the form "http://server:port/".
PROXY_SERVERS = []

try:
  LOGFILE_PATH = "%s/system32/logfiles/GRRlog.txt" % os.environ["WINDIR"]
except KeyError:
  LOGFILE_PATH = "/tmp/GRRlog.txt"

# This is the version of this client.
NETWORK_API = 3

# Certificates: Separate CA certificates are stored here. The --camode argument
# in the client sets which one of these the client trusts. The default
# of --camode is set by the CAMODE value below.
# This provides enforced isolation of the environments.

CAMODE = "TEST"

CACERTS = {
    "TEST": """
-----BEGIN CERTIFICATE-----
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
ImKbVCFIXYW/vECT2R/v
-----END CERTIFICATE-----
"""
}

# Key for controlling code execution.
EXEC_SIGNING_KEY = {
    "TEST": """
-----BEGIN PUBLIC KEY-----
MFwwDQYJKoZIhvcNAQEBBQADSwAwSAJBAMQpeVjrxmf6nPmsjHjULWhLmquSgTDK
GpJgTFkTIAgX0Ih5lxoFB5TUjUfJFbBkSmKQPRA/IyuLBtCLQgwkTNkCAwEAAQ==
-----END PUBLIC KEY-----
"""}

# Key for controlling driver execution.
DRIVER_SIGNING_KEY = {
    "TEST": """
-----BEGIN PUBLIC KEY-----
MFwwDQYJKoZIhvcNAQEBBQADSwAwSAJBALnfFW1FffeKPs5PLUhFOSkNrr9TDCOD
QAI3WluLh0sW7/ro93eoIZ0FbipnTpzGkPpriONbSOXmxWNTo0b9ma8CAwEAAQ==
-----END PUBLIC KEY-----
"""}

# The following allows the certificates to be updated using the command line or
# config file.
flags.DEFINE_string("cacert", None,
                    help="The CA certificate we use to verify the server.")

flags.DEFINE_string("exec_signing_key", None,
                    help="The certificate we use to verify executables.")

flags.DEFINE_string("driver_signing_key", None,
                    help="The certificate we use to verify drivers.")


if platform.system() == "Windows":
  flags.DEFINE_string("regpath", REGISTRY_KEY,
                      "A registry path for storing GRR configuration.")
else:
  flags.DEFINE_string("config", CONFIG_FILE,
                      "Comma separated list of grr configuration files.")

FLAGS = flags.FLAGS


class ConfigInit(registry.InitHook):
  """Update configuration from command line flags."""

  def CheckCert(self, cert_string, label):
    """Check certificates for validity and try to fix mangled cert strings."""

    start_marker = "-----BEGIN CERTIFICATE-----"
    end_marker = "-----END CERTIFICATE-----"

    try:
      X509.load_cert_string(cert_string)
      return cert_string
    except X509.X509Error:
      pass

    # If we arrive here, the certificate might be given as a one line string.
    if (start_marker in cert_string and
        end_marker in cert_string):

      start_cert = cert_string.find(start_marker) + len(start_marker)
      end_cert = cert_string.find(end_marker)
      cert = cert_string[start_cert:end_cert]

      parts = [start_marker]
      parts.append(re.sub("(.{64})", r"\1\n", cert).rstrip())
      parts.append(end_marker)

      new_cert_string = "\n".join(parts)
      try:
        X509.load_cert_string(new_cert_string)
        return new_cert_string
      except X509.X509Error:
        pass

    # Cannot fix this cert, giving up.
    raise RuntimeError("Invalid %s certificate." % label)

  def CheckKey(self, key_string, label):
    """Check keys for validity and try to fix mangled key strings."""

    start_marker = "-----BEGIN PUBLIC KEY-----"
    end_marker = "-----END PUBLIC KEY-----"

    try:
      bio = BIO.MemoryBuffer(key_string)
      RSA.load_pub_key_bio(bio)
      return key_string
    except RSA.RSAError:
      pass

    # If we arrive here, the key might be given as a one line string.
    if (start_marker in key_string and
        end_marker in key_string):

      start_key = key_string.find(start_marker) + len(start_marker)
      end_key = key_string.find(end_marker)
      key = key_string[start_key:end_key]

      parts = [start_marker]
      parts.append(re.sub("(.{64})", r"\1\n", key).rstrip())
      parts.append(end_marker)

      new_key_string = "\n".join(parts)
      try:
        bio = BIO.MemoryBuffer(new_key_string)
        RSA.load_pub_key_bio(bio)
        return new_key_string
      except RSA.RSAError:
        pass

    # Cannot fix this key, giving up.
    raise RuntimeError("Invalid %s key." % label)

  def RunOnce(self):
    """Inits and validates the certificates."""

    try:
      camode = FLAGS.camode.upper()
    except AttributeError:
      # UI does not use certificates/keys so we return.
      return

    # Allow updating of the certificates from the command line.
    if FLAGS.cacert is not None:
      CACERTS[camode] = FLAGS.cacert

    if FLAGS.exec_signing_key is not None:
      EXEC_SIGNING_KEY[camode] = FLAGS.exec_signing_key

    if FLAGS.driver_signing_key is not None:
      DRIVER_SIGNING_KEY[camode] = FLAGS.driver_signing_key

   # Check for validity.
    CACERTS[camode] = self.CheckCert(
        CACERTS[camode], "CA")
    EXEC_SIGNING_KEY[camode] = self.CheckKey(
        EXEC_SIGNING_KEY[camode], "exec signing")
    DRIVER_SIGNING_KEY[camode] = self.CheckKey(
        DRIVER_SIGNING_KEY[camode], "driver signing")
