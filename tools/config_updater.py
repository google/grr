#!/usr/bin/env python
"""Util for modifying the GRR server configuration."""



import argparse
import ConfigParser
import getpass
import os
# importing readline enables the raw_input calls to have history etc.
import readline  # pylint: disable=unused-import
import sys


from grr.client import conf

# pylint: disable=unused-import,g-bad-import-order
# Client pieces need to be imported and registered for repack_clients command.
from grr.client import client_plugins
from grr.client import installer
from grr.lib import server_plugins
# pylint: enable=g-bad-import-order,unused-import

from grr.client import conf

from grr.lib import aff4
from grr.lib import build
from grr.lib import config_lib
from grr.lib import data_store

# pylint: disable=g-import-not-at-top,no-name-in-module
try:
  # FIXME(dbilby): Temporary hack until key_utils is deprecated.
  from grr.lib import key_utils
except ImportError:
  pass

from grr.lib import maintenance_utils
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import utils

parser = conf.PARSER
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


# Parent parser used in other user based parsers.
parser_user_args = argparse.ArgumentParser(add_help=False)

# User arguments.
parser_user_args.add_argument(
    "--username", required=True,
    help="Username to create.")
parser_user_args.add_argument(
    "--noadmin", default=False, action="store_true",
    help="Don't create the user as an administrator.")
parser_user_args.add_argument(
    "--password", default=None,
    help="Password to set for the user. If None, user will be prompted.")
parser_user_args.add_argument(
    "--label", default=[], action="append",
    help="Labels to add to the user object. These are used to control access.")


parser_add_user = subparsers.add_parser(
    "add_user", parents=[parser_user_args],
    help="Add a user to the system.")

parser_update_user = subparsers.add_parser(
    "update_user", parents=[parser_user_args],
    help="Update user settings.")

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

parser_upload_signed_args.add_argument(
    "--platform", required=True, choices=maintenance_utils.SUPPORTED_PLATFORMS,
    default="windows",
    help="The platform the file will be used on. This determines which signing"
    " keys to use, and the path on the server the file will be uploaded to.")

# Upload parsers.
parser_upload_raw = subparsers.add_parser(
    "upload_raw", parents=[parser_upload_args],
    help="Upload a raw file to an aff4 path.")

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


args = None


def LoadMemoryDrivers(grr_dir):
  """Load memory drivers from disk to database."""

  f_path = os.path.join(
      grr_dir, config_lib.CONFIG["MemoryDriverDarwin.driver_file_64"])
  up_path = maintenance_utils.UploadSignedDriverBlob(
      open(f_path).read(), platform="Darwin", file_name="osxpmem")
  print "uploaded %s" % up_path

  f_path = os.path.join(
      grr_dir, config_lib.CONFIG["MemoryDriverWindows.driver_file_32"])
  up_path = maintenance_utils.UploadSignedDriverBlob(
      open(f_path).read(), platform="Windows", file_name="winpmem.32.sys")
  print "uploaded %s" % up_path

  f_path = os.path.join(
      grr_dir, config_lib.CONFIG["MemoryDriverWindows.driver_file_64"])
  up_path = maintenance_utils.UploadSignedDriverBlob(
      open(f_path).read(), platform="Windows", file_name="winpmem.64.sys")
  print "uploaded %s" % up_path


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
  if config["PrivateKeys.server_key"] and not args.overwrite:
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

  # Add OS specific inherit sections.
  config.Set("PrivateKeysWindows.@inherit_from_section", "PrivateKeys")
  config.Set("PrivateKeysLinux.@inherit_from_section", "PrivateKeys")
  config.Set("PrivateKeysDarwin.@inherit_from_section", "PrivateKeys")

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
  except OSError:
    print "Sorry, we couldn't guess your public hostname"
    hostname = raw_input(
        "Please enter it manually e.g. grr.example.com: ").strip()

  print """\n\nServer URL
The Server URL specifies the URL that the clients will connect to
communicate with the server. This needs to be publically accessible. By default
this will be port 8080 with the URL ending in /control.
"""
  def_location = "http://%s:8080/control" % hostname
  location = raw_input("Server URL [%s]: " % def_location) or def_location
  config.Set("Client.location", location)

  print """\nUI URL:
The UI URL specifies where the Administrative Web Interface can be found.
"""
  def_url = "http://%s:8000" % hostname
  ui_url = raw_input("AdminUI URL [%s]: " % def_url) or def_url
  config.Set("AdminUI.url", ui_url)

  print """\nMonitoring email address
Address where monitoring events get sent, e.g. crashed clients, broken server
etc.
"""
  def_email = "grr-emergency@example.com"
  email = raw_input("Monitoring email [%s]: " % def_email) or def_email
  config.Set("Monitoring.emergency_access_email", email)

  print """\nEmergency email address
Address where high priority events such as an emergency ACL bypass are sent.
"""
  def_email = "grr-emergency@example.com"
  emergency_email = raw_input("Emergency email [%s]: " % email) or email
  config.Set("Monitoring.emergency_access_email", emergency_email)

  config.Write()
  print ("Configuration parameters set. You can edit these in %s" %
         config.parser)


def Initialize(config):
  """Initialize or update a GRR configuration."""
  print "Checking read access on config %s" % config.parser
  if not os.access(config.parser.filename, os.W_OK):
    raise IOError("Config not writeable (need sudo?)")
  print "\nStep 1: Key Generation"
  if config["PrivateKeys.server_key"]:
    if ((raw_input("You already have keys in your config, do you want to"
                   " overwrite them? [yN]: ").upper() or "N") == "Y"):
      args.overwrite = True
      GenerateKeys(config)
  else:
    GenerateKeys(config)

  print "\nStep 2: Adding Admin User"
  password = getpass.getpass(prompt="Please enter password for user 'admin': ")
  data_store.DB.security_manager.user_manager.UpdateUser(
      "admin", password=password, admin=True)
  print "User admin added."

  print "\nStep 3: Uploading Memory Drivers to the Database"
  LoadMemoryDrivers(args.share_dir)

  print "\nStep 3: Setting Basic Configuration Parameters"
  ConfigureBaseOptions(config_lib.CONFIG)

  print "\nStep 4: Repackaging clients with new configuration."
  RepackAndUpload(os.path.join(args.share_dir, "executables"), upload=True)


def RepackAndUpload(executables_dir, upload=True):
  """Repack all clients and upload them."""
  built = build.RepackAllBinaries(executables_dir=executables_dir)
  if upload:
    print "\n## Uploading"
    for file_path, platform, arch in built:
      print "Uploading %s %s binary from %s" % (platform, arch, file_path)
      if platform == "Darwin":
        # Darwin currently doesn't do a full repack, just the config.
        up = UploadRaw(file_path, "/config/executables/darwin/installers")
      elif platform == "Windows":
        up = maintenance_utils.UploadSignedConfigBlob(
            open(file_path).read(1024*1024*30), platform=platform,
            file_name=os.path.basename(file_path))
      print "Uploaded to %s" % up


def UploadRaw(file_path, aff4_path):
  """Upload a file to the datastore."""
  full_path = rdfvalue.RDFURN(aff4_path).Add(os.path.basename(file_path))
  fd = aff4.FACTORY.Create(full_path, "AFF4Image", mode="w")
  fd.Write(open(file_path).read(1024*1024*30))
  fd.Close()
  return str(fd.urn)


def main(unused_argv):
  """Main."""
  registry.Init()
  global args  # pylint: disable=global-statement
  args=conf.FLAGS

  print "Using configuration %s" % config_lib.CONFIG.parser

  if args.subparser_name == "load_memory_drivers":
    LoadMemoryDrivers(args.share_dir)

  elif args.subparser_name == "generate_keys":
    try:
      GenerateKeys(config_lib.CONFIG)
    except RuntimeError, e:
      # GenerateKeys will raise if keys exist and --overwrite is not set.
      print "ERROR: %s" % e
      sys.exit(1)
    config_lib.CONFIG.Write()

  elif args.subparser_name == "repack_clients":
    RepackAndUpload(os.path.join(args.share_dir, "executables"),
                    upload=args.upload)

  if args.subparser_name == "add_user":
    if args.password:
      password = args.password
    else:
      password = getpass.getpass(prompt="Please enter password for user %s: " %
                                 args.username)
    admin = not args.noadmin
    data_store.DB.security_manager.user_manager.AddUser(
        args.username, password=password, admin=admin,
        labels=args.label)

  elif args.subparser_name == "update_user":
    admin = not args.noadmin
    data_store.DB.security_manager.user_manager.UpdateUser(
        args.username, password=args.password, admin=admin,
        labels=args.label)

  elif args.subparser_name == "initialize":
    Initialize(config_lib.CONFIG)

  elif args.subparser_name == "upload_python":
    content = open(args.file).read(1024*1024*30)
    if args.dest_path:
      uploaded = maintenance_utils.UploadSignedConfigBlob(
          content, platform=args.platform, aff4_path=args.dest_path)
    else:
      uploaded = maintenance_utils.UploadSignedConfigBlob(
          content, file_name=os.path.basename(args.file),
          platform=args.platform, aff4_path="/config/python_hacks/{file_name}")
    print "Uploaded to %s" % uploaded

  elif args.subparser_name == "upload_exe":
    content = open(args.file).read(1024*1024*30)
    if args.dest_path:
      uploaded = maintenance_utils.UploadSignedConfigBlob(
          content, aff4_path=args.dest_path, platform=args.platform)
    else:
      uploaded = maintenance_utils.UploadSignedConfigBlob(
          content, file_name=os.path.basename(args.file),
          platform=args.platform)
    print "Uploaded to %s" % uploaded

  elif args.subparser_name == "upload_memory_driver":
    content = open(args.file).read(1024*1024*30)
    if args.dest_path:
      uploaded = maintenance_utils.UploadSignedDriverBlob(
          content, platform=args.platform, aff4_path=args.dest_path)
    else:
      uploaded = maintenance_utils.UploadSignedDriverBlob(
          content, platform=args.platform,
          file_name=os.path.basename(args.file))
    print "Uploaded to %s" % uploaded

  elif args.subparser_name == "upload_raw":
    if not args.dest_path:
      args.dest_path = aff4.ROOT_URN.Add("config").Add("raw")
    uploaded = UploadRaw(args.file, args.dest_path)
    print "Uploaded to %s" % uploaded


def ConsoleMain():
  """Helper function for calling with setup tools entry points."""
  conf.StartMain(main)


if __name__ == "__main__":
  ConsoleMain()
