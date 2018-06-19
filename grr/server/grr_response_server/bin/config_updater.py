#!/usr/bin/env python
"""Util for modifying the GRR server configuration."""

import argparse
import getpass
import os

import re
# importing readline enables the raw_input calls to have history etc.
import readline  # pylint: disable=unused-import
import socket
import subprocess
import sys
import urlparse

import pkg_resources
import yaml

# pylint: disable=unused-import,g-bad-import-order
from grr.server.grr_response_server import server_plugins
# pylint: enable=g-bad-import-order,unused-import

from grr import config as grr_config
from grr.config import contexts
from grr.config import server as config_server
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import repacking
from grr.lib import utils
from grr.lib.rdfvalues import crypto as rdf_crypto
from grr.server.grr_response_server import access_control
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import artifact
from grr.server.grr_response_server import artifact_registry
from grr.server.grr_response_server import data_migration
from grr.server.grr_response_server import key_utils
from grr.server.grr_response_server import maintenance_utils
from grr.server.grr_response_server import rekall_profile_server
from grr.server.grr_response_server import server_startup
from grr.server.grr_response_server.aff4_objects import users as aff4_users

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
    choices=aff4_users.GlobalNotification.Type.enum_dict.keys(),
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


def ImportConfig(filename, config):
  """Reads an old config file and imports keys and user accounts."""
  sections_to_import = ["PrivateKeys"]
  entries_to_import = [
      "Client.executable_signing_public_key", "CA.certificate",
      "Frontend.certificate"
  ]
  options_imported = 0
  old_config = grr_config.CONFIG.MakeNewConfig()
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


def GenerateCSRFKey(config):
  """Update a config with a random csrf key."""
  secret_key = config.Get("AdminUI.csrf_secret_key", None)
  if not secret_key:
    # TODO(amoser): Remove support for django_secret_key.
    secret_key = config.Get("AdminUI.django_secret_key", None)
    if secret_key:
      config.Set("AdminUI.csrf_secret_key", secret_key)

  if not secret_key:
    key = utils.GeneratePassphrase(length=100)
    config.Set("AdminUI.csrf_secret_key", key)
  else:
    print "Not updating csrf key as it is already set."


def GenerateKeys(config, overwrite_keys=False):
  """Generate the keys we need for a GRR server."""
  if not hasattr(key_utils, "MakeCACert"):
    parser.error("Generate keys can only run with open source key_utils.")
  if (config.Get("PrivateKeys.server_key", default=None) and
      not overwrite_keys):
    print config.Get("PrivateKeys.server_key")
    raise RuntimeError("Config %s already has keys, use --overwrite_keys to "
                       "override." % config.parser)

  length = grr_config.CONFIG["Server.rsa_key_length"]
  print "All keys will have a bit length of %d." % length
  print "Generating executable signing key"
  executable_key = rdf_crypto.RSAPrivateKey.GenerateKey(bits=length)
  config.Set("PrivateKeys.executable_signing_private_key",
             executable_key.AsPEM())
  config.Set("Client.executable_signing_public_key",
             executable_key.GetPublicKey().AsPEM())

  print "Generating CA keys"
  ca_key = rdf_crypto.RSAPrivateKey.GenerateKey(bits=length)
  ca_cert = key_utils.MakeCACert(ca_key)
  config.Set("CA.certificate", ca_cert.AsPEM())
  config.Set("PrivateKeys.ca_key", ca_key.AsPEM())

  print "Generating Server keys"
  server_key = rdf_crypto.RSAPrivateKey.GenerateKey(bits=length)
  server_cert = key_utils.MakeCASignedCert(u"grr", server_key, ca_cert, ca_key)
  config.Set("Frontend.certificate", server_cert.AsPEM())
  config.Set("PrivateKeys.server_key", server_key.AsPEM())

  print "Generating secret key for csrf protection."
  GenerateCSRFKey(config)


def RetryQuestion(question_text, output_re="", default_val=None):
  """Continually ask a question until the output_re is matched."""
  while True:
    if default_val is not None:
      new_text = "%s [%s]: " % (question_text, default_val)
    else:
      new_text = "%s: " % question_text
    output = raw_input(new_text) or str(default_val)
    output = output.strip()
    if not output_re or re.match(output_re, output):
      break
    else:
      print "Invalid input, must match %s" % output_re
  return output


def RetryBoolQuestion(question_text, default_bool):
  if not isinstance(default_bool, bool):
    raise ValueError(
        "default_bool should be a boolean, not %s" % type(default_bool))
  default_val = "Y" if default_bool else "N"
  prompt_suff = "[Yn]" if default_bool else "[yN]"
  return RetryQuestion("%s %s: " % (question_text, prompt_suff), "[yY]|[nN]",
                       default_val)[0].upper() == "Y"


def ConfigureHostnames(config):
  """This configures the hostnames stored in the config."""
  if flags.FLAGS.external_hostname:
    hostname = flags.FLAGS.external_hostname
  else:
    try:
      hostname = socket.gethostname()
    except (OSError, IOError):
      print "Sorry, we couldn't guess your hostname.\n"

    hostname = RetryQuestion(
        "Please enter your hostname e.g. "
        "grr.example.com", "^[\\.A-Za-z0-9-]+$", hostname)

  print """\n\n-=Server URL=-
The Server URL specifies the URL that the clients will connect to
communicate with the server. For best results this should be publicly
accessible. By default this will be port 8080 with the URL ending in /control.
"""
  frontend_url = RetryQuestion("Frontend URL", "^http://.*/$",
                               "http://%s:8080/" % hostname)
  config.Set("Client.server_urls", [frontend_url])

  frontend_port = urlparse.urlparse(frontend_url).port or grr_config.CONFIG.Get(
      "Frontend.bind_port")
  config.Set("Frontend.bind_port", frontend_port)

  print """\n\n-=AdminUI URL=-:
The UI URL specifies where the Administrative Web Interface can be found.
"""
  ui_url = RetryQuestion("AdminUI URL", "^http[s]*://.*$",
                         "http://%s:8000" % hostname)
  config.Set("AdminUI.url", ui_url)
  ui_port = urlparse.urlparse(ui_url).port or grr_config.CONFIG.Get(
      "AdminUI.port")
  config.Set("AdminUI.port", ui_port)


def ConfigureDatastore(config):
  """Set the datastore to use by prompting the user to choose."""
  print """
1. SQLite (Default) - This datastore is stored on the local file system. If you
configure GRR to run as non-root be sure to allow that user access to the files.

2. MySQL - This datastore uses MySQL and requires MySQL 5.6 server or later
to be running and a user with the ability to create the GRR database and tables.
The MySQL client binaries are required for use with the MySQLdb python module as
well.
"""

  datastore = RetryQuestion("Datastore", "^[1-2]$", "1")

  if datastore == "1":
    config.Set("Datastore.implementation", "SqliteDataStore")
    datastore_location = RetryQuestion(
        "Datastore Location", ".*", grr_config.CONFIG.Get("Datastore.location"))
    if datastore_location:
      config.Set("Datastore.location", datastore_location)

  if datastore == "2":
    print """\n\n***WARNING***

Do not continue until a MySQL server, version 5.6 or greater, is running and a
user with the ability to create the GRR database and tables has been created.
You will need the server, username, password, and database name (if already
created) to continue. If no database has been created this script will attempt
to create the necessary database and tables using the credentials provided.

***WARNING***
"""
    while raw_input("Are you ready to continue?[Yn]: ").upper() != "Y":
      pass
    config.Set("Datastore.implementation", "MySQLAdvancedDataStore")
    mysql_host = RetryQuestion("MySQL Host", "^[\\.A-Za-z0-9-]+$",
                               grr_config.CONFIG.Get("Mysql.host"))
    config.Set("Mysql.host", mysql_host)

    mysql_port = RetryQuestion("MySQL Port (0 for local socket)", "^[0-9]+$",
                               grr_config.CONFIG.Get("Mysql.port"))
    config.Set("Mysql.port", mysql_port)

    mysql_database = RetryQuestion("MySQL Database", "^[A-Za-z0-9-]+$",
                                   grr_config.CONFIG.Get("Mysql.database_name"))
    config.Set("Mysql.database_name", mysql_database)

    mysql_username = RetryQuestion(
        "MySQL Username", "[A-Za-z0-9-]+$",
        grr_config.CONFIG.Get("Mysql.database_username"))
    config.Set("Mysql.database_username", mysql_username)

    mysql_password = getpass.getpass(
        prompt="Please enter password for database user %s: " % mysql_username)
    config.Set("Mysql.database_password", mysql_password)


def ConfigureEmails(config):
  """Configure email notification addresses."""
  print """\n\n-=Monitoring/Email Domain=-
Emails concerning alerts or updates must be sent to this domain.
"""
  domain = RetryQuestion("Email Domain e.g example.com",
                         "^([\\.A-Za-z0-9-]+)*$",
                         grr_config.CONFIG.Get("Logging.domain"))
  config.Set("Logging.domain", domain)

  print """\n\n-=Alert Email Address=-
Address where monitoring events get sent, e.g. crashed clients, broken server
etc.
"""
  email = RetryQuestion("Alert Email Address", "", "grr-monitoring@%s" % domain)
  config.Set("Monitoring.alert_email", email)

  print """\n\n-=Emergency Email Address=-
Address where high priority events such as an emergency ACL bypass are sent.
"""
  emergency_email = RetryQuestion("Emergency Access Email Address", "",
                                  "grr-emergency@%s" % domain)
  config.Set("Monitoring.emergency_access_email", emergency_email)


def ConfigureBaseOptions(config):
  """Configure the basic options required to run the server."""

  print "We are now going to configure the server using a bunch of questions."

  print """\n\n-=GRR Datastore=-
For GRR to work each GRR server has to be able to communicate with the
datastore.  To do this we need to configure a datastore.\n"""

  existing_datastore = grr_config.CONFIG.Get("Datastore.implementation")

  if not existing_datastore or existing_datastore == "FakeDataStore":
    ConfigureDatastore(config)
  else:
    print """Found existing settings:
  Datastore: %s""" % existing_datastore

    if existing_datastore == "SqliteDataStore":
      print """  Datastore Location: %s
      """ % grr_config.CONFIG.Get("Datastore.location")

    if existing_datastore == "MySQLAdvancedDataStore":
      print """  MySQL Host: %s
  MySQL Port: %s
  MySQL Database: %s
  MySQL Username: %s
  """ % (grr_config.CONFIG.Get("Mysql.host"),
         grr_config.CONFIG.Get("Mysql.port"),
         grr_config.CONFIG.Get("Mysql.database_name"),
         grr_config.CONFIG.Get("Mysql.database_username"))

    if raw_input("Do you want to keep this configuration?"
                 " [Yn]: ").upper() == "N":
      ConfigureDatastore(config)

  print """\n\n-=GRR URLs=-
For GRR to work each client has to be able to communicate with the server. To do
this we normally need a public dns name or IP address to communicate with. In
the standard configuration this will be used to host both the client facing
server and the admin user interface.\n"""

  existing_ui_urn = grr_config.CONFIG.Get("AdminUI.url", default=None)
  existing_frontend_urns = grr_config.CONFIG.Get("Client.server_urls")
  if not existing_frontend_urns:
    # Port from older deprecated setting Client.control_urls.
    existing_control_urns = grr_config.CONFIG.Get(
        "Client.control_urls", default=None)
    if existing_control_urns is not None:
      existing_frontend_urns = []
      for existing_control_urn in existing_control_urns:
        if not existing_control_urn.endswith("control"):
          raise RuntimeError(
              "Invalid existing control URL: %s" % existing_control_urn)

        existing_frontend_urns.append(
            existing_control_urn.rsplit("/", 1)[0] + "/")

      config.Set("Client.server_urls", existing_frontend_urns)
      config.Set("Client.control_urls", ["deprecated use Client.server_urls"])

  if not existing_frontend_urns or not existing_ui_urn:
    ConfigureHostnames(config)
  else:
    print """Found existing settings:
  AdminUI URL: %s
  Frontend URL(s): %s
""" % (existing_ui_urn, existing_frontend_urns)

    if raw_input("Do you want to keep this configuration?"
                 " [Yn]: ").upper() == "N":
      ConfigureHostnames(config)

  print """\n\n-=GRR Emails=-
  GRR needs to be able to send emails for various logging and
  alerting functions.  The email domain will be appended to GRR user names
  when sending emails to users.\n"""

  existing_log_domain = grr_config.CONFIG.Get("Logging.domain", default=None)
  existing_al_email = grr_config.CONFIG.Get(
      "Monitoring.alert_email", default=None)

  existing_em_email = grr_config.CONFIG.Get(
      "Monitoring.emergency_access_email", default=None)
  if not existing_log_domain or not existing_al_email or not existing_em_email:
    ConfigureEmails(config)
  else:
    print """Found existing settings:
  Email Domain: %s
  Alert Email Address: %s
  Emergency Access Email Address: %s
""" % (existing_log_domain, existing_al_email, existing_em_email)

    if raw_input("Do you want to keep this configuration?"
                 " [Yn]: ").upper() == "N":
      ConfigureEmails(config)
  rekall_enabled = grr_config.CONFIG.Get("Rekall.enabled", False)
  if rekall_enabled:
    rekall_enabled = RetryBoolQuestion("Keep Rekall enabled?", True)
  else:
    rekall_enabled = RetryBoolQuestion(
        "Rekall is no longer actively supported. Enable anyway?", False)
  config.Set("Rekall.enabled", rekall_enabled)
  config.Set("Server.initialized", True)
  config.Write()
  print("Configuration parameters set. You can edit these in %s" %
        grr_config.CONFIG.Get("Config.writeback"))


def AddUsers(token=None):
  # Now initialize with our modified config.
  server_startup.Init()

  print "\nStep 3: Adding Admin User"
  try:
    maintenance_utils.AddUser(
        "admin",
        labels=["admin"],
        token=token,
        password=flags.FLAGS.admin_password)
  except maintenance_utils.UserError:
    if flags.FLAGS.noprompt:
      maintenance_utils.UpdateUser(
          "admin",
          password=flags.FLAGS.admin_password,
          add_labels=["admin"],
          token=token)
    else:
      if ((raw_input("User 'admin' already exists, do you want to "
                     "reset the password? [yN]: ").upper() or "N") == "Y"):
        maintenance_utils.UpdateUser(
            "admin", password=True, add_labels=["admin"], token=token)


def InstallTemplatePackage():
  """Call pip to install the templates."""
  virtualenv_bin = os.path.dirname(sys.executable)
  extension = os.path.splitext(sys.executable)[1]
  pip = "%s/pip%s" % (virtualenv_bin, extension)

  # Install the GRR server component to satisfy the dependency below.
  major_minor_version = ".".join(
      pkg_resources.get_distribution("grr-response-core").version.split(".")[0:
                                                                             2])
  # Note that this version spec requires a recent version of pip
  subprocess.check_call([
      sys.executable, pip, "install", "--upgrade", "-f",
      "https://storage.googleapis.com/releases.grr-response.com/index.html",
      "grr-response-templates==%s.*" % major_minor_version
  ])


def ManageBinaries(config=None, token=None):
  """Repack templates into installers."""
  print "\nStep 4: Repackaging clients with new configuration."
  redownload_templates = False
  repack_templates = False

  if flags.FLAGS.noprompt:
    redownload_templates = flags.FLAGS.redownload_templates
    repack_templates = not flags.FLAGS.norepack_templates
  else:
    redownload_templates = RetryBoolQuestion(
        "Server debs include client templates. Re-download templates?", False)
    repack_templates = RetryBoolQuestion("Repack client templates?", True)

  if redownload_templates:
    InstallTemplatePackage()

  # Build debug binaries, then build release binaries.
  if repack_templates:
    repacking.TemplateRepacker().RepackAllTemplates(upload=True, token=token)

  print "\nInitialization complete, writing configuration."
  config.Write()
  print "Please restart the service for it to take effect.\n\n"


def Initialize(config=None, token=None):
  """Initialize or update a GRR configuration."""

  print "Checking write access on config %s" % config["Config.writeback"]
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
      print("Since you have imported keys from another installation in the "
            "last step,\nyou probably do not want to generate new keys now.")
    if (raw_input("You already have keys in your config, do you want to"
                  " overwrite them? [yN]: ").upper() or "N") == "Y":
      GenerateKeys(config, overwrite_keys=True)
  else:
    GenerateKeys(config)

  print "\nStep 2: Setting Basic Configuration Parameters"
  ConfigureBaseOptions(config)
  AddUsers(token=token)
  ManageBinaries(config, token=token)
  print "\nGRR Initialization complete!\n"


def InitializeNoPrompt(config=None, token=None):
  """Initialize GRR with no prompts, assumes SQLite db.

  Args:
    config: config object
    token: auth token

  Raises:
    ValueError: if hostname and password not supplied.
    IOError: if config is not writeable

  This method does the minimum work necessary to configure GRR without any user
  prompting, relying heavily on config default values. User must supply the
  external hostname and admin password, everything else is set automatically.
  """
  if not (flags.FLAGS.external_hostname and flags.FLAGS.admin_password):
    raise ValueError(
        "If interactive prompting is disabled, external_hostname and "
        "admin_password must be set.")

  print "Checking write access on config %s" % config.parser
  if not os.access(config.parser.filename, os.W_OK):
    raise IOError("Config not writeable (need sudo?)")

  config_dict = {}
  GenerateKeys(config)
  config_dict["Datastore.implementation"] = "SqliteDataStore"
  hostname = flags.FLAGS.external_hostname
  config_dict["Client.server_urls"] = [
      "http://%s:%s/" % (hostname, config.Get("Frontend.bind_port"))
  ]

  config_dict["AdminUI.url"] = "http://%s:%s" % (hostname,
                                                 config.Get("AdminUI.port"))
  config_dict["Logging.domain"] = hostname
  config_dict["Monitoring.alert_email"] = "grr-monitoring@%s" % hostname
  config_dict["Monitoring.emergency_access_email"] = (
      "grr-emergency@%s" % hostname)
  config_dict["Rekall.enabled"] = flags.FLAGS.enable_rekall
  print "Setting configuration as:\n\n%s" % config_dict
  for key, value in config_dict.iteritems():
    config.Set(key, value)
  config.Set("Server.initialized", True)
  config.Write()

  print("Configuration parameters set. You can edit these in %s" %
        grr_config.CONFIG.Get("Config.writeback"))
  AddUsers(token=token)
  ManageBinaries(config, token=token)


def UploadRaw(file_path, aff4_path, token=None):
  """Upload a file to the datastore."""
  full_path = rdfvalue.RDFURN(aff4_path).Add(os.path.basename(file_path))
  fd = aff4.FACTORY.Create(full_path, "AFF4Image", mode="w", token=token)
  fd.Write(open(file_path, "rb").read(1024 * 1024 * 30))
  fd.Close()
  return str(fd.urn)


def GetToken():
  # Extend for user authorization
  # SetUID is required to create and write to various aff4 paths when updating
  # config.
  return access_control.ACLToken(username="GRRConsole").SetUID()


def main(argv):
  """Main."""
  del argv  # Unused.

  token = GetToken()
  grr_config.CONFIG.AddContext(contexts.COMMAND_LINE_CONTEXT)
  grr_config.CONFIG.AddContext(contexts.CONFIG_UPDATER_CONTEXT)

  if flags.FLAGS.subparser_name == "initialize":
    config_lib.ParseConfigCommandLine()
    if flags.FLAGS.noprompt:
      InitializeNoPrompt(grr_config.CONFIG, token=token)
    else:
      Initialize(grr_config.CONFIG, token=token)
    return

  server_startup.Init()

  try:
    print "Using configuration %s" % grr_config.CONFIG
  except AttributeError:
    raise RuntimeError("No valid config specified.")

  if flags.FLAGS.subparser_name == "generate_keys":
    try:
      GenerateKeys(grr_config.CONFIG, overwrite_keys=flags.FLAGS.overwrite_keys)
    except RuntimeError, e:
      # GenerateKeys will raise if keys exist and overwrite_keys is not set.
      print "ERROR: %s" % e
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
      print e

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
      print e

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

    print "Uploaded to %s" % dest_path

  elif flags.FLAGS.subparser_name == "set_var":
    config = grr_config.CONFIG
    print "Setting %s to %s" % (flags.FLAGS.var, flags.FLAGS.val)
    if flags.FLAGS.val.startswith("["):  # Allow setting of basic lists.
      flags.FLAGS.val = flags.FLAGS.val[1:-1].split(",")
    config.Set(flags.FLAGS.var, flags.FLAGS.val)
    config.Write()

  elif flags.FLAGS.subparser_name == "upload_raw":
    if not flags.FLAGS.dest_path:
      flags.FLAGS.dest_path = aff4.ROOT_URN.Add("config").Add("raw")
    uploaded = UploadRaw(flags.FLAGS.file, flags.FLAGS.dest_path, token=token)
    print "Uploaded to %s" % uploaded

  elif flags.FLAGS.subparser_name == "upload_artifact":
    yaml.load(open(flags.FLAGS.file, "rb"))  # Check it will parse.
    try:
      artifact.UploadArtifactYamlFile(
          open(flags.FLAGS.file, "rb").read(),
          overwrite=flags.FLAGS.overwrite_artifact)
    except artifact_registry.ArtifactDefinitionError as e:
      print "Error %s. You may need to set --overwrite_artifact." % e

  elif flags.FLAGS.subparser_name == "delete_artifacts":
    artifact_list = flags.FLAGS.artifact
    if not artifact_list:
      raise ValueError("No artifact to delete given.")
    artifact_registry.DeleteArtifactsFromDatastore(artifact_list, token=token)
    print "Artifacts %s deleted." % artifact_list

  elif flags.FLAGS.subparser_name == "download_missing_rekall_profiles":
    print "Downloading missing Rekall profiles."
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

    print "Setting global notification."
    print notification

    with aff4.FACTORY.Create(
        aff4_users.GlobalNotificationStorage.DEFAULT_PATH,
        aff4_type=aff4_users.GlobalNotificationStorage,
        mode="rw",
        token=token) as storage:
      storage.AddNotification(notification)
  elif flags.FLAGS.subparser_name == "rotate_server_key":
    print """
You are about to rotate the server key. Note that:

  - Clients might experience intermittent connection problems after
    the server keys rotated.

  - It's not possible to go back to an earlier key. Clients that see a
    new certificate will remember the cert's serial number and refuse
    to accept any certificate with a smaller serial number from that
    point on.
    """

    if raw_input("Continue? [yN]: ").upper() == "Y":
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
