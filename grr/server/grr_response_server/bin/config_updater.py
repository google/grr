#!/usr/bin/env python
"""Util for modifying the GRR server configuration."""
from __future__ import print_function

import argparse
import os
import sys


import builtins
from future.utils import iterkeys
import yaml

# pylint: disable=unused-import,g-bad-import-order
from grr_response_core.lib.rdfvalues import artifacts as rdf_artifacts
from grr_response_server import server_plugins
# pylint: enable=g-bad-import-order,unused-import

from grr_response_core import config as grr_config
from grr_response_core.config import contexts
from grr_response_core.config import server as config_server
from grr_response_core.lib import config_lib
from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import repacking
from grr_response_server import aff4
from grr_response_server import artifact
from grr_response_server import artifact_registry
from grr_response_server import data_migration
from grr_response_server import maintenance_utils
from grr_response_server import rekall_profile_server
from grr_response_server import server_startup
from grr_response_server.aff4_objects import users as aff4_users
from grr_response_server.bin import config_updater_util

parser = flags.PARSER
parser.description = ("Set configuration parameters for the GRR Server."
                      "\nThis script has numerous subcommands to perform "
                      "various actions. When you are first setting up, you "
                      "probably only care about 'initialize'.")

# Generic arguments.
parser.add_argument(
    "--version",
    action="version",
    version=config_server.VERSION["packageversion"])

parser.add_argument(
    "--share_dir",
    default="/usr/share/grr",
    help="Path to the directory containing grr data.")

subparsers = parser.add_subparsers(
    title="subcommands", dest="subparser_name", description="valid subcommands")

# Subparsers.
parser_generate_keys = subparsers.add_parser(
    "generate_keys", help="Generate crypto keys in the configuration.")

parser_repack_clients = subparsers.add_parser(
    "repack_clients",
    help="Repack the clients binaries with the current configuration.")

parser_initialize = subparsers.add_parser(
    "initialize", help="Run all the required steps to setup a new GRR install.")

parser_set_var = subparsers.add_parser("set_var", help="Set a config variable.")

# Update an existing user.
parser_update_user = subparsers.add_parser(
    "update_user", help="Update user settings.")

parser_update_user.add_argument("username", help="Username to update.")

parser_update_user.add_argument(
    "--password",
    default=False,
    action="store_true",
    help="Reset the password for this user (will prompt for password).")

parser_update_user.add_argument(
    "--add_labels",
    default=[],
    action="append",
    help="Add labels to the user object. These are used to control access.")

parser_update_user.add_argument(
    "--delete_labels",
    default=[],
    action="append",
    help="Delete labels from the user object. These are used to control "
    "access.")

parser_add_user = subparsers.add_parser("add_user", help="Add a new user.")

parser_add_user.add_argument("username", help="Username to create.")
parser_add_user.add_argument("--password", default=None, help="Set password.")

parser_add_user.add_argument(
    "--labels",
    default=[],
    action="append",
    help="Create user with labels. These are used to control access.")

parser_add_user.add_argument(
    "--noadmin",
    default=False,
    action="store_true",
    help="Don't create the user as an administrator.")

parser_initialize.add_argument(
    "--external_hostname", default=None, help="External hostname to use.")

parser_initialize.add_argument(
    "--admin_password", default=None, help="Admin password for web interface.")

parser_initialize.add_argument(
    "--noprompt",
    default=False,
    action="store_true",
    help="Set to avoid prompting during initialize.")

parser_initialize.add_argument(
    "--redownload_templates",
    default=False,
    action="store_true",
    help="Re-download templates during noninteractive config initialization "
    "(server debs already include templates).")

parser_initialize.add_argument(
    "--norepack_templates",
    default=False,
    action="store_true",
    help="Skip template repacking during noninteractive config initialization.")

parser_initialize.add_argument(
    "--enable_rekall",
    default=False,
    action="store_true",
    help="Enable Rekall during noninteractive config initialization.")

parser_initialize.add_argument(
    "--mysql_hostname",
    help="Hostname for a running MySQL instance (only appplies if --noprompt "
    "is set).")

parser_initialize.add_argument(
    "--mysql_port",
    type=int,
    help="Port for a running MySQL instance (only applies if --noprompt "
    "is set).")

parser_initialize.add_argument(
    "--mysql_db",
    help="Name of GRR's MySQL database (only applies if --noprompt is set).")

parser_initialize.add_argument(
    "--mysql_username",
    help="Name of GRR MySQL database user (only applies if --noprompt is set).")

parser_initialize.add_argument(
    "--mysql_password",
    help="Password for GRR MySQL database user (only applies if --noprompt is "
    "set).")

parser_set_var.add_argument("var", help="Variable to set.")
parser_set_var.add_argument("val", help="Value to set.")

# Delete an existing user.
parser_delete_user = subparsers.add_parser(
    "delete_user", help="Delete an user account.")

parser_delete_user.add_argument("username", help="Username to delete.")

# Show user account.
parser_show_user = subparsers.add_parser(
    "show_user", help="Display user settings or list all users.")

parser_show_user.add_argument(
    "username",
    default=None,
    nargs="?",
    help="Username to display. If not specified, list all users.")

# Generate Keys Arguments
parser_generate_keys.add_argument(
    "--overwrite_keys",
    default=False,
    action="store_true",
    help="Required to overwrite existing keys.")

# Repack arguments.
parser_repack_clients.add_argument(
    "--noupload",
    default=False,
    action="store_true",
    help="Don't upload the client binaries to the datastore.")

# Parent parser used in other upload based parsers.
parser_upload_args = argparse.ArgumentParser(add_help=False)
parser_upload_signed_args = argparse.ArgumentParser(add_help=False)

# Upload arguments.
parser_upload_args.add_argument(
    "--file", help="The file to upload", required=True)

parser_upload_args.add_argument(
    "--dest_path",
    required=False,
    default=None,
    help="The destination path to upload the file to, specified in aff4: form,"
    "e.g. aff4:/config/test.raw")

parser_upload_signed_args.add_argument(
    "--platform",
    required=True,
    choices=maintenance_utils.SUPPORTED_PLATFORMS,
    default="windows",
    help="The platform the file will be used on. This determines which signing"
    " keys to use, and the path on the server the file will be uploaded to.")

parser_upload_signed_args.add_argument(
    "--arch",
    required=True,
    choices=maintenance_utils.SUPPORTED_ARCHITECTURES,
    default="amd64",
    help="The architecture the file will be used on. This determines "
    " the path on the server the file will be uploaded to.")

# Upload parsers.
parser_upload_raw = subparsers.add_parser(
    "upload_raw",
    parents=[parser_upload_args],
    help="Upload a raw file to an aff4 path.")

parser_upload_artifact = subparsers.add_parser(
    "upload_artifact",
    parents=[parser_upload_args],
    help="Upload a raw json artifact file.")

parser_upload_artifact.add_argument(
    "--overwrite_artifact",
    default=False,
    action="store_true",
    help="Overwrite existing artifact.")

parser_delete_artifacts = subparsers.add_parser(
    "delete_artifacts",
    parents=[],
    help="Delete a list of artifacts from the data store.")

parser_delete_artifacts.add_argument(
    "--artifact", default=[], action="append", help="The artifacts to delete.")

parser_upload_python = subparsers.add_parser(
    "upload_python",
    parents=[parser_upload_args, parser_upload_signed_args],
    help="Sign and upload a 'python hack' which can be used to execute code on "
    "a client.")

parser_upload_exe = subparsers.add_parser(
    "upload_exe",
    parents=[parser_upload_args, parser_upload_signed_args],
    help="Sign and upload an executable which can be used to execute code on "
    "a client.")

subparsers.add_parser(
    "download_missing_rekall_profiles",
    parents=[],
    help="Downloads all Rekall profiles from the repository that are not "
    "currently present in the database.")

set_global_notification = subparsers.add_parser(
    "set_global_notification",
    parents=[],
    help="Sets a global notification for all GRR users to see.")

set_global_notification.add_argument(
    "--type",
    choices=list(iterkeys(aff4_users.GlobalNotification.Type.enum_dict)),
    default="INFO",
    help="Global notification type.")

set_global_notification.add_argument(
    "--header", default="", required=True, help="Global notification header.")

set_global_notification.add_argument(
    "--content", default="", help="Global notification content.")

set_global_notification.add_argument(
    "--link", default="", help="Global notification link.")

set_global_notification.add_argument(
    "--show_from",
    default="",
    help="When to start showing the notification (in a "
    "human-readable format, i.e. 2011-11-01 10:23:00). Timestamp is "
    "assumed to be in UTC timezone.")

set_global_notification.add_argument(
    "--duration",
    default=None,
    help="How much time the notification is valid (duration in "
    "human-readable form, i.e. 1h, 1d, etc).")

parser_rotate_key = subparsers.add_parser(
    "rotate_server_key", parents=[], help="Sets a new server key.")

parser_rotate_key.add_argument(
    "--common_name", default="grr", help="The common name to use for the cert.")

parser_rotate_key.add_argument(
    "--keylength",
    default=None,
    help="The key length for the new server key. "
    "Defaults to the Server.rsa_key_length config option.")

parser_migrate_data = subparsers.add_parser(
    "migrate_data",
    parents=[],
    help="Migrates data to the relational database.")


def main(argv):
  """Main."""
  del argv  # Unused.

  token = config_updater_util.GetToken()
  grr_config.CONFIG.AddContext(contexts.COMMAND_LINE_CONTEXT)
  grr_config.CONFIG.AddContext(contexts.CONFIG_UPDATER_CONTEXT)

  if flags.FLAGS.subparser_name == "initialize":
    config_lib.ParseConfigCommandLine()
    if flags.FLAGS.noprompt:
      config_updater_util.InitializeNoPrompt(grr_config.CONFIG, token=token)
    else:
      config_updater_util.Initialize(grr_config.CONFIG, token=token)
    return

  server_startup.Init()

  try:
    print("Using configuration %s" % grr_config.CONFIG)
  except AttributeError:
    raise RuntimeError("No valid config specified.")

  if flags.FLAGS.subparser_name == "generate_keys":
    try:
      config_updater_util.GenerateKeys(
          grr_config.CONFIG, overwrite_keys=flags.FLAGS.overwrite_keys)
    except RuntimeError as e:
      # GenerateKeys will raise if keys exist and overwrite_keys is not set.
      print("ERROR: %s" % e)
      sys.exit(1)
    grr_config.CONFIG.Write()

  elif flags.FLAGS.subparser_name == "repack_clients":
    upload = not flags.FLAGS.noupload
    repacking.TemplateRepacker().RepackAllTemplates(upload=upload, token=token)

  elif flags.FLAGS.subparser_name == "show_user":
    maintenance_utils.ShowUser(flags.FLAGS.username, token=token)

  elif flags.FLAGS.subparser_name == "update_user":
    try:
      maintenance_utils.UpdateUser(
          flags.FLAGS.username,
          flags.FLAGS.password,
          flags.FLAGS.add_labels,
          flags.FLAGS.delete_labels,
          token=token)
    except maintenance_utils.UserError as e:
      print(e)

  elif flags.FLAGS.subparser_name == "delete_user":
    maintenance_utils.DeleteUser(flags.FLAGS.username, token=token)

  elif flags.FLAGS.subparser_name == "add_user":
    labels = []
    if not flags.FLAGS.noadmin:
      labels.append("admin")

    if flags.FLAGS.labels:
      labels.extend(flags.FLAGS.labels)

    try:
      maintenance_utils.AddUser(
          flags.FLAGS.username, flags.FLAGS.password, labels, token=token)
    except maintenance_utils.UserError as e:
      print(e)

  elif flags.FLAGS.subparser_name == "upload_python":
    python_hack_root_urn = grr_config.CONFIG.Get("Config.python_hack_root")
    content = open(flags.FLAGS.file, "rb").read(1024 * 1024 * 30)
    aff4_path = flags.FLAGS.dest_path
    platform = flags.FLAGS.platform
    if not aff4_path:
      aff4_path = python_hack_root_urn.Add(platform.lower()).Add(
          os.path.basename(flags.FLAGS.file))
    if not str(aff4_path).startswith(str(python_hack_root_urn)):
      raise ValueError("AFF4 path must start with %s." % python_hack_root_urn)
    context = ["Platform:%s" % platform.title(), "Client Context"]
    maintenance_utils.UploadSignedConfigBlob(
        content, aff4_path=aff4_path, client_context=context, token=token)

  elif flags.FLAGS.subparser_name == "upload_exe":
    content = open(flags.FLAGS.file, "rb").read(1024 * 1024 * 30)
    context = ["Platform:%s" % flags.FLAGS.platform.title(), "Client Context"]

    if flags.FLAGS.dest_path:
      dest_path = rdfvalue.RDFURN(flags.FLAGS.dest_path)
    else:
      dest_path = grr_config.CONFIG.Get(
          "Executables.aff4_path", context=context).Add(
              os.path.basename(flags.FLAGS.file))

    # Now upload to the destination.
    maintenance_utils.UploadSignedConfigBlob(
        content, aff4_path=dest_path, client_context=context, token=token)

    print("Uploaded to %s" % dest_path)

  elif flags.FLAGS.subparser_name == "set_var":
    config = grr_config.CONFIG
    print("Setting %s to %s" % (flags.FLAGS.var, flags.FLAGS.val))
    if flags.FLAGS.val.startswith("["):  # Allow setting of basic lists.
      flags.FLAGS.val = flags.FLAGS.val[1:-1].split(",")
    config.Set(flags.FLAGS.var, flags.FLAGS.val)
    config.Write()

  elif flags.FLAGS.subparser_name == "upload_raw":
    if not flags.FLAGS.dest_path:
      flags.FLAGS.dest_path = aff4.ROOT_URN.Add("config").Add("raw")
    uploaded = config_updater_util.UploadRaw(
        flags.FLAGS.file, flags.FLAGS.dest_path, token=token)
    print("Uploaded to %s" % uploaded)

  elif flags.FLAGS.subparser_name == "upload_artifact":
    yaml.load(open(flags.FLAGS.file, "rb"))  # Check it will parse.
    try:
      artifact.UploadArtifactYamlFile(
          open(flags.FLAGS.file, "rb").read(),
          overwrite=flags.FLAGS.overwrite_artifact)
    except rdf_artifacts.ArtifactDefinitionError as e:
      print("Error %s. You may need to set --overwrite_artifact." % e)

  elif flags.FLAGS.subparser_name == "delete_artifacts":
    artifact_list = flags.FLAGS.artifact
    if not artifact_list:
      raise ValueError("No artifact to delete given.")
    artifact_registry.DeleteArtifactsFromDatastore(artifact_list, token=token)
    print("Artifacts %s deleted." % artifact_list)

  elif flags.FLAGS.subparser_name == "download_missing_rekall_profiles":
    print("Downloading missing Rekall profiles.")
    s = rekall_profile_server.GRRRekallProfileServer()
    s.GetMissingProfiles()

  elif flags.FLAGS.subparser_name == "set_global_notification":
    notification = aff4_users.GlobalNotification(
        type=flags.FLAGS.type,
        header=flags.FLAGS.header,
        content=flags.FLAGS.content,
        link=flags.FLAGS.link)
    if flags.FLAGS.show_from:
      notification.show_from = rdfvalue.RDFDatetime().ParseFromHumanReadable(
          flags.FLAGS.show_from)
    if flags.FLAGS.duration:
      notification.duration = rdfvalue.Duration().ParseFromHumanReadable(
          flags.FLAGS.duration)

    print("Setting global notification.")
    print(notification)

    with aff4.FACTORY.Create(
        aff4_users.GlobalNotificationStorage.DEFAULT_PATH,
        aff4_type=aff4_users.GlobalNotificationStorage,
        mode="rw",
        token=token) as storage:
      storage.AddNotification(notification)
  elif flags.FLAGS.subparser_name == "rotate_server_key":
    print("""
You are about to rotate the server key. Note that:

  - Clients might experience intermittent connection problems after
    the server keys rotated.

  - It's not possible to go back to an earlier key. Clients that see a
    new certificate will remember the cert's serial number and refuse
    to accept any certificate with a smaller serial number from that
    point on.
    """)

    if builtins.input("Continue? [yN]: ").upper() == "Y":
      if flags.FLAGS.keylength:
        keylength = int(flags.FLAGS.keylength)
      else:
        keylength = grr_config.CONFIG["Server.rsa_key_length"]

      maintenance_utils.RotateServerKey(
          cn=flags.FLAGS.common_name, keylength=keylength)
  elif flags.FLAGS.subparser_name == "migrate_data":
    data_migration.Migrate()


if __name__ == "__main__":
  flags.StartMain(main)
