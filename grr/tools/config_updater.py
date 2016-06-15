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
import socket
import subprocess
import sys
import urlparse

import pkg_resources

# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=g-bad-import-order,unused-import

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import artifact
from grr.lib import artifact_registry
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import key_utils
from grr.lib import maintenance_utils
from grr.lib import rdfvalue
from grr.lib import rekall_profile_server
from grr.lib import repacking
from grr.lib import startup
from grr.lib import utils
from grr.lib.aff4_objects import users


class Error(Exception):
  """Base error class."""
  pass


class UserError(Error):
  pass


parser = flags.PARSER
parser.description = ("Set configuration parameters for the GRR Server."
                      "\nThis script has numerous subcommands to perform "
                      "various actions. When you are first setting up, you "
                      "probably only care about 'initialize'.")

# Generic arguments.

parser.add_argument("--share_dir",
                    default="/usr/share/grr",
                    help="Path to the directory containing grr data.")

subparsers = parser.add_subparsers(title="subcommands",
                                   dest="subparser_name",
                                   description="valid subcommands")

# Subparsers.
parser_generate_keys = subparsers.add_parser(
    "generate_keys",
    help="Generate crypto keys in the configuration.")

parser_repack_clients = subparsers.add_parser(
    "repack_clients",
    help="Repack the clients binaries with the current configuration.")

parser_initialize = subparsers.add_parser(
    "initialize",
    help="Run all the required steps to setup a new GRR install.")

parser_set_var = subparsers.add_parser("set_var", help="Set a config variable.")

# Update an existing user.
parser_update_user = subparsers.add_parser("update_user",
                                           help="Update user settings.")

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

parser_add_user.add_argument("--noadmin",
                             default=False,
                             action="store_true",
                             help="Don't create the user as an administrator.")

parser_initialize.add_argument("--external_hostname",
                               default=None,
                               help="External hostname to use.")

parser_initialize.add_argument("--admin_password",
                               default=None,
                               help="Admin password for web interface.")

parser_initialize.add_argument("--noprompt",
                               default=False,
                               action="store_true",
                               help="Set to avoid prompting during initialize.")

parser_set_var.add_argument("var", help="Variable to set.")
parser_set_var.add_argument("val", help="Value to set.")


def AddUser(username, password=None, labels=None, token=None):
  """Implementation of the add_user command."""
  try:
    if aff4.FACTORY.Open("aff4:/users/%s" % username,
                         users.GRRUser,
                         token=token):
      raise UserError("Cannot add user %s: User already exists." % username)
  except aff4.InstantiationError:
    pass

  fd = aff4.FACTORY.Create("aff4:/users/%s" % username,
                           users.GRRUser,
                           mode="rw",
                           token=token)
  # Note this accepts blank passwords as valid.
  if password is None:
    password = getpass.getpass(prompt="Please enter password for user '%s': " %
                               username)
  fd.SetPassword(password)

  if labels:
    fd.AddLabels(*set(labels), owner="GRR")

  fd.Close()

  print "Added user %s." % username


def UpdateUser(username,
               password,
               add_labels=None,
               delete_labels=None,
               token=None):
  """Implementation of the update_user command."""
  try:
    fd = aff4.FACTORY.Open("aff4:/users/%s" % username,
                           users.GRRUser,
                           mode="rw",
                           token=token)
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
    fd.AddLabels(*final_add_labels, owner="GRR")

  if final_del_labels:
    fd.RemoveLabels(*final_del_labels, owner="GRR")

  fd.Close()

  print "Updated user %s" % username

  ShowUser(username, token=token)

# Delete an existing user.
parser_update_user = subparsers.add_parser("delete_user",
                                           help="Delete an user account.")

parser_update_user.add_argument("username", help="Username to update.")


def DeleteUser(username, token=None):
  try:
    aff4.FACTORY.Open("aff4:/users/%s" % username, users.GRRUser, token=token)
  except aff4.InstantiationError:
    print "User %s not found." % username
    return

  aff4.FACTORY.Delete("aff4:/users/%s" % username, token=token)
  print "User %s has been deleted." % username

# Show user account.
parser_show_user = subparsers.add_parser(
    "show_user", help="Display user settings or list all users.")

parser_show_user.add_argument(
    "username",
    default=None,
    nargs="?",
    help="Username to display. If not specified, list all users.")


def ShowUser(username, token=None):
  """Implementation of the show_user command."""
  if username is None:
    fd = aff4.FACTORY.Open("aff4:/users", token=token)
    for user in fd.OpenChildren():
      if isinstance(user, users.GRRUser):
        print user.Describe()
  else:
    user = aff4.FACTORY.Open("aff4:/users/%s" % username, token=token)
    if isinstance(user, users.GRRUser):
      print user.Describe()
    else:
      print "User %s not found" % username

# Generate Keys Arguments
parser_generate_keys.add_argument("--overwrite_keys",
                                  default=False,
                                  action="store_true",
                                  help="Required to overwrite existing keys.")

# Repack arguments.
parser_repack_clients.add_argument(
    "--upload",
    default=True,
    action="store_false",
    help="Upload the client binaries to the datastore.")

# Parent parser used in other upload based parsers.
parser_upload_args = argparse.ArgumentParser(add_help=False)
parser_upload_signed_args = argparse.ArgumentParser(add_help=False)

# Upload arguments.
parser_upload_args.add_argument("--file",
                                help="The file to upload",
                                required=True)

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

parser_upload_artifact.add_argument("--overwrite_artifact",
                                    default=False,
                                    action="store_true",
                                    help="Overwrite existing artifact.")

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

parser_sign_component = subparsers.add_parser(
    "sign_component",
    parents=[],
    help="Authenticode Sign the component.")

parser_sign_component.add_argument(
    "component_filename",
    help="Path to the compiled component to upload.")

parser_sign_component.add_argument(
    "output_filename",
    help="Path to write the signed component file.")

parser_upload_component = subparsers.add_parser(
    "upload_component",
    parents=[],
    help="Sign and upload a client component.")

parser_upload_component.add_argument(
    "component_filename",
    help="Path to the compiled component to upload.")

parser_upload_component.add_argument(
    "--overwrite_component",
    default=False,
    action="store_true",
    help="Allow overwriting of the component path.")

parser_upload_components = subparsers.add_parser(
    "upload_components",
    parents=[],
    help="Sign and upload all client components.")

subparsers.add_parser(
    "download_missing_rekall_profiles",
    parents=[],
    help="Downloads all Rekall profiles from the repository that are not "
    "currently present in the database.")


def ImportConfig(filename, config):
  """Reads an old config file and imports keys and user accounts."""
  sections_to_import = ["PrivateKeys"]
  entries_to_import = ["Client.executable_signing_public_key", "CA.certificate",
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


def GenerateKeys(config, overwrite_keys=False):
  """Generate the keys we need for a GRR server."""
  if not hasattr(key_utils, "MakeCACert"):
    parser.error("Generate keys can only run with open source key_utils.")
  if (config.Get("PrivateKeys.server_key",
                 default=None) and not overwrite_keys):
    print config.Get("PrivateKeys.server_key")
    raise RuntimeError("Config %s already has keys, use --overwrite_keys to "
                       "override." % config.parser)

  length = config_lib.CONFIG["Server.rsa_key_length"]
  print "All keys will have a bit length of %d." % length
  print "Generating executable signing key"
  priv_key, pub_key = key_utils.GenerateRSAKey(key_length=length)
  config.Set("PrivateKeys.executable_signing_private_key", priv_key)
  config.Set("Client.executable_signing_public_key", pub_key)

  print "Generating CA keys"
  ca_cert, ca_pk, _ = key_utils.MakeCACert(bits=length)
  cipher = None
  config.Set("CA.certificate", ca_cert.as_pem())
  config.Set("PrivateKeys.ca_key", ca_pk.as_pem(cipher))

  print "Generating Server keys"
  server_cert, server_key = key_utils.MakeCASignedCert("grr",
                                                       ca_pk,
                                                       bits=length)
  config.Set("Frontend.certificate", server_cert.as_pem())
  config.Set("PrivateKeys.server_key", server_key.as_pem(cipher))

  print "Generating Django Secret key (used for xsrf protection etc)"
  GenerateDjangoKey(config)


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


def ConfigureHostnames(config):
  """This configures the hostnames stored in the config."""
  if flags.FLAGS.external_hostname:
    hostname = flags.FLAGS.external_hostname
  else:
    try:
      hostname = socket.gethostname()
    except (OSError, IOError):
      print "Sorry, we couldn't guess your hostname.\n"

    hostname = RetryQuestion("Please enter your hostname e.g. "
                             "grr.example.com", "^[\\.A-Za-z0-9-]+$", hostname)

  print """\n\n-=Server URL=-
The Server URL specifies the URL that the clients will connect to
communicate with the server. For best results this should be publicly
accessible. By default this will be port 8080 with the URL ending in /control.
"""
  frontend_url = RetryQuestion("Frontend URL", "^http://.*/$",
                               "http://%s:8080/" % hostname)
  config.Set("Client.server_urls", [frontend_url])

  frontend_port = urlparse.urlparse(frontend_url).port or config_lib.CONFIG.Get(
      "Frontend.bind_port")
  config.Set("Frontend.bind_port", frontend_port)

  print """\n\n-=AdminUI URL=-:
The UI URL specifies where the Administrative Web Interface can be found.
"""
  ui_url = RetryQuestion("AdminUI URL", "^http[s]*://.*$",
                         "http://%s:8000" % hostname)
  config.Set("AdminUI.url", ui_url)
  ui_port = urlparse.urlparse(ui_url).port or config_lib.CONFIG.Get(
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
        "Datastore Location", ".*", config_lib.CONFIG.Get("Datastore.location"))
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
                               config_lib.CONFIG.Get("Mysql.host"))
    config.Set("Mysql.host", mysql_host)

    mysql_port = RetryQuestion("MySQL Port (0 for local socket)", "^[0-9]+$",
                               config_lib.CONFIG.Get("Mysql.port"))
    config.Set("Mysql.port", mysql_port)

    mysql_database = RetryQuestion("MySQL Database", "^[A-Za-z0-9-]+$",
                                   config_lib.CONFIG.Get("Mysql.database_name"))
    config.Set("Mysql.database_name", mysql_database)

    mysql_username = RetryQuestion(
        "MySQL Username", "[A-Za-z0-9-]+$",
        config_lib.CONFIG.Get("Mysql.database_username"))
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
                         config_lib.CONFIG.Get("Logging.domain"))
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

  existing_datastore = config_lib.CONFIG.Get("Datastore.implementation")

  if not existing_datastore or existing_datastore == "FakeDataStore":
    ConfigureDatastore(config)
  else:
    print """Found existing settings:
  Datastore: %s""" % existing_datastore

    if existing_datastore == "SqliteDataStore":
      print """  Datastore Location: %s
      """ % config_lib.CONFIG.Get("Datastore.location")

    if existing_datastore == "MySQLAdvancedDataStore":
      print """  MySQL Host: %s
  MySQL Port: %s
  MySQL Database: %s
  MySQL Username: %s
  """ % (config_lib.CONFIG.Get("Mysql.host"),
         config_lib.CONFIG.Get("Mysql.port"),
         config_lib.CONFIG.Get("Mysql.database_name"),
         config_lib.CONFIG.Get("Mysql.database_username"))

    if raw_input("Do you want to keep this configuration?"
                 " [Yn]: ").upper() == "N":
      ConfigureDatastore(config)

  print """\n\n-=GRR URLs=-
For GRR to work each client has to be able to communicate with the server. To do
this we normally need a public dns name or IP address to communicate with. In
the standard configuration this will be used to host both the client facing
server and the admin user interface.\n"""

  existing_ui_urn = config_lib.CONFIG.Get("AdminUI.url", default=None)
  existing_frontend_urns = config_lib.CONFIG.Get("Client.server_urls")
  if not existing_frontend_urns:
    # Port from older deprecated setting Client.control_urls.
    existing_control_urns = config_lib.CONFIG.Get("Client.control_urls",
                                                  default=None)
    if existing_control_urns is not None:
      existing_frontend_urns = []
      for existing_control_urn in existing_control_urns:
        if not existing_control_urn.endswith("control"):
          raise RuntimeError("Invalid existing control URL: %s" %
                             existing_control_urn)

        existing_frontend_urns.append(existing_control_urn.rsplit("/", 1)[0] +
                                      "/")

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

  existing_log_domain = config_lib.CONFIG.Get("Logging.domain", default=None)
  existing_al_email = config_lib.CONFIG.Get("Monitoring.alert_email",
                                            default=None)

  existing_em_email = config_lib.CONFIG.Get("Monitoring.emergency_access_email",
                                            default=None)
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

  config.Set("Server.initialized", True)
  config.Write()
  print("Configuration parameters set. You can edit these in %s" %
        config_lib.CONFIG.Get("Config.writeback"))


def AddUsers(token=None):
  # Now initialize with our modified config.
  startup.Init()

  print "\nStep 3: Adding Admin User"
  try:
    AddUser("admin",
            labels=["admin"],
            token=token,
            password=flags.FLAGS.admin_password)
  except UserError:
    if flags.FLAGS.noprompt:
      UpdateUser("admin",
                 password=flags.FLAGS.admin_password,
                 add_labels=["admin"],
                 token=token)
    else:
      if ((raw_input("User 'admin' already exists, do you want to "
                     "reset the password? [yN]: ").upper() or "N") == "Y"):
        UpdateUser("admin", password=True, add_labels=["admin"], token=token)


def InstallTemplatePackage():
  virtualenv_bin = os.path.dirname(sys.executable)
  pip = "%s/pip" % virtualenv_bin
  # Install the GRR server component to satisfy the dependency below.
  major_minor_version = ".".join(pkg_resources.get_distribution(
      "grr-response-core").version.split(".")[0:2])
  # Note that this version spec requires a recent version of pip
  subprocess.check_call(
      [sys.executable, pip, "install", "--upgrade", "-f",
       "https://storage.googleapis.com/releases.grr-response.com/index.html",
       "grr-response-templates==%s.*" % major_minor_version])


def ManageBinaries(config=None, token=None):
  """Repack templates into installers."""
  print("\nStep 4: Installing template package and repackaging clients with"
        " new configuration.")

  if flags.FLAGS.noprompt or ((raw_input(
      "Download and upgrade client templates? You can skip this if "
      "templates are already installed. [Yn]: ").upper() or "Y") == "Y"):
    InstallTemplatePackage()

  # Build debug binaries, then build release binaries.
  repacking.TemplateRepacker().RepackAllTemplates(upload=True, token=token)
  print "\nStep 5: Signing and uploading client components."

  maintenance_utils.SignAllComponents(token=token)

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
  config_dict["Client.server_urls"] = ["http://%s:%s/" %
                                       (hostname,
                                        config.Get("Frontend.bind_port"))]

  config_dict["AdminUI.url"] = "http://%s:%s" % (hostname,
                                                 config.Get("AdminUI.port"))
  config_dict["Logging.domain"] = hostname
  config_dict["Monitoring.alert_email"] = "grr-monitoring@%s" % hostname
  config_dict["Monitoring.emergency_access_email"] = ("grr-emergency@%s" %
                                                      hostname)

  print "Setting configuration as:\n\n%s" % config_dict
  for key, value in config_dict.iteritems():
    config.Set(key, value)
  config.Set("Server.initialized", True)
  config.Write()

  print("Configuration parameters set. You can edit these in %s" %
        config_lib.CONFIG.Get("Config.writeback"))
  AddUsers(token=token)
  ManageBinaries(config, token=token)


def UploadRaw(file_path, aff4_path, token=None):
  """Upload a file to the datastore."""
  full_path = rdfvalue.RDFURN(aff4_path).Add(os.path.basename(file_path))
  fd = aff4.FACTORY.Create(full_path, "AFF4Image", mode="w", token=token)
  fd.Write(open(file_path).read(1024 * 1024 * 30))
  fd.Close()
  return str(fd.urn)


def GetToken():
  # Extend for user authorization
  # SetUID is required to create and write to various aff4 paths when updating
  # config.
  return access_control.ACLToken(username="GRRConsole").SetUID()


def main(unused_argv):
  """Main."""
  token = GetToken()
  config_lib.CONFIG.AddContext("Commandline Context")
  config_lib.CONFIG.AddContext("ConfigUpdater Context")

  if flags.FLAGS.subparser_name == "initialize":
    startup.ConfigInit()
    if flags.FLAGS.noprompt:
      InitializeNoPrompt(config_lib.CONFIG, token=token)
    else:
      Initialize(config_lib.CONFIG, token=token)
    return

  startup.Init()

  try:
    print "Using configuration %s" % config_lib.CONFIG
  except AttributeError:
    raise RuntimeError("No valid config specified.")

  if flags.FLAGS.subparser_name == "generate_keys":
    try:
      GenerateKeys(config_lib.CONFIG, overwrite_keys=flags.FLAGS.overwrite_keys)
    except RuntimeError, e:
      # GenerateKeys will raise if keys exist and overwrite_keys is not set.
      print "ERROR: %s" % e
      sys.exit(1)
    config_lib.CONFIG.Write()

  elif flags.FLAGS.subparser_name == "repack_clients":
    repacking.TemplateRepacker().RepackAllTemplates(upload=flags.FLAGS.upload,
                                                    token=token)

  elif flags.FLAGS.subparser_name == "show_user":
    ShowUser(flags.FLAGS.username, token=token)

  elif flags.FLAGS.subparser_name == "update_user":
    try:
      UpdateUser(flags.FLAGS.username,
                 flags.FLAGS.password,
                 flags.FLAGS.add_labels,
                 flags.FLAGS.delete_labels,
                 token=token)
    except UserError as e:
      print e

  elif flags.FLAGS.subparser_name == "delete_user":
    DeleteUser(flags.FLAGS.username, token=token)

  elif flags.FLAGS.subparser_name == "add_user":
    labels = []
    if not flags.FLAGS.noadmin:
      labels.append("admin")

    if flags.FLAGS.labels:
      labels.extend(flags.FLAGS.labels)

    try:
      AddUser(flags.FLAGS.username, flags.FLAGS.password, labels, token=token)
    except UserError as e:
      print e

  elif flags.FLAGS.subparser_name == "upload_python":
    content = open(flags.FLAGS.file).read(1024 * 1024 * 30)
    aff4_path = flags.FLAGS.dest_path
    if not aff4_path:
      python_hack_root_urn = config_lib.CONFIG.Get("Config.python_hack_root")
      aff4_path = python_hack_root_urn.Add(os.path.basename(flags.FLAGS.file))
    context = ["Platform:%s" % flags.FLAGS.platform.title(), "Client Context"]
    maintenance_utils.UploadSignedConfigBlob(content,
                                             aff4_path=aff4_path,
                                             client_context=context,
                                             token=token)

  elif flags.FLAGS.subparser_name == "upload_exe":
    content = open(flags.FLAGS.file).read(1024 * 1024 * 30)
    context = ["Platform:%s" % flags.FLAGS.platform.title(), "Client Context"]

    if flags.FLAGS.dest_path:
      dest_path = rdfvalue.RDFURN(flags.FLAGS.dest_path)
    else:
      dest_path = config_lib.CONFIG.Get(
          "Executables.aff4_path",
          context=context).Add(os.path.basename(flags.FLAGS.file))

    # Now upload to the destination.
    maintenance_utils.UploadSignedConfigBlob(content,
                                             aff4_path=dest_path,
                                             client_context=context,
                                             token=token)

    print "Uploaded to %s" % dest_path

  elif flags.FLAGS.subparser_name == "sign_component":
    maintenance_utils.SignComponentContent(flags.FLAGS.component_filename,
                                           flags.FLAGS.output_filename)

  elif flags.FLAGS.subparser_name == "upload_component":
    maintenance_utils.SignComponent(flags.FLAGS.component_filename,
                                    overwrite=flags.FLAGS.overwrite_component,
                                    token=token)

  elif flags.FLAGS.subparser_name == "upload_components":
    maintenance_utils.SignAllComponents(
        overwrite=flags.FLAGS.overwrite_component,
        token=token)

  elif flags.FLAGS.subparser_name == "set_var":
    config = config_lib.CONFIG
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
    json.load(open(flags.FLAGS.file))  # Check it will parse.
    base_urn = aff4.ROOT_URN.Add("artifact_store")
    try:
      artifact.UploadArtifactYamlFile(
          open(flags.FLAGS.file).read(1000000),
          base_urn=base_urn,
          token=None,
          overwrite=flags.FLAGS.overwrite_artifact)
    except artifact_registry.ArtifactDefinitionError as e:
      print "Error %s. You may need to set --overwrite_artifact." % e

  elif flags.FLAGS.subparser_name == "download_missing_rekall_profiles":
    print "Downloading missing Rekall profiles."
    s = rekall_profile_server.GRRRekallProfileServer()
    s.GetMissingProfiles()


if __name__ == "__main__":
  flags.StartMain(main)
