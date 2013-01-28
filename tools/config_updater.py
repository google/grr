#!/usr/bin/env python
"""Util for modifying the GRR server configuration."""



import argparse
import ConfigParser
import getpass
import os
import sys


from grr.client import conf
from grr.client import conf as flags

from grr.lib import aff4
from grr.lib import build
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import key_utils
from grr.lib import maintenance_utils
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import server_plugins  # pylint: disable=W0611


parser = argparse.ArgumentParser(
    description="Set configuration parameters for the GRR Server.\nThis script "
    "has numerous subcommands to perform various actions. When you are first "
    "setting up, you probably only care about 'initialize'.")

# Generic arguments.

parser.add_argument(
    "--share_dir", default="/usr/share/grr",
    help="Path to the directory containing grr data.")

# Allow arguments we need from FLAGS to pass through argparse unhindered.
# TODO(user): Clean this up once we deprecate most of flags.
parser.add_argument("--config")

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


# Upload arguments.
parser_upload_args.add_argument(
    "--file", help="The file to upload", required=True)

parser_upload_args.add_argument(
    "--platform", required=True, choices=maintenance_utils.SUPPORTED_PLATFORMS,
    default="windows",
    help="The platform the file will be used on. This determines which signing"
    " keys to use, and the path on the server the file will be uploaded to.")

# Upload parsers.
parser_upload_python = subparsers.add_parser(
    "upload_python", parents=[parser_upload_args],
    help="Sign and upload a 'python hack' which can be used to execute code on "
    "a client.")

parser_upload_exe = subparsers.add_parser(
    "upload_exe", parents=[parser_upload_args],
    help="Sign and upload an executable which can be used to execute code on "
    "a client.")

parser_upload_memory_driver = subparsers.add_parser(
    "upload_memory_driver", parents=[parser_upload_args],
    help="Sign and upload a memory driver for a specific platform.")


FLAGS = flags.FLAGS
CONFIG = config_lib.CONFIG
CONFIG.flag_sections.append("ServerFlags")

args = parser.parse_args()


def LoadMemoryDrivers(grr_dir):
  """Load memory drivers from disk to database."""

  f_path = os.path.join(grr_dir, CONFIG["MemoryDriverDarwin.driver_file_64"])
  up_path = maintenance_utils.UploadSignedDriverBlob(
      open(f_path).read(), config=CONFIG, platform="Darwin",
      file_name="osxpmem")
  print "uploaded %s" % up_path

  f_path = os.path.join(grr_dir, CONFIG["MemoryDriverWindows.driver_file_32"])
  up_path = maintenance_utils.UploadSignedDriverBlob(
      open(f_path).read(), config=CONFIG, platform="Windows",
      file_name="winpmem.32.sys")
  print "uploaded %s" % up_path

  f_path = os.path.join(grr_dir, CONFIG["MemoryDriverWindows.driver_file_64"])
  up_path = maintenance_utils.UploadSignedDriverBlob(
      open(f_path).read(), config=CONFIG, platform="Windows",
      file_name="winpmem.64.sys")
  print "uploaded %s" % up_path


def GenerateDjangoKey(config):
  """Update a config with a random django key."""
  try:
    secret_key = config["ServerFlags.django_secret_key"]
  except ConfigParser.NoOptionError:
    secret_key = "CHANGE_ME"  # This is the config file default.

  if secret_key.strip().upper() == "CHANGE_ME":
    key = key_utils.GeneratePassphrase(length=100)
    config["ServerFlags.django_secret_key"] = key
  else:
    print "Not updating django_secret_key as it is already set."


def GenerateKeys(config):
  """Generate the keys we need for a GRR server."""
  if not hasattr(key_utils, "MakeCACert"):
    parser.error("Generate keys can only run with open source key_utils.")
  if (config.has_option("ServerKeys", "server_private_key")
      and not args.overwrite):
    raise RuntimeError("Config %s already has keys, use --overwrite to "
                       "override." % config.config_filename)

  required_sections = ["ClientSigningKeys", "ClientSigningKeysWindows",
                       "ClientSigningKeysDarwin", "ClientSigningKeysLinux",
                       "ServerKeys"]
  for section in required_sections:
    if not config.has_section(section):
      config.add_section(section)

  print "Generating executable signing key"
  priv_key, pub_key = key_utils.GenerateRSAKey()
  config.set("ClientSigningKeys", "executable_signing_private_key", priv_key)
  config.set("ClientSigningKeys", "executable_signing_public_key", pub_key)

  print "Generating driver signing key"
  priv_key, pub_key = key_utils.GenerateRSAKey()
  section = "ClientSigningKeys"
  config.set(section, "driver_signing_private_key", priv_key)
  config.set(section, "driver_signing_public_key", pub_key)
  # Add OS specific inherit sections.
  config.set("ClientSigningKeysWindows", "@inherit_from_section", section)
  config.set("ClientSigningKeysLinux", "@inherit_from_section", section)
  config.set("ClientSigningKeysDarwin", "@inherit_from_section", section)

  print "Generating CA keys"
  ca_cert, ca_pk, _ = key_utils.MakeCACert()
  cipher = None
  config.set("ServerKeys", "ca_public_cert", ca_cert.as_pem())
  config.set("ServerKeys", "ca_private_key", ca_pk.as_pem(cipher) +
             ca_cert.as_pem())

  print "Generating Server keys"
  server_cert, server_key = key_utils.MakeCASignedCert("grr", ca_pk, bits=2048)
  config.set("ServerKeys", "server_public_cert", server_cert.as_pem())
  config.set("ServerKeys", "server_private_key", server_key.as_pem(cipher) +
             server_cert.as_pem())

  print "Generating Django Secret key (used for xsrf protection etc)"
  GenerateDjangoKey(config)


def ConfigureBaseOptions(config):
  """Configure the basic options required to run the server."""

  # TODO(user): Many of these use the ServerFlags section but need to be moved
  # when the next config refactor happens.

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
  config["ClientBuild.location"] = location

  print """\nUI URL:
The UI URL specifies where the Administrative Web Interface can be found.
"""
  def_url = "http://%s:8000" % hostname
  ui_url = raw_input("UI URL [%s]: " % def_url) or def_url
  config["ServerFlags.ui_url"] = ui_url

  print """\nMonitoring email address
Address where monitoring events get sent, e.g. crashed clients, broken server
etc.
"""
  def_email = "grr-emergency@example.com"
  email = raw_input("Monitoring email [%s]: " % def_email) or def_email
  config["ServerFlags.monitoring_email"] = email

  print """\nEmergency email address
Address where high priority events such as an emergency ACL bypass are sent.
"""
  def_email = "grr-emergency@example.com"
  emergency_email = raw_input("Emergency email [%s]: " % email) or email
  config["ServerFlags.grr_emergency_email_address"] = emergency_email

  print "\nConfiguration completed"
  print_config = ((raw_input("Would you like to review the config before"
                             " writing it? [Yn]: ") or "Y").upper() == "Y")
  if print_config:
    print config.FormattedAsString(truncate_len=80)

  config.WriteConfig()
  print ("Configuration parameters set. You can edit these in %s" %
         config.config_filename)


def Initialize(config):
  """Initialize or update a GRR configuration."""
  print "Checking read access on config %s" % config.config_filename
  if not os.access(config.config_filename, os.W_OK):
    raise IOError("Config not writeable (need sudo?)")
  print "\nStep 1: Key Generation"
  if config.has_option("ServerKeys", "server_private_key"):
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
  ConfigureBaseOptions(CONFIG)

  print "\nStep 4: Repackaging clients with new configuration."
  RepackAndUpload(CONFIG, args.share_dir, upload=True)


def RepackAndUpload(config, share_dir, upload=True):
  """Repack all clients and upload them."""
  py_dir = os.path.dirname(os.path.realpath(__file__))
  build_files_dir = os.path.join(os.path.dirname(py_dir), "config")
  exe_dir = os.path.join(share_dir, "executables")
  built = build.RepackAllBinaries(build_files_dir=build_files_dir,
                                  config=config, exe_dir=exe_dir)
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
            file_name=os.path.basename(file_path), config=CONFIG)
      print "Uploaded to %s" % up


def UploadSigned(file_path, platform, config):
  """Sign an executable file and upload it to the datastore."""
  return maintenance_utils.UploadSignedConfigBlob(
      open(file_path).read(1024*1024*30), file_name=os.path.basename(file_path),
      config=config, platform=platform)


def UploadRaw(file_path, aff4_path):
  """Upload a file to the datastore."""
  full_path = rdfvalue.RDFURN(aff4_path).Add(os.path.basename(file_path))
  fd = aff4.FACTORY.Create(full_path, "AFF4Image", mode="w")
  fd.Write(open(file_path).read(1024*1024*30))
  fd.Close()
  return str(fd.urn)


def UpdateConfig():
  """Write the current config out to the config file."""
  with open(args.config, "w") as conf_fd:
    CONFIG.write(conf_fd)
    print "Wrote updated configuration to %s" % args.config


def main(unused_argv):
  """Main."""
  registry.Init()

  print "Using configuration %s" % CONFIG.config_filename

  if args.subparser_name == "load_memory_drivers":
    LoadMemoryDrivers(args.share_dir)

  elif args.subparser_name == "generate_keys":
    try:
      GenerateKeys(CONFIG)
    except RuntimeError, e:
      # GenerateKeys will raise if keys exist and --overwrite is not set.
      print "ERROR: %s" % e
      sys.exit(1)
    CONFIG.WriteConfig()

  elif args.subparser_name == "repack_clients":
    RepackAndUpload(CONFIG, args.share_dir, upload=args.upload)

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
    Initialize(CONFIG)

  elif args.subparser_name == "upload_python":
    uploaded = maintenance_utils.UploadSignedConfigBlob(
        open(args.file).read(1024*1024*30), config=CONFIG,
        file_name=os.path.basename(args.file), platform=args.platform,
        aff4_path="/config/python_hacks/{file_name}")
    print "Uploaded to %s" % uploaded

  elif args.subparser_name == "upload_exe":
    uploaded = maintenance_utils.UploadSignedConfigBlob(
        open(args.file).read(1024*1024*30), config=CONFIG,
        file_name=os.path.basename(args.file), platform=args.platform)
    print "Uploaded to %s" % uploaded

  elif args.subparser_name == "upload_memory_driver":
    uploaded = maintenance_utils.UploadSignedDriverBlob(
        open(args.file).read(1024*1024*30), config=CONFIG,
        platform=args.platform, file_name=os.path.basename(args.file))
    print "Uploaded to %s" % uploaded


def ConsoleMain():
  """Helper function for calling with setup tools entry points."""
  conf.StartMain(main)


if __name__ == "__main__":
  ConsoleMain()
