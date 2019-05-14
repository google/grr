#!/usr/bin/env python
"""Util for modifying the GRR server configuration."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import io
import sys


from absl import app
from absl.flags import argparse_flags
from future.builtins import input

# pylint: disable=unused-import,g-bad-import-order
from grr_response_core.lib.rdfvalues import artifacts as rdf_artifacts
from grr_response_server import server_plugins
# pylint: enable=g-bad-import-order,unused-import

from grr_response_client_builder import repacking
from grr_response_core import config as grr_config
from grr_response_core.config import contexts
from grr_response_core.config import server as config_server
from grr_response_core.lib import config_lib
from grr_response_server import artifact
from grr_response_server import artifact_registry
from grr_response_server import maintenance_utils
from grr_response_server import server_startup
from grr_response_server.bin import config_updater_keys_util
from grr_response_server.bin import config_updater_util
from grr_response_server.rdfvalues import objects as rdf_objects

parser = argparse_flags.ArgumentParser(
    description=("Set configuration parameters for the GRR Server."
                 "\nThis script has numerous subcommands to perform "
                 "various actions. When you are first setting up, you "
                 "probably only care about 'initialize'."))

# Generic arguments.
parser.add_argument(
    "--version",
    action="version",
    version=config_server.VERSION["packageversion"],
    help="Print config updater version number and exit immediately.")

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

parser_switch_datastore = subparsers.add_parser(
    "switch_datastore",
    help="Switch from a legacy datastore (AFF4) "
    "to the new optimized implementation (REL_DB).")

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

# TODO(hanuszczak): Rename this flag to `repack_templates` (true by default).
parser_initialize.add_argument(
    "--norepack_templates",
    default=False,
    action="store_true",
    help="Skip template repacking during noninteractive config initialization.")

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

parser_initialize.add_argument(
    "--mysql_client_key_path",
    help="The path name of the client private key file.")

parser_initialize.add_argument(
    "--mysql_client_cert_path",
    help="The path name of the client public key certificate file.")

parser_initialize.add_argument(
    "--mysql_ca_cert_path",
    help="The path name of the Certificate Authority (CA) certificate file.")

parser_initialize.add_argument(
    "--use_rel_db",
    default=False,
    action="store_true",
    help="Use the new-generation datastore (REL_DB).")

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
    "--username",
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

parser_rotate_key = subparsers.add_parser(
    "rotate_server_key", help="Sets a new server key.")

parser_rotate_key.add_argument(
    "--common_name", default="grr", help="The common name to use for the cert.")

parser_rotate_key.add_argument(
    "--keylength",
    default=None,
    help="The key length for the new server key. "
    "Defaults to the Server.rsa_key_length config option.")


def main(args):
  """Main."""
  token = config_updater_util.GetToken()
  grr_config.CONFIG.AddContext(contexts.COMMAND_LINE_CONTEXT)
  grr_config.CONFIG.AddContext(contexts.CONFIG_UPDATER_CONTEXT)

  if args.subparser_name == "initialize":
    config_lib.ParseConfigCommandLine()
    if args.noprompt:
      config_updater_util.InitializeNoPrompt(
          grr_config.CONFIG,
          external_hostname=args.external_hostname,
          admin_password=args.admin_password,
          mysql_hostname=args.mysql_hostname,
          mysql_port=args.mysql_port,
          mysql_username=args.mysql_username,
          mysql_password=args.mysql_password,
          mysql_db=args.mysql_db,
          mysql_client_key_path=args.mysql_client_key_path,
          mysql_client_cert_path=args.mysql_client_cert_path,
          mysql_ca_cert_path=args.mysql_ca_cert_path,
          use_rel_db=args.use_rel_db,
          redownload_templates=args.redownload_templates,
          repack_templates=not args.norepack_templates,
          token=token)
    else:
      config_updater_util.Initialize(
          grr_config.CONFIG,
          external_hostname=args.external_hostname,
          admin_password=args.admin_password,
          redownload_templates=args.redownload_templates,
          repack_templates=not args.norepack_templates,
          token=token)
    return

  server_startup.Init()

  try:
    print("Using configuration %s" % grr_config.CONFIG)
  except AttributeError:
    raise RuntimeError("No valid config specified.")

  if args.subparser_name == "generate_keys":
    try:
      config_updater_keys_util.GenerateKeys(
          grr_config.CONFIG, overwrite_keys=args.overwrite_keys)
    except RuntimeError as e:
      # GenerateKeys will raise if keys exist and overwrite_keys is not set.
      print("ERROR: %s" % e)
      sys.exit(1)
    grr_config.CONFIG.Write()

  elif args.subparser_name == "repack_clients":
    upload = not args.noupload
    repacking.TemplateRepacker().RepackAllTemplates(upload=upload, token=token)

  elif args.subparser_name == "show_user":
    if args.username:
      print(config_updater_util.GetUserSummary(args.username))
    else:
      print(config_updater_util.GetAllUserSummaries())

  elif args.subparser_name == "update_user":
    config_updater_util.UpdateUser(
        args.username, password=args.password, is_admin=args.admin)

  elif args.subparser_name == "delete_user":
    config_updater_util.DeleteUser(args.username)

  elif args.subparser_name == "add_user":
    config_updater_util.CreateUser(
        args.username, password=args.password, is_admin=args.admin)

  elif args.subparser_name == "upload_python":
    config_updater_util.UploadSignedBinary(
        args.file,
        rdf_objects.SignedBinaryID.BinaryType.PYTHON_HACK,
        args.platform,
        upload_subdirectory=args.upload_subdirectory)

  elif args.subparser_name == "upload_exe":
    config_updater_util.UploadSignedBinary(
        args.file,
        rdf_objects.SignedBinaryID.BinaryType.EXECUTABLE,
        args.platform,
        upload_subdirectory=args.upload_subdirectory)

  elif args.subparser_name == "set_var":
    var = args.var
    val = args.val

    config = grr_config.CONFIG
    print("Setting %s to %s" % (var, val))
    if val.startswith("["):  # Allow setting of basic lists.
      val = val[1:-1].split(",")
    config.Set(var, val)
    config.Write()

  elif args.subparser_name == "switch_datastore":
    config_updater_util.SwitchToRelDB(grr_config.CONFIG)
    grr_config.CONFIG.Write()

  elif args.subparser_name == "upload_artifact":
    with io.open(args.file, "r") as filedesc:
      source = filedesc.read()
    try:
      artifact.UploadArtifactYamlFile(source, overwrite=args.overwrite_artifact)
    except rdf_artifacts.ArtifactDefinitionError as e:
      print("Error %s. You may need to set --overwrite_artifact." % e)

  elif args.subparser_name == "delete_artifacts":
    artifact_list = args.artifact
    if not artifact_list:
      raise ValueError("No artifact to delete given.")
    artifact_registry.DeleteArtifactsFromDatastore(artifact_list, token=token)
    print("Artifacts %s deleted." % artifact_list)

  elif args.subparser_name == "rotate_server_key":
    print("""
You are about to rotate the server key. Note that:

  - Clients might experience intermittent connection problems after
    the server keys rotated.

  - It's not possible to go back to an earlier key. Clients that see a
    new certificate will remember the cert's serial number and refuse
    to accept any certificate with a smaller serial number from that
    point on.
    """)

    if input("Continue? [yN]: ").upper() == "Y":
      if args.keylength:
        keylength = int(args.keylength)
      else:
        keylength = grr_config.CONFIG["Server.rsa_key_length"]

      maintenance_utils.RotateServerKey(
          cn=args.common_name, keylength=keylength)


def Run():
  app.run(main, flags_parser=lambda argv: parser.parse_args(argv[1:]))


if __name__ == "__main__":
  Run()
