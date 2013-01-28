#!/usr/bin/env python
# Copyright 2012 Google Inc.
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


"""This file contains utility classes related to maintenance used by GRR."""



import hashlib
import socket

import ipaddr

import logging

from grr.lib import aff4
from grr.lib import data_store
from grr.lib import rdfvalue

DIGEST_ALGORITHM = hashlib.sha256
DIGEST_ALGORITHM_STR = "sha256"

SUPPORTED_PLATFORMS = ["windows", "linux", "darwin"]


def UploadSignedConfigBlob(
    content, file_name, config, platform,
    aff4_path="/config/executables/{platform}/installers/{file_name}",
    token=None):
  """Upload a signed blob into the datastore.

  Args:
    content: File content to upload.
    file_name: Unique name for file to upload.
    config: A ConfigManager object which contains the signing keys.
    platform: Which client platform to sign for. This determines which signing
        keys to use.
    aff4_path: aff4 path to upload to. Note this can handle platform and
        file_name interpolation.
    token: A security token.

  Returns:
    String containing path the file was written to.

  Raises:
    IOError: On failure to write.
  """
  section = "ClientSigningKeys%s" % platform.title()
  sig_key = config["%s.executable_signing_private_key" % section]
  ver_key = config["%s.executable_signing_public_key" % section]
  blob_rdf = rdfvalue.SignedBlob()
  blob_rdf.Sign(content, sig_key, ver_key, prompt=True)
  aff4_path = rdfvalue.RDFURN(aff4_path.format(platform=platform.lower(),
                                               file_name=file_name))
  fd = aff4.FACTORY.Create(aff4_path, "GRRSignedBlob", mode="w", token=token)
  fd.Set(fd.Schema.BINARY(blob_rdf))
  fd.Close()
  logging.info("Uploaded to %s", fd.urn)
  return str(fd.urn)


def UploadSignedDriverBlob(content, file_name, config, platform,
                           aff4_path="/config/drivers/{platform}/memory/"
                           "{file_name}", install_request=None, token=None):
  """Upload a signed blob into the datastore.

  Args:
    content: Content of the driver file to upload.
    file_name: Unique name for file to upload.
    config: A ConfigManager object which contains the signing keys.
    platform: Which client platform to sign for. This determines which signing
        keys to use. If you don't have per platform signing keys. The standard
        keys will be used.
    aff4_path: aff4 path to upload to. Note this can handle platform and
        file_name interpolation.
    install_request: A DriverInstallRequest rdfvalue describing the installation
      parameters for this driver. If None these are read from the config.
    token: A security token.

  Returns:
    String containing path the file was written to.

  Raises:
    IOError: On failure to write.
  """
  sig_key = config["ClientSigningKeys%s.driver_signing_private_key" %
                   platform.title()]
  ver_key = config["ClientSigningKeys%s.driver_signing_public_key" %
                   platform.title()]
  blob_rdf = rdfvalue.SignedBlob()
  blob_rdf.Sign(content, sig_key, ver_key, prompt=True)
  aff4_path = rdfvalue.RDFURN(aff4_path.format(platform=platform.lower(),
                                               file_name=file_name))
  fd = aff4.FACTORY.Create(aff4_path, "GRRMemoryDriver", mode="w", token=token)
  fd.Set(fd.Schema.BINARY(blob_rdf))
  if not install_request:
    installer = rdfvalue.DriverInstallTemplate()
    # Create install_request from the configuration.
    section = "MemoryDriver%s" % platform.title()
    installer.device_path = config["%s.device_path" % section]
    installer.write_path = config["%s.install_write_path" % section]
    if platform == "Windows":
      installer.driver_display_name = config["%s.driver_display_name" % section]
      installer.driver_name = config["%s.driver_service_name" % section]
  else:
    installer = install_request

  fd.Set(fd.Schema.INSTALLATION(installer))
  fd.Close()
  logging.info("Uploaded to %s", fd.urn)
  return str(fd.urn)


def GetConfigBinaryPathType(aff4_path):
  """Take an aff4_path and return type or None.

  Args:
    aff4_path: An RDFURN containing the path to the binary.

  Returns:
    None if the path is not supported for binary upload, otherwise a type.
  """
  if not aff4_path.Path().startswith("/config"):
    return
  components = aff4_path.RelativeName("aff4:/config").split("/")
  if components[0] == "drivers" and components[1] in SUPPORTED_PLATFORMS:
    return "GRRMemoryDriver"
  elif components[0] == "executables" and components[1] in SUPPORTED_PLATFORMS:
    return "GRRSignedBlob"
  elif components[0] == "python_hacks":
    return "GRRSignedBlob"
  else:
    return


def CreateBinaryConfigPaths(token=None):
  """Create the paths required for binary configs."""
  required_dirs = set(["drivers", "executables", "python_hacks"])
  required_urns = set()

  try:
    for req_dir in required_dirs:
      required_urns.add("aff4:/config/%s" % req_dir)

    # We weren't already initialized, create all directories.
    for platform in SUPPORTED_PLATFORMS:
      required_urns.add("aff4:/config/drivers/%s/memory" % platform)
      required_urns.add("aff4:/config/executables/%s/agentupdates" % platform)
      required_urns.add("aff4:/config/executables/%s/installers" % platform)

    existing_urns = [x["urn"] for x in aff4.FACTORY.Stat(list(required_urns),
                                                         token=token)]

    missing_urns = required_urns - set(existing_urns)

    # One by one is not optimal but we have to do it only once per urn.
    for urn in missing_urns:
      aff4.FACTORY.Create(urn, "AFF4Volume", token=token).Flush()

  except data_store.UnauthorizedAccess:
    logging.info("User is not admin, cannot check configuration tree.")
    return


def GuessPublicHostname():
  """Attempt to guess a public host name for this machine."""
  local_hostname = socket.gethostname()
  local_ip = socket.gethostbyname(local_hostname)
  if not ipaddr.IPAddress(local_ip).is_private:
    # The host name resolves and is not private.
    return local_hostname
  else:
    # Our local host does not resolve attempt to retreive it externally.
    raise OSError("Could not detect public hostname for this machine")



