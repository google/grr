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

from grr.client import client_keys
from grr.lib import registry

flags.DEFINE_string("camode", client_keys.CAMODE,
                    "The mode to run in, test,production,staging. This "
                    "affects the CA certificate we trust.")


# Default Windows nanny service name. Override using --service_name flag.
SERVICE_NAME = "GRR Monitor"

# Client Information
GRR_CLIENT_NAME = "GRR Monitor"

# Version 0.1
GRR_CLIENT_VERSION = 1
GRR_CLIENT_REVISION = 0
GRR_CLIENT_BUILDTIME = "unknown"

# MacOS-X launchctl plist
LAUNCHCTL_PLIST = "/Library/LaunchDaemons/com.google.code.grrd.plist"

# The key we store our config in windows
REGISTRY_KEY = "HKEY_LOCAL_MACHINE\\SOFTWARE\\GRR"

LOCATION = "http://grr-server/control"

# Config file for linux/osx
CONFIG_FILE = "/etc/grr.ini"

# Nanny control
NANNY_LOGFILE = "/var/run/grr.log"
NANNY_STATUS_FILE = "/var/run/grr.status"
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

# Import the keys from the client_key file.
CAMODE = client_keys.CAMODE
CACERTS = client_keys.CACERTS
EXEC_SIGNING_KEY = client_keys.EXEC_SIGNING_KEY
DRIVER_SIGNING_KEY = client_keys.DRIVER_SIGNING_KEY

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
  flags.DEFINE_string("client_config", CONFIG_FILE,
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
