#!/usr/bin/env python
"""Util for modifying the GRR server configuration."""


import argparse
import ConfigParser
import getpass
import json
import os
import re
# importing readline enables the raw_input calls to have history etc.
import readline  # pylint: disable=unused-import
import sys
import urlparse


# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=g-bad-import-order,unused-import

from grr.lib import aff4
from grr.lib import artifact
from grr.lib import artifact_lib
from grr.lib import config_lib
from grr.lib import flags

# pylint: disable=g-import-not-at-top,no-name-in-module
try:
  # FIXME(dbilby): Temporary hack until key_utils is deprecated.
  from grr.lib import key_utils
except ImportError:
  pass

from grr.lib import maintenance_utils
from grr.lib import rdfvalue
from grr.lib import startup
from grr.lib import utils
from grr.lib.aff4_objects import users
# pylint: enable=g-import-not-at-top,no-name-in-module


parser = flags.PARSER
parser.description = ("Set configuration parameters for the GRR Server."
                      "\nThis script has numerous subcommands to perform "
                      "various actions. When you are first setting up, you "
                      "probably only care about 'initialize'.")

# Generic arguments.

parser.add_argument(
    "--share_dir", default="/usr/share/grr",
    help="Path to the directory containing grr data.")

subparsers = parser.add_subparsers(
    title="subcommands", dest="subparser_name", description="valid subcommands")

# Subparsers.
parser_memory = subparsers.add_parser(
    "load_memory_drivers", help="Load memory drivers from disk to database.")

parser_generate_keys = subparsers.add_parser(
    "generate_keys", help="Generate crypto keys in the configuration.")

parser_repack_clients = subparsers.add_parser(
    "repack_clients",
    help="Repack the clients binaries with the current configuration.")

parser_initialize = subparsers.add_parser(
    "initialize",
    help="Interactively run all the required steps to setup a new GRR install.")


# Update an existing user.
parser_update_user = subparsers.add_parser(
    "update_user", help="Update user settings.")

parser_update_user.add_argument("username", help="Username to update.")

parser_update_user.add_argument(
    "--password", default=False, action="store_true",
    help="Reset the password for this user (will prompt for password).")

parser_update_user.add_argument(
    "--add_labels", default=[], action="append",
    help="Add labels to the user object. These are used to control access.")

parser_update_user.add_argument(
    "--delete_labels", default=[], action="append",
    help="Delete labels from the user object. These are used to control access."
    )

parser_add_user = subparsers.add_parser(
    "add_user", help="Add a new user.")

parser_add_user.add_argument("username", help="Username to update.")

parser_add_user.add_argument(
    "--noadmin", default=False, action="store_true",
    help="Don't create the user as an administrator.")


def UpdateUser(username, password, add_labels=None, delete_labels=None):
  """Implementation of the update_user command."""
  print "Updating user %s" % username
  with aff4.FACTORY.Create("aff4:/users/%s" % username,
                           "GRRUser", mode="rw") as fd:
    # Note this accepts blank passwords as valid.
    if password is not None:
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
      fd.AddLabels(*final_add_labels, owner="GRR")

    if final_del_labels:
      fd.RemoveLabels(*final_del_labels, owner="GRR")

  ShowUser(username)

# Delete an existing user.
parser_update_user = subparsers.add_parser(
    "delete_user", help="Delete an user account.")

parser_update_user.add_argument("username", help="Username to update.")


def DeleteUser(username):
  try:
    aff4.FACTORY.Open("aff4:/users/%s" % username, "GRRUser")
  except aff4.InstantiationError:
    print "User %s not found." % username
    return

  aff4.FACTORY.Delete("aff4:/users/%s" % username)
  print "User %s has been deleted." % username

# Show user account.
parser_show_user = subparsers.add_parser(
    "show_user", help="Display user settings or list all users.")

parser_show_user.add_argument(
    "username", default=None, nargs="?",
    help="Username to display. If not specified, list all users.")


def ShowUser(username):
  """Implementation o the show_user command."""
  if username is None:
    fd = aff4.FACTORY.Open("aff4:/users")
    for user in fd.OpenChildren():
      if isinstance(user, users.GRRUser):
        print user.Describe()
  else:
    user = aff4.FACTORY.Open("aff4:/users/%s" % username)
    if isinstance(user, users.GRRUser):
      print user.Describe()
    else:
      print "User %s not found" % username


# Generate Keys Arguments
parser_generate_keys.add_argument(
    "--overwrite", default=False, action="store_true",
    help="Required to overwrite existing keys.")

# Repack arguments.
parser_repack_clients.add_argument(
    "--upload", default=True, action="store_false",
    help="Upload the client binaries to the datastore.")


# Parent parser used in other upload based parsers.
parser_upload_args = argparse.ArgumentParser(add_help=False)
parser_upload_signed_args = argparse.ArgumentParser(add_help=False)

# Upload arguments.
parser_upload_args.add_argument(
    "--file", help="The file to upload", required=True)

parser_upload_args.add_argument(
    "--dest_path", required=False, default=None,
    help="The destination path to upload the file to, specified in aff4: form,"
    "e.g. aff4:/config/test.raw")

parser_upload_args.add_argument(
    "--overwrite", default=False, action="store_true",
    help="Required to overwrite existing files.")

parser_upload_signed_args.add_argument(
    "--platform", required=True, choices=maintenance_utils.SUPPORTED_PLATFORMS,
    default="windows",
    help="The platform the file will be used on. This determines which signing"
    " keys to use, and the path on the server the file will be uploaded to.")

parser_upload_signed_args.add_argument(
    "--arch", required=True, choices=maintenance_utils.SUPPORTED_ARCHICTECTURES,
    default="amd64",
    help="The architecture the file will be used on. This determines "
    " the path on the server the file will be uploaded to.")

# Upload parsers.
parser_upload_raw = subparsers.add_parser(
    "upload_raw", parents=[parser_upload_args],
    help="Upload a raw file to an aff4 path.")

parser_upload_artifact = subparsers.add_parser(
    "upload_artifact", parents=[parser_upload_args],
    help="Upload a raw json artifact file.")


parser_upload_python = subparsers.add_parser(
    "upload_python", parents=[parser_upload_args, parser_upload_signed_args],
    help="Sign and upload a 'python hack' which can be used to execute code on "
    "a client.")

parser_upload_exe = subparsers.add_parser(
    "upload_exe", parents=[parser_upload_args, parser_upload_signed_args],
    help="Sign and upload an executable which can be used to execute code on "
    "a client.")

parser_upload_memory_driver = subparsers.add_parser(
    "upload_memory_driver",
    parents=[parser_upload_args, parser_upload_signed_args],
    help="Sign and upload a memory driver for a specific platform.")


def LoadMemoryDrivers(grr_dir):
  """Load memory drivers from disk to database."""
  for client_context in [["Platform:Darwin", "Arch:amd64"],
                         ["Platform:Windows", "Arch:i386"],
                         ["Platform:Windows", "Arch:amd64"]]:
    file_paths = config_lib.CONFIG.Get(
        "MemoryDriver.driver_files", context=client_context)
    aff4_paths = config_lib.CONFIG.Get(
        "MemoryDriver.aff4_paths", context=client_context)
    if len(file_paths) != len(aff4_paths):
      print "Length mismatch:"
      print "%s.", file_paths
      print "%s.", aff4_paths
      raise RuntimeError("Could not find all files/aff4 paths.")

    for file_path, aff4_path in zip(file_paths, aff4_paths):
      f_path = os.path.join(grr_dir, file_path)
      print "Signing and uploading %s to %s" % (f_path, aff4_path)
      up_path = maintenance_utils.UploadSignedDriverBlob(
          open(f_path).read(), aff4_path=aff4_path,
          client_context=client_context)
      print "uploaded %s" % up_path


def ImportConfig(filename, config):
  """Reads an old config file and imports keys and user accounts."""
  sections_to_import = ["PrivateKeys"]
  entries_to_import = ["Client.driver_signing_public_key",
                       "Client.executable_signing_public_key",
                       "CA.certificate",
                       "Frontend.certificate"]
  options_imported = 0
  old_config = config_lib.CONFIG.MakeNewConfig()
  old_config.Initialize(filename)

  for entry in old_config.raw_data.keys():
    try:
      section = entry.split(".")[0]
      if section in sections_to_import or entry in entries_to_import:
        config.Set(entry, old_config.Get(entry))
        print "Imported %s." % entry
        options_imported += 1

    except Exception as e:  # pylint: disable=broad-except
      print "Exception during import of %s: %s" % (entry, e)
  return options_imported


def GenerateDjangoKey(config):
  """Update a config with a random django key."""
  try:
    secret_key = config["AdminUI.django_secret_key"]
  except ConfigParser.NoOptionError:
    secret_key = "CHANGE_ME"  # This is the config file default.

  if not secret_key or secret_key.strip().upper() == "CHANGE_ME":
    key = utils.GeneratePassphrase(length=100)
    config.Set("AdminUI.django_secret_key", key)
  else:
    print "Not updating django_secret_key as it is already set."


def GenerateKeys(config):
  """Generate the keys we need for a GRR server."""
  if not hasattr(key_utils, "MakeCACert"):
    parser.error("Generate keys can only run with open source key_utils.")
  if (config.Get("PrivateKeys.server_key", default=None) and
      not flags.FLAGS.overwrite):
    raise RuntimeError("Config %s already has keys, use --overwrite to "
                       "override." % config.parser)

  print "Generating executable signing key"
  priv_key, pub_key = key_utils.GenerateRSAKey()
  config.Set("PrivateKeys.executable_signing_private_key", priv_key)
  config.Set("Client.executable_signing_public_key", pub_key)

  print "Generating driver signing key"
  priv_key, pub_key = key_utils.GenerateRSAKey()
  config.Set("PrivateKeys.driver_signing_private_key", priv_key)
  config.Set("Client.driver_signing_public_key", pub_key)

  print "Generating CA keys"
  ca_cert, ca_pk, _ = key_utils.MakeCACert()
  cipher = None
  config.Set("CA.certificate", ca_cert.as_pem())
  config.Set("PrivateKeys.ca_key", ca_pk.as_pem(cipher))

  print "Generating Server keys"
  server_cert, server_key = key_utils.MakeCASignedCert("grr", ca_pk, bits=2048)
  config.Set("Frontend.certificate", server_cert.as_pem())
  config.Set("PrivateKeys.server_key", server_key.as_pem(cipher))

  print "Generating Django Secret key (used for xsrf protection etc)"
  GenerateDjangoKey(config)


def RetryQuestion(question_text, output_re="", default_val=""):
  """Continually ask a question until the output_re is matched."""
  while True:
    if default_val:
      new_text = "%s [%s]: " % (question_text, default_val)
    else:
      new_text = "%s: " % question_text
    output = raw_input(new_text) or default_val
    output = output.strip()
    if not output_re or re.match(output_re, output):
      break
    else:
      print "Invalid input, must match %s" % output_re
  return output


def ConfigureBaseOptions(config):
  """Configure the basic options required to run the server."""

  print "We are now going to configure the server using a bunch of questions.\n"

  print """\nFor GRR to work each client has to be able to communicate with the
server. To do this we normally need a public dns name or IP address to
communicate with. In the standard configuration this will be used to host both
the client facing server and the admin user interface.\n"""
  print "Guessing public hostname of your server..."
  try:
    hostname = maintenance_utils.GuessPublicHostname()
    print "Using %s as public hostname" % hostname
  except (OSError, IOError):
    print "Sorry, we couldn't guess your public hostname"

  hostname = RetryQuestion("Please enter your public hostname e.g. "
                           "grr.example.com", "^([\\.A-Za-z0-9-]+)*$")

  print """\n\nServer URL
The Server URL specifies the URL that the clients will connect to
communicate with the server. This needs to be publically accessible. By default
this will be port 8080 with the URL ending in /control.
"""
  location = RetryQuestion("Server URL", "^http://.*/control$",
                           "http://%s:8080/control" % hostname)
  config.Set("Client.control_urls", [location])

  frontend_port = urlparse.urlparse(location).port or 80
  if frontend_port != config_lib.CONFIG.Get("Frontend.bind_port"):
    config.Set("Frontend.bind_port", frontend_port)
    print "\nSetting the frontend listening port to %d.\n" % frontend_port
    print "Please make sure that this matches your client settings.\n"

  print """\nUI URL:
The UI URL specifies where the Administrative Web Interface can be found.
"""
  ui_url = RetryQuestion("AdminUI URL", "^http://.*$",
                         "http://%s:8000" % hostname)
  config.Set("AdminUI.url", ui_url)

  print """\nMonitoring/Email domain name:
Emails concerning alerts or updates must be sent to this domain.
"""
  domain = RetryQuestion("Email domain", "^([\\.A-Za-z0-9-]+)*$",
                         "example.com")
  config.Set("Logging.domain", domain)

  print """\nMonitoring email address
Address where monitoring events get sent, e.g. crashed clients, broken server
etc.
"""
  email = RetryQuestion("Monitoring email", "",
                        "grr-monitoring@%s" % domain)
  config.Set("Monitoring.alert_email", email)

  print """\nEmergency email address
Address where high priority events such as an emergency ACL bypass are sent.
"""
  emergency_email = RetryQuestion("Monitoring emergency email", "",
                                  "grr-emergency@%s" % domain)
  config.Set("Monitoring.emergency_access_email", emergency_email)

  config.Write()
  print ("Configuration parameters set. You can edit these in %s" %
         config.parser)


def Initialize(config=None):
  """Initialize or update a GRR configuration."""

  print "Checking write access on config %s" % config.parser
  if not os.access(config.parser.filename, os.W_OK):
    raise IOError("Config not writeable (need sudo?)")

  print "\nStep 0: Importing Configuration from previous installation."
  options_imported = 0
  prev_config_file = config.Get("ConfigUpdater.old_config", default=None)
  if prev_config_file and os.access(prev_config_file, os.R_OK):
    print "Found config file %s." % prev_config_file
    if raw_input("Do you want to import this configuration?"
                 " [yN]: ").upper() == "Y":
      options_imported = ImportConfig(prev_config_file, config)
  else:
    print "No old config file found."

  print "\nStep 1: Key Generation"
  if config.Get("PrivateKeys.server_key", default=None):
    if options_imported > 0:
      print ("Since you have imported keys from another installation in the "
             "last step,\nyou probably do not want to generate new keys now.")
    if ((raw_input("You already have keys in your config, do you want to"
                   " overwrite them? [yN]: ").upper() or "N") == "Y"):
      flags.FLAGS.overwrite = True
      GenerateKeys(config)
  else:
    GenerateKeys(config)

  print "\nStep 2: Setting Basic Configuration Parameters"
  ConfigureBaseOptions(config)

  # Now load our modified config.
  startup.ConfigInit()

  print "\nStep 3: Adding Admin User"
  password = getpass.getpass(prompt="Please enter password for user 'admin': ")
  UpdateUser("admin", password, ["admin"])
  print "User admin added."

  print "\nStep 4: Uploading Memory Drivers to the Database"
  LoadMemoryDrivers(flags.FLAGS.share_dir)

  print "\nStep 5: Repackaging clients with new configuration."
  # We need to update the config to point to the installed templates now.
  config.Set("ClientBuilder.executables_path", os.path.join(
      flags.FLAGS.share_dir, "executables"))

  # Build debug binaries, then build release binaries.
  maintenance_utils.RepackAllBinaries(upload=True, debug_build=True)
  maintenance_utils.RepackAllBinaries(upload=True)

  print "\nInitialization complete, writing configuration."
  config.Write()
  print "Please restart the service for it to take effect.\n\n"


def UploadRaw(file_path, aff4_path):
  """Upload a file to the datastore."""
  full_path = rdfvalue.RDFURN(aff4_path).Add(os.path.basename(file_path))
  fd = aff4.FACTORY.Create(full_path, "AFF4Image", mode="w")
  fd.Write(open(file_path).read(1024*1024*30))
  fd.Close()
  return str(fd.urn)


def main(unused_argv):
  """Main."""
  config_lib.CONFIG.AddContext("Commandline Context")
  config_lib.CONFIG.AddContext("ConfigUpdater Context")
  startup.Init()

  try:
    print "Using configuration %s" % config_lib.CONFIG.parser
  except AttributeError:
    raise RuntimeError("No valid config specified.")

  if flags.FLAGS.subparser_name == "load_memory_drivers":
    LoadMemoryDrivers(flags.FLAGS.share_dir)

  elif flags.FLAGS.subparser_name == "generate_keys":
    try:
      GenerateKeys(config_lib.CONFIG)
    except RuntimeError, e:
      # GenerateKeys will raise if keys exist and --overwrite is not set.
      print "ERROR: %s" % e
      sys.exit(1)
    config_lib.CONFIG.Write()

  elif flags.FLAGS.subparser_name == "repack_clients":
    maintenance_utils.RepackAllBinaries(upload=flags.FLAGS.upload)
    maintenance_utils.RepackAllBinaries(upload=flags.FLAGS.upload,
                                        debug_build=True)

  elif flags.FLAGS.subparser_name == "initialize":
    Initialize(config_lib.CONFIG)

  elif flags.FLAGS.subparser_name == "show_user":
    ShowUser(flags.FLAGS.username)

  elif flags.FLAGS.subparser_name == "update_user":
    password = None
    if flags.FLAGS.password:
      password = getpass.getpass(prompt="Please enter new password for '%s': " %
                                 flags.FLAGS.username)
    UpdateUser(flags.FLAGS.username, password, flags.FLAGS.add_labels,
               flags.FLAGS.delete_labels)

  elif flags.FLAGS.subparser_name == "delete_user":
    DeleteUser(flags.FLAGS.username)

  elif flags.FLAGS.subparser_name == "add_user":
    password = getpass.getpass(prompt="Please enter password for user '%s': " %
                               flags.FLAGS.username)
    labels = []
    if not flags.FLAGS.noadmin:
      labels.append("admin")
    UpdateUser(flags.FLAGS.username, password, labels)

  elif flags.FLAGS.subparser_name == "upload_python":
    content = open(flags.FLAGS.file).read(1024*1024*30)
    aff4_path = flags.FLAGS.dest_path
    if not aff4_path:
      python_hack_root_urn = config_lib.CONFIG.Get("Config.python_hack_root")
      aff4_path = python_hack_root_urn.Add(os.path.basename(flags.FLAGS.file))
    context = ["Platform:%s" % flags.FLAGS.platform.title(),
               "Client"]
    maintenance_utils.UploadSignedConfigBlob(content, aff4_path=aff4_path,
                                             client_context=context)

  elif flags.FLAGS.subparser_name == "upload_exe":
    content = open(flags.FLAGS.file).read(1024*1024*30)
    context = ["Platform:%s" % flags.FLAGS.platform.title(),
               "Client"]

    if flags.FLAGS.dest_path:
      dest_path = rdfvalue.RDFURN(flags.FLAGS.dest_path)
    else:
      dest_path = config_lib.CONFIG.Get(
          "Executables.aff4_path", context=context).Add(
              os.path.basename(flags.FLAGS.file))

    # Now upload to the destination.
    uploaded = maintenance_utils.UploadSignedConfigBlob(
        content, aff4_path=dest_path, client_context=context)

    print "Uploaded to %s" % dest_path

  elif flags.FLAGS.subparser_name == "upload_memory_driver":
    client_context = ["Platform:%s" % flags.FLAGS.platform.title(),
                      "Arch:%s" % flags.FLAGS.arch]
    content = open(flags.FLAGS.file).read(1024*1024*30)

    if flags.FLAGS.dest_path:
      uploaded = maintenance_utils.UploadSignedDriverBlob(
          content, aff4_path=flags.FLAGS.dest_path,
          client_context=client_context)

    else:
      uploaded = maintenance_utils.UploadSignedDriverBlob(
          content, client_context=client_context)

    print "Uploaded to %s" % uploaded

  elif flags.FLAGS.subparser_name == "upload_raw":
    if not flags.FLAGS.dest_path:
      flags.FLAGS.dest_path = aff4.ROOT_URN.Add("config").Add("raw")
    uploaded = UploadRaw(flags.FLAGS.file, flags.FLAGS.dest_path)
    print "Uploaded to %s" % uploaded

  elif flags.FLAGS.subparser_name == "upload_artifact":
    json.load(open(flags.FLAGS.file))  # Check it will parse.
    base_urn = aff4.ROOT_URN.Add("artifact_store")
    try:
      artifact.UploadArtifactYamlFile(
          open(flags.FLAGS.file).read(1000000), base_urn=base_urn, token=None,
          overwrite=flags.FLAGS.overwrite)
    except artifact_lib.ArtifactDefinitionError as e:
      print "Error %s. You may need to set --overwrite." % e

if __name__ == "__main__":
  flags.StartMain(main)
