#!/usr/bin/env python
"""Util for modifying the GRR server configuration."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import sys


import builtins
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
from grr_response_core.lib import repacking
from grr_response_server import artifact
from grr_response_server import artifact_registry
from grr_response_server import maintenance_utils
from grr_response_server import rekall_profile_server
from grr_response_server import server_startup
from grr_response_server.bin import config_updater_util
from grr_response_server.rdfvalues import objects as rdf_objects

parser = flags.PARSER
parser.description = ("Set configuration parameters for the GRR Server."
                      "\nThis script has numerous subcommands to perform "
                      "various actions. When you are first setting up, you "
                      "probably only care about 'initialize'.")

# Generic arguments.
parser.add_argument(
    "--share_dir",
    default="/usr/share/grr",
    help="Path to the directory containing grr data.")

subparsers = parser.add_subparsers(
    title="subcommands", dest="subparser_name", description="valid subcommands")

# Subparsers.

# TODO(hanuszczak): Before Python 3.3 there is no way to make subparsers
# optional, so having a `--version` flag in a non-magic way (through `version`
# action) is impossible. As a temporary hack we use `version` command instead
# of a flag to achieve that. Once we migrate to Abseil this should no longer be
# an issue and version should be declarable as an optional flag again.
parser_version = subparsers.add_parser(
    "version", help="Print config updater version number and exit immediately")

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
    "--admin",
    default=True,
    action="store_true",
    help="Make the user an admin, if they aren't already.")

parser_add_user = subparsers.add_parser("add_user", help="Add a new user.")

parser_add_user.add_argument("username", help="Username to create.")
parser_add_user.add_argument("--password", default=None, help="Set password.")

parser_add_user.add_argument(
    "--admin",
    default=True,
    action="store_true",
    help="Add the user with admin privileges.")

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


def _ExtendWithUploadArgs(upload_parser):
  upload_parser.add_argument("--file", help="The file to upload", required=True)


def _ExtendWithUploadSignedArgs(upload_signed_parser):
  upload_signed_parser.add_argument(
      "--platform",
      required=True,
      choices=maintenance_utils.SUPPORTED_PLATFORMS,
      help="The platform the file will be used on. This determines which "
      "signing keys to use, and the path on the server the file will be "
      "uploaded to.")
  upload_signed_parser.add_argument(
      "--upload_subdirectory",
      required=False,
      default="",
      help="Directory path under which to place an uploaded python-hack "
      "or executable, e.g for a Windows executable named 'hello.exe', "
      "if --upload_subdirectory is set to 'test', the path of the "
      "uploaded binary will be 'windows/test/hello.exe', relative to "
      "the root path for executables.")

# Upload parsers.

parser_upload_artifact = subparsers.add_parser(
    "upload_artifact", help="Upload a raw json artifact file.")

_ExtendWithUploadArgs(parser_upload_artifact)

parser_upload_artifact.add_argument(
    "--overwrite_artifact",
    default=False,
    action="store_true",
    help="Overwrite existing artifact.")

parser_delete_artifacts = subparsers.add_parser(
    "delete_artifacts", help="Delete a list of artifacts from the data store.")

parser_delete_artifacts.add_argument(
    "--artifact", default=[], action="append", help="The artifacts to delete.")

parser_upload_python = subparsers.add_parser(
    "upload_python",
    help="Sign and upload a 'python hack' which can be used to execute code on "
    "a client.")

_ExtendWithUploadArgs(parser_upload_python)
_ExtendWithUploadSignedArgs(parser_upload_python)

parser_upload_exe = subparsers.add_parser(
    "upload_exe",
    help="Sign and upload an executable which can be used to execute code on "
    "a client.")

_ExtendWithUploadArgs(parser_upload_exe)
_ExtendWithUploadSignedArgs(parser_upload_exe)

subparsers.add_parser(
    "download_missing_rekall_profiles",
    help="Downloads all Rekall profiles from the repository that are not "
    "currently present in the database.")

parser_rotate_key = subparsers.add_parser(
    "rotate_server_key", help="Sets a new server key.")

parser_rotate_key.add_argument(
    "--common_name", default="grr", help="The common name to use for the cert.")

parser_rotate_key.add_argument(
    "--keylength",
    default=None,
    help="The key length for the new server key. "
    "Defaults to the Server.rsa_key_length config option.")


def main(argv):
  """Main."""
  del argv  # Unused.

  if flags.FLAGS.subparser_name == "version":
    version = config_server.VERSION["packageversion"]
    print("GRR configuration updater {}".format(version))
    return

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
    if flags.FLAGS.username:
      print(config_updater_util.GetUserSummary(flags.FLAGS.username))
    else:
      print(config_updater_util.GetAllUserSummaries())

  elif flags.FLAGS.subparser_name == "update_user":
    config_updater_util.UpdateUser(
        flags.FLAGS.username,
        password=flags.FLAGS.password,
        is_admin=flags.FLAGS.admin)

  elif flags.FLAGS.subparser_name == "delete_user":
    config_updater_util.DeleteUser(flags.FLAGS.username)

  elif flags.FLAGS.subparser_name == "add_user":
    config_updater_util.CreateUser(
        flags.FLAGS.username,
        password=flags.FLAGS.password,
        is_admin=flags.FLAGS.admin)

  elif flags.FLAGS.subparser_name == "upload_python":
    config_updater_util.UploadSignedBinary(
        flags.FLAGS.file,
        rdf_objects.SignedBinaryID.BinaryType.PYTHON_HACK,
        flags.FLAGS.platform,
        upload_subdirectory=flags.FLAGS.upload_subdirectory,
        token=token)

  elif flags.FLAGS.subparser_name == "upload_exe":
    config_updater_util.UploadSignedBinary(
        flags.FLAGS.file,
        rdf_objects.SignedBinaryID.BinaryType.EXECUTABLE,
        flags.FLAGS.platform,
        upload_subdirectory=flags.FLAGS.upload_subdirectory,
        token=token)

  elif flags.FLAGS.subparser_name == "set_var":
    config = grr_config.CONFIG
    print("Setting %s to %s" % (flags.FLAGS.var, flags.FLAGS.val))
    if flags.FLAGS.val.startswith("["):  # Allow setting of basic lists.
      flags.FLAGS.val = flags.FLAGS.val[1:-1].split(",")
    config.Set(flags.FLAGS.var, flags.FLAGS.val)
    config.Write()

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


if __name__ == "__main__":
  flags.StartMain(main)
