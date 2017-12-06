#!/usr/bin/env python
"""This file contains utility classes related to maintenance used by GRR."""


import getpass
import hashlib
import logging
import os
import StringIO
import sys
import time
import zipfile


from grr import config
from grr.lib import utils
from grr.lib.builders import signing
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import crypto as rdf_crypto
from grr.server import access_control
from grr.server import aff4
from grr.server import data_store
from grr.server import events
from grr.server import key_utils
from grr.server.aff4_objects import collects
from grr.server.aff4_objects import users

DIGEST_ALGORITHM = hashlib.sha256  # pylint: disable=invalid-name
DIGEST_ALGORITHM_STR = "sha256"

SUPPORTED_PLATFORMS = ["windows", "linux", "darwin"]
SUPPORTED_ARCHITECTURES = ["i386", "amd64"]


class Error(Exception):
  """Base error class."""
  pass


class UserError(Error):
  pass


def EPrint(message):
  sys.stderr.write("%s\n" % message)


def UploadSignedConfigBlob(content,
                           aff4_path,
                           client_context=None,
                           limit=None,
                           token=None):
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
    limit = config.CONFIG["Datastore.maximum_blob_size"]

  # Get the values of these parameters which apply to the client running on the
  # target platform.
  if client_context is None:
    # Default to the windows client.
    client_context = ["Platform:Windows", "Client Context"]

  config.CONFIG.Validate(
      parameters="PrivateKeys.executable_signing_private_key")

  sig_key = config.CONFIG.Get(
      "PrivateKeys.executable_signing_private_key", context=client_context)

  ver_key = config.CONFIG.Get(
      "Client.executable_signing_public_key", context=client_context)

  urn = collects.GRRSignedBlob.NewFromContent(
      content,
      aff4_path,
      chunk_size=limit,
      token=token,
      private_key=sig_key,
      public_key=ver_key)

  logging.info("Uploaded to %s", urn)


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
  if components[0] == "executables" and components[1] in SUPPORTED_PLATFORMS:
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
      required_urns.add("aff4:/config/executables/%s/agentupdates" % platform)
      required_urns.add("aff4:/config/executables/%s/installers" % platform)

    existing_urns = [x["urn"] for x in aff4.FACTORY.Stat(list(required_urns))]

    missing_urns = required_urns - set(existing_urns)

    # One by one is not optimal but we have to do it only once per urn.
    for urn in missing_urns:
      aff4.FACTORY.Create(urn, aff4.AFF4Volume, token=token).Flush()

  except access_control.UnauthorizedAccess:
    logging.info("User is not admin, cannot check configuration tree.")
    return


def _SignWindowsComponent(component, output_filename):
  print "Enter passphrase for code signing cert:"
  passwd = getpass.getpass()
  cert = config.CONFIG.Get("ClientBuilder.windows_signing_cert")
  key = config.CONFIG.Get("ClientBuilder.windows_signing_key")
  app_name = config.CONFIG.Get("ClientBuilder.windows_signing_application_name")

  signer = signing.WindowsOsslsigncodeCodeSigner(cert, key, passwd, app_name)
  with utils.TempDirectory() as temp_dir:
    zip_file = zipfile.ZipFile(StringIO.StringIO(component.raw_data))
    zip_file.extractall(temp_dir)

    new_data = StringIO.StringIO()
    new_zipfile = zipfile.ZipFile(
        new_data, mode="w", compression=zipfile.ZIP_DEFLATED)

    for root, _, files in os.walk(temp_dir):
      for basename in files:
        basename = basename.lstrip("\\/")
        filename = os.path.join(root, basename)

        # The relative filename to the root of the zip file.
        relative_filename = filename[len(temp_dir):].lstrip("/")

        extension = os.path.splitext(filename)[1].lower()
        if extension in [".sys", ".exe", ".dll", ".pyd"]:
          out_filename = filename + ".signed"
          signer.SignFile(filename, out_filename=out_filename)
          new_zipfile.write(out_filename, arcname=relative_filename)
        else:
          new_zipfile.write(filename, arcname=relative_filename)

    # Flush the Zip file.
    new_zipfile.close()
    component.raw_data = new_data.getvalue()

    with open(output_filename, "wb") as out_fd:
      out_fd.write(component.SerializeToString())


def SignComponentContent(component_filename, output_filename):
  """Some OSs require the contents of a component to be signed as well.

  Specifically this action unzips the component and authenticode signs all
  binaries. The component is then repacked.

  Args:
    component_filename: The filename of the component.
    output_filename: We write the new signed component here.

  Raises:
    RuntimeError: If called for any other OS than windows.
  """
  component = rdf_client.ClientComponent.FromSerializedString(
      open(component_filename, "rb").read())
  EPrint("Opened component %s." % component.summary.name)

  if component.build_system.system == "Windows":
    _SignWindowsComponent(component, output_filename)
    return

  raise RuntimeError("Component signing is not implemented for OS %s." %
                     component.build_system.system)


def SignComponent(component_filename, overwrite=False, token=None):
  """Sign and upload the component to the data store."""

  EPrint("Signing and uploading component %s" % component_filename)
  serialized_component = open(component_filename, "rb").read()
  component = rdf_client.ClientComponent.FromSerializedString(
      serialized_component)
  EPrint("Opened component %s." % component.summary.name)

  client_context = [
      "Platform:%s" % component.build_system.system.title(),
      "Arch:%s" % component.build_system.arch
  ]

  sig_key = config.CONFIG.Get(
      "PrivateKeys.executable_signing_private_key", context=client_context)

  ver_key = config.CONFIG.Get(
      "Client.executable_signing_public_key", context=client_context)

  # For each platform specific component, we have a component summary object
  # which contains high level information in common to all components of this
  # specific version.
  component_urn = config.CONFIG.Get("Config.aff4_root").Add("components").Add(
      "%s_%s" % (component.summary.name, component.summary.version))

  component_fd = aff4.FACTORY.Create(
      component_urn, collects.ComponentObject, mode="rw", token=token)

  component_summary = component_fd.Get(component_fd.Schema.COMPONENT)
  if overwrite or component_summary is None:
    EPrint("Storing component summary at %s" % component_urn)

    component_summary = component.summary
    component_summary.seed = "%x%x" % (time.time(), utils.PRNG.GetULong())
    component_summary.url = ("/static/components/" + component_summary.seed)

    component_fd.Set(component_fd.Schema.COMPONENT, component_summary)
    component_fd.Close()

  else:
    EPrint("Using seed from stored component summary at %s" % component_urn)
    component.summary.url = component_summary.url
    component.summary.seed = component_summary.seed

  # Sign the component, encrypt it and store it at the static aff4 location.
  signed_component = rdf_crypto.SignedBlob()
  signed_component.Sign(component.SerializeToString(), sig_key, ver_key)

  aff4_urn = aff4.FACTORY.GetComponentRoot().Add(component.summary.seed).Add(
      component.build_system.signature())

  EPrint("Storing signed component at %s" % aff4_urn)
  with aff4.FACTORY.Create(aff4_urn, aff4.AFF4MemoryStream, token=token) as fd:
    fd.Write(
        component_summary.cipher.Encrypt(signed_component.SerializeToString()))

  return component


def SignAllComponents(overwrite=False, token=None):

  components_dir = config.CONFIG["ClientBuilder.components_dir"]
  for root, _, files in os.walk(components_dir):
    for f in files:
      if os.path.splitext(f)[1] != ".bin":
        continue

      component_filename = os.path.join(root, f)
      try:
        SignComponent(component_filename, overwrite=overwrite, token=token)
      except Exception as e:  # pylint: disable=broad-except
        EPrint("Could not sign component %s: %s" % (component_filename, e))


def ListComponents(token=None):

  component_root = aff4.FACTORY.Open("aff4:/config/components", token=token)
  for component in component_root.OpenChildren():
    if not isinstance(component, collects.ComponentObject):
      continue

    desc = component.Get(component.Schema.COMPONENT)
    if not desc:
      continue

    EPrint("* Component %s (version %s)" % (desc.name, desc.version))

    versions = []
    base_urn = "aff4:/web%s" % desc.url
    for urn, _, _ in data_store.DB.ScanAttribute(base_urn, "aff4:type"):
      versions.append(urn.split("/")[-1])

    if not versions:
      EPrint("No platform signatures available.")
    else:
      EPrint("Available platform signatures:")
      for v in sorted(versions):
        EPrint("- %s" % v)


def ShowUser(username, token=None):
  """Implementation of the show_user command."""
  if username is None:
    fd = aff4.FACTORY.Open("aff4:/users", token=token)
    for user in fd.OpenChildren():
      if isinstance(user, users.GRRUser):
        EPrint(user.Describe())
  else:
    user = aff4.FACTORY.Open("aff4:/users/%s" % username, token=token)
    if isinstance(user, users.GRRUser):
      EPrint(user.Describe())
    else:
      EPrint("User %s not found" % username)


def AddUser(username, password=None, labels=None, token=None):
  """Implementation of the add_user command."""
  if not username:
    raise UserError("Cannot add user: User must have a non-empty name")

  token = data_store.GetDefaultToken(token)
  user_urn = "aff4:/users/%s" % username
  try:
    if aff4.FACTORY.Open(user_urn, users.GRRUser, token=token):
      raise UserError("Cannot add user %s: User already exists." % username)
  except aff4.InstantiationError:
    pass

  fd = aff4.FACTORY.Create(user_urn, users.GRRUser, mode="rw", token=token)
  # Note this accepts blank passwords as valid.
  if password is None:
    password = getpass.getpass(
        prompt="Please enter password for user '%s': " % username)
  fd.SetPassword(password)

  if labels:
    fd.AddLabels(set(labels), owner="GRR")

  fd.Close()

  EPrint("Added user %s." % username)

  events.Events.PublishEvent(
      "Audit",
      events.AuditEvent(user=token.username, action="USER_ADD", urn=user_urn),
      token=token)


def UpdateUser(username,
               password,
               add_labels=None,
               delete_labels=None,
               token=None):
  """Implementation of the update_user command."""
  if not username:
    raise UserError("User must have a non-empty name")

  token = data_store.GetDefaultToken(token)

  user_urn = "aff4:/users/%s" % username
  try:
    fd = aff4.FACTORY.Open(user_urn, users.GRRUser, mode="rw", token=token)
  except aff4.InstantiationError:
    raise UserError("User %s does not exist." % username)

  # Note this accepts blank passwords as valid.
  if password:
    if not isinstance(password, basestring):
      password = getpass.getpass(
          prompt="Please enter password for user '%s': " % username)
    fd.SetPassword(password)

  # Use sets to dedup input.
  current_labels = set()

  # Build a list of existing labels.
  for label in fd.GetLabels():
    current_labels.add(label.name)

  # Build a list of labels to be added.
  expanded_add_labels = set()
  if add_labels:
    for label in add_labels:
      # Split up any space or comma separated labels in the list.
      labels = label.split(",")
      expanded_add_labels.update(labels)

  # Build a list of labels to be removed.
  expanded_delete_labels = set()
  if delete_labels:
    for label in delete_labels:
      # Split up any space or comma separated labels in the list.
      labels = label.split(",")
      expanded_delete_labels.update(labels)

  # Set subtraction to remove labels being added and deleted at the same time.
  clean_add_labels = expanded_add_labels - expanded_delete_labels
  clean_del_labels = expanded_delete_labels - expanded_add_labels

  # Create final list using difference to only add new labels.
  final_add_labels = clean_add_labels - current_labels

  # Create final list using intersection to only remove existing labels.
  final_del_labels = clean_del_labels & current_labels

  if final_add_labels:
    fd.AddLabels(final_add_labels, owner="GRR")

  if final_del_labels:
    fd.RemoveLabels(final_del_labels, owner="GRR")

  fd.Close()

  EPrint("Updated user %s" % username)

  ShowUser(username, token=token)

  events.Events.PublishEvent(
      "Audit",
      events.AuditEvent(
          user=token.username, action="USER_UPDATE", urn=user_urn),
      token=token)


def DeleteUser(username, token=None):
  """Deletes an existing user."""
  if not username:
    raise UserError("User must have a non-empty name")

  token = data_store.GetDefaultToken(token)
  user_urn = "aff4:/users/%s" % username
  try:
    aff4.FACTORY.Open(user_urn, users.GRRUser, token=token)
  except aff4.InstantiationError:
    EPrint("User %s not found." % username)
    return

  aff4.FACTORY.Delete(user_urn, token=token)
  EPrint("User %s has been deleted." % username)

  events.Events.PublishEvent(
      "Audit",
      events.AuditEvent(
          user=token.username, action="USER_DELETE", urn=user_urn),
      token=token)


def RotateServerKey(cn=u"grr", keylength=4096):
  """This function creates and installs a new server key.

  Note that

  - Clients might experience intermittent connection problems after
    the server keys rotated.

  - It's not possible to go back to an earlier key. Clients that see a
    new certificate will remember the cert's serial number and refuse
    to accept any certificate with a smaller serial number from that
    point on.

  Args:
    cn: The common name for the server to use.
    keylength: Length in bits for the new server key.
  Raises:
    ValueError: There is no CA cert in the config. Probably the server
                still needs to be initialized.
  """
  ca_certificate = config.CONFIG["CA.certificate"]
  ca_private_key = config.CONFIG["PrivateKeys.ca_key"]

  if not ca_certificate or not ca_private_key:
    raise ValueError("No existing CA certificate found.")

  # Check the current certificate serial number
  existing_cert = config.CONFIG["Frontend.certificate"]

  serial_number = existing_cert.GetSerialNumber() + 1
  EPrint("Generating new server key (%d bits, cn '%s', serial # %d)" %
         (keylength, cn, serial_number))

  server_private_key = rdf_crypto.RSAPrivateKey.GenerateKey(bits=keylength)
  server_cert = key_utils.MakeCASignedCert(
      unicode(cn),
      server_private_key,
      ca_certificate,
      ca_private_key,
      serial_number=serial_number)

  EPrint("Updating configuration.")
  config.CONFIG.Set("Frontend.certificate", server_cert)
  config.CONFIG.Set("PrivateKeys.server_key", server_private_key.AsPEM())
  config.CONFIG.Write()

  EPrint("Server key rotated, please restart the GRR Frontends.")
