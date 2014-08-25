#!/usr/bin/env python
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
from grr.lib import data_store
from grr.lib import rdfvalue


DIGEST_ALGORITHM = hashlib.sha256  # pylint: disable=invalid-name
DIGEST_ALGORITHM_STR = "sha256"

SUPPORTED_PLATFORMS = ["windows", "linux", "darwin"]
SUPPORTED_ARCHICTECTURES = ["i386", "amd64"]


def UploadSignedConfigBlob(content, aff4_path, client_context=None,
                           limit=None, token=None):
  """Upload a signed blob into the datastore.

  Args:
    content: File content to upload.
    aff4_path: aff4 path to upload to.
    client_context: The configuration contexts to use.
    limit: The maximum size of the chunk to use.
    token: A security token.

  Raises:
    IOError: On failure to write.
  """
  if limit is None:
    limit = config_lib.CONFIG["Datastore.maximum_blob_size"]

  # Get the values of these parameters which apply to the client running on the
  # target platform.
  if client_context is None:
    # Default to the windows client.
    client_context = ["Platform:Windows", "Client"]

  config_lib.CONFIG.Validate(
      parameters="PrivateKeys.executable_signing_private_key")

  sig_key = config_lib.CONFIG.Get("PrivateKeys.executable_signing_private_key",
                                  context=client_context)

  ver_key = config_lib.CONFIG.Get("Client.executable_signing_public_key",
                                  context=client_context)
  with aff4.FACTORY.Create(
      aff4_path, "GRRSignedBlob", mode="w", token=token) as fd:

    for start_of_chunk in xrange(0, len(content), limit):
      chunk = content[start_of_chunk:start_of_chunk + limit]

      blob_rdf = rdfvalue.SignedBlob()
      blob_rdf.Sign(chunk, sig_key, ver_key, prompt=True)
      fd.Add(blob_rdf)

  logging.info("Uploaded to %s", fd.urn)


def UploadSignedDriverBlob(content, aff4_path=None, client_context=None,
                           install_request=None, token=None):
  """Upload a signed blob into the datastore.

  Args:
    content: Content of the driver file to upload.

    aff4_path: aff4 path to upload to. If not specified, we use the config to
      figure out where it goes.

    client_context: The configuration contexts to use.

    install_request: A DriverInstallRequest rdfvalue describing the installation
      parameters for this driver. If None these are read from the config.

    token: A security token.

  Returns:
    String containing path the file was written to.

  Raises:
    IOError: On failure to write.
  """
  sig_key = config_lib.CONFIG.Get("PrivateKeys.driver_signing_private_key",
                                  context=client_context)

  ver_key = config_lib.CONFIG.Get("Client.driver_signing_public_key",
                                  context=client_context)

  if aff4_path is None:
    aff4_paths = config_lib.CONFIG.Get("MemoryDriver.aff4_paths",
                                       context=client_context)
    if not aff4_paths:
      raise IOError("Could not determine driver location.")
    if len(aff4_paths) > 1:
      logging.info("Possible driver locations: %s", aff4_paths)
      raise IOError("Ambiguous driver location, please specify.")
    aff4_path = aff4_paths[0]

  blob_rdf = rdfvalue.SignedBlob()
  blob_rdf.Sign(content, sig_key, ver_key, prompt=True)

  with aff4.FACTORY.Create(
      aff4_path, "GRRMemoryDriver", mode="w", token=token) as fd:
    fd.Add(blob_rdf)

    if install_request is None:
      # Create install_request from the configuration.
      install_request = rdfvalue.DriverInstallTemplate(
          device_path=config_lib.CONFIG.Get(
              "MemoryDriver.device_path", context=client_context),
          driver_display_name=config_lib.CONFIG.Get(
              "MemoryDriver.driver_display_name", context=client_context),
          driver_name=config_lib.CONFIG.Get(
              "MemoryDriver.driver_service_name", context=client_context))

    fd.Set(fd.Schema.INSTALLATION(install_request))

  logging.info("Uploaded to %s", fd.urn)

  return fd.urn


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
  required_urns = set()

  try:
    # We weren't already initialized, create all directories we will need.
    for platform in SUPPORTED_PLATFORMS:
      for arch in SUPPORTED_ARCHICTECTURES:
        client_context = ["Platform:%s" % platform.title(),
                          "Arch:%s" % arch]

        aff4_paths = config_lib.CONFIG.Get("MemoryDriver.aff4_paths",
                                           context=client_context)
        for aff4_path in aff4_paths:
          required_urns.add(rdfvalue.RDFURN(aff4_path).Basename())

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
    builder_obj = builder_cls(context=context)
    try:
      return builder_obj.MakeDeployableBinary(template_path)
    except Exception as e:  # pylint: disable=broad-except
      print "Repacking template %s failed: %s" % (template_path, e)
  else:
    print "Template %s missing - will not repack." % template_path


def RepackAllBinaries(upload=False, debug_build=False):
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
    debug_build: Repack as a debug build.

  Returns:
    A list of output installers generated.
  """
  built = []

  base_context = ["ClientBuilder Context"]
  if debug_build:
    base_context += ["DebugClientBuild Context"]

  clients_to_repack = [
      (["Target:Windows", "Platform:Windows", "Arch:amd64"],
       build.WindowsClientDeployer),
      (["Target:Windows", "Platform:Windows", "Arch:i386"],
       build.WindowsClientDeployer),
      (["Target:Linux", "Platform:Linux", "Arch:amd64"],
       build.LinuxClientDeployer),
      (["Target:Linux", "Platform:Linux", "Arch:i386"],
       build.LinuxClientDeployer),
      (["Target:Linux", "Target:LinuxRpm", "Platform:Linux", "Arch:amd64"],
       build.CentosClientDeployer),
      (["Target:Darwin", "Platform:Darwin", "Arch:amd64"],
       build.DarwinClientDeployer)]

  msg = "Will repack the following clients "
  if debug_build:
    msg += "(debug build)"
  print msg + ":"
  print

  for context, deployer in clients_to_repack:
    context = base_context + context

    template_path = config_lib.CONFIG.Get("ClientBuilder.template_path",
                                          context=context)
    output_path = config_lib.CONFIG.Get("ClientBuilder.output_path",
                                        context=context)
    readable = (os.path.isfile(template_path) and
                os.access(template_path, os.R_OK))

    if not readable:
      readable_str = " (NOT READABLE)"
    else:
      readable_str = ""
    print "Repacking : " + template_path + readable_str
    print "To :        " + output_path
    print

  for context, deployer in clients_to_repack:
    context = base_context + context
    template_path = config_lib.CONFIG.Get("ClientBuilder.template_path",
                                          context=context)
    output_path = _RepackBinary(context, deployer)
    if output_path:
      print "%s repacked ok." % template_path
      built.append(output_path)
      if upload:
        dest = config_lib.CONFIG.Get("Executables.installer",
                                     context=context)
        UploadSignedConfigBlob(open(output_path).read(100*1024*1024),
                               dest, client_context=context)
    else:
      print "Failed to repack %s." % template_path

  return built


def RebuildIndex(urn, primary_attribute, indexed_attributes, token):
  """Rebuild the Label Indexes."""
  index_urn = rdfvalue.RDFURN(urn)

  logging.info("Deleting index %s", urn)
  data_store.DB.DeleteSubject(index_urn, sync=True)
  attribute_predicates = [a.predicate for a in indexed_attributes]
  filter_obj = data_store.DB.filter.HasPredicateFilter(
      primary_attribute.predicate)

  index = aff4.FACTORY.Create(index_urn, "AFF4Index",
                              token=token, mode="w")

  for row in data_store.DB.Query(attributes=attribute_predicates,
                                 filter_obj=filter_obj, limit=1000000):
    try:
      subject = row["subject"][0][0]
      urn = rdfvalue.RDFURN(subject)
    except ValueError:
      continue
    for attribute in indexed_attributes:
      value = row.get(attribute.predicate)
      if value:
        value = value[0][0]
      if value:
        logging.debug("Adding: %s %s %s", str(urn), attribute.predicate, value)
        index.Add(urn, attribute, value)
  logging.info("Flushing index %s", urn)
  index.Flush(sync=True)


def RebuildLabelIndexes(token):
  """Rebuild the Label Indexes."""
  RebuildIndex("/index/label",
               primary_attribute=aff4.AFF4Object.SchemaCls.LABEL,
               indexed_attributes=[aff4.AFF4Object.SchemaCls.LABEL],
               token=token)


def RebuildClientIndexes(token=None):
  """Rebuild the Client Indexes."""
  indexed_attributes = [a for a in aff4.VFSGRRClient.SchemaCls.ListAttributes()
                        if a.index]
  RebuildIndex("/index/client",
               primary_attribute=aff4.VFSGRRClient.SchemaCls.HOSTNAME,
               indexed_attributes=indexed_attributes, token=token)
