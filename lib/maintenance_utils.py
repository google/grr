#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.

"""This file contains utility classes related to maintenance used by GRR."""



import hashlib
import os
import socket

import ipaddr

import logging

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import build
from grr.lib import config_lib
from grr.lib import rdfvalue

DIGEST_ALGORITHM = hashlib.sha256
DIGEST_ALGORITHM_STR = "sha256"

SUPPORTED_PLATFORMS = ["windows", "linux", "darwin"]


config_lib.DEFINE_string("MemoryDriver.driver_service_name",
                         "Pmem",
                         "The SCCM service name for the driver.")

config_lib.DEFINE_string("MemoryDriver.driver_display_name",
                         "%(Client.name) Pmem",
                         "The SCCM display name for the driver.")


def UploadSignedConfigBlob(content, aff4_path, client_context=None, token=None):
  """Upload a signed blob into the datastore.

  Args:
    content: File content to upload.
    aff4_path: aff4 path to upload to.
    client_context: The configuration contexts to use.
    token: A security token.

  Raises:
    IOError: On failure to write.
  """
  # Get the values of these parameters which apply to the client running on the
  # trarget platform.
  if client_context is None:
    # Default to the windows client.
    client_context = ["Platform:Windows", "Client"]

  config_lib.CONFIG.Validate(
      parameters="PrivateKeys.executable_signing_private_key")

  sig_key = config_lib.CONFIG.Get("PrivateKeys.executable_signing_private_key",
                                  context=client_context)

  ver_key = config_lib.CONFIG.Get("Client.executable_signing_public_key",
                                  context=client_context)

  blob_rdf = rdfvalue.SignedBlob()
  blob_rdf.Sign(content, sig_key, ver_key, prompt=True)

  fd = aff4.FACTORY.Create(aff4_path, "GRRSignedBlob", mode="w", token=token)
  fd.Set(fd.Schema.BINARY(blob_rdf))
  fd.Close()

  logging.info("Uploaded to %s", fd.urn)


def UploadSignedDriverBlob(content, file_name, platform, arch="i386",
                           aff4_path="/config/drivers/{platform}/memory/"
                           "{file_name}", install_request=None, token=None):
  """Upload a signed blob into the datastore.

  Args:
    content: Content of the driver file to upload.
    file_name: Unique name for file to upload.
    platform: Which client platform to sign for. This determines which signing
        keys to use. If you don't have per platform signing keys. The standard
        keys will be used.
    arch: The architecture of the platform (e.g. i386, amd64).
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
  # We create a client context to emulate the specific client's
  # environment. This allows us to configure different values for the same
  # parameters for different client architectures in the same configuration
  # file.
  client_context = ["Platform:%s" % platform.title(),
                    "Arch:%s" % arch,
                    "Client"]
  sig_key = config_lib.CONFIG.Get("PrivateKeys.driver_signing_private_key",
                                  context=client_context)

  ver_key = config_lib.CONFIG.Get("Client.driver_signing_public_key",
                                  context=client_context)

  blob_rdf = rdfvalue.SignedBlob()
  blob_rdf.Sign(content, sig_key, ver_key, prompt=True)
  aff4_path = rdfvalue.RDFURN(aff4_path.format(platform=platform.lower(),
                                               file_name=file_name))
  fd = aff4.FACTORY.Create(aff4_path, "GRRMemoryDriver", mode="w", token=token)
  fd.Set(fd.Schema.BINARY(blob_rdf))

  if not install_request:
    installer = rdfvalue.DriverInstallTemplate()
    # Create install_request from the configuration.
    installer.device_path = config_lib.CONFIG.Get(
        "MemoryDriver.device_path", context=client_context)

    if platform == "Windows":
      installer.driver_display_name = config_lib.CONFIG.Get(
          "MemoryDriver.driver_display_name", context=client_context)

      installer.driver_name = config_lib.CONFIG.Get(
          "MemoryDriver.driver_service_name", context=client_context)

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

  except access_control.UnauthorizedAccess:
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


def _RepackBinary(context, builder_cls):
  # Check for the presence of the template.
  template_path = config_lib.CONFIG.Get("ClientBuilder.template_path",
                                        context=context)

  if os.path.exists(template_path):
    builder = builder_cls(context=context)
    try:
      return builder.MakeDeployableBinary(template_path)
    except Exception as e:  # pylint: disable=broad-except
      print "Repacking template %s failed: %s" % (template_path, e)
  else:
    print "Template %s missing - will not repack." % template_path


def RepackAllBinaries(upload=False):
  """Repack binaries based on the configuration.

  NOTE: The configuration file specifies the location of the binaries
  templates. These usually depend on the client version which is also specified
  in the configuration file. This simple function simply runs through all the
  supported architectures looking for available templates for the configured
  client version, architecture and operating system.

  We do not repack all the binaries that are found in the template directories,
  only the ones that are valid for the current configuration. It is not an error
  to have a template missing, we simply ignore it and move on.

  Args:
    upload: If specified we also upload the repacked binary into the datastore.

  Returns:
    A list of output installers generated.
  """
  built = []

  base_context = ["ClientBuilder Context"]
  for context, builder in (
      (["Target:Windows", "Platform:Windows", "Arch:amd64"],
       build.WindowsClientBuilder),
      (["Target:Windows", "Platform:Windows", "Arch:i386"],
       build.WindowsClientBuilder),
      (["Target:Linux", "Platform:Linux", "Arch:amd64"],
       build.LinuxClientBuilder),
      (["Target:Darwin", "Platform:Darwin", "Arch:amd64"],
       build.DarwinClientBuilder)):

    context = base_context + context
    output_path = _RepackBinary(context, builder)
    if output_path:
      built.append(output_path)
      if upload:
        dest = config_lib.CONFIG.Get("Executables.installer",
                                     context=context)
        UploadSignedConfigBlob(open(output_path).read(100*1024*1024),
                               dest, client_context=context)

  return built
