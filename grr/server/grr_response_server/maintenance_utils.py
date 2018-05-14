#!/usr/bin/env python
"""This file contains utility classes related to maintenance used by GRR."""

import getpass
import hashlib
import logging
import sys


from grr import config
from grr.lib.rdfvalues import crypto as rdf_crypto
from grr.lib.rdfvalues import events as rdf_events
from grr.server.grr_response_server import access_control
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import data_store
from grr.server.grr_response_server import events
from grr.server.grr_response_server import key_utils
from grr.server.grr_response_server.aff4_objects import collects
from grr.server.grr_response_server.aff4_objects import users

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
    password = getpass.getpass(prompt="Please enter password for user '%s': " %
                               username)
  fd.SetPassword(password)

  if labels:
    fd.AddLabels(set(labels), owner="GRR")

  fd.Close()

  EPrint("Added user %s." % username)

  events.Events.PublishEvent(
      "Audit",
      rdf_events.AuditEvent(
          user=token.username, action="USER_ADD", urn=user_urn),
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
      rdf_events.AuditEvent(
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
      rdf_events.AuditEvent(
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
