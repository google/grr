#!/usr/bin/env python
"""Utililies for modifying the GRR server configuration."""
from __future__ import absolute_import
from __future__ import division

from __future__ import print_function
from __future__ import unicode_literals

import getpass
import os
import re
import socket
import subprocess
import sys
import time


# Usually we import concrete items from the builtins module. However, here we
# use `builtins.input` which is stubbed in the test, so we have to always use
# qualified version.
from future import builtins
from future.moves.urllib import parse as urlparse
from future.utils import iteritems

import MySQLdb
from MySQLdb.constants import CR as mysql_conn_errors
from MySQLdb.constants import ER as general_mysql_errors
import pkg_resources

from typing import Optional, Text

# pylint: disable=unused-import,g-bad-import-order
from grr_response_server import server_plugins
# pylint: enable=g-bad-import-order,unused-import

from grr_api_client import errors as api_errors
from grr_response_client_builder import repacking
from grr_response_core import config as grr_config
from grr_response_server import access_control
from grr_response_server import maintenance_utils
from grr_response_server import server_startup
from grr_response_server.bin import config_updater_keys_util
from grr_response_server.gui.api_plugins import user as api_user

try:
  # Importing readline enables the raw_input calls to have history etc.
  import readline  # pylint: disable=unused-import,g-bad-import-order,g-import-not-at-top
except ImportError:
  # readline is not bundled with Python on Windows. Simply ignoring failing
  # import then.
  pass

# These control retry behavior when checking that GRR can connect to
# MySQL during config initialization.
_MYSQL_MAX_RETRIES = 2
_MYSQL_RETRY_WAIT_SECS = 2

# Python hacks or executables larger than this limit will not be uploaded.
_MAX_SIGNED_BINARY_BYTES = 100 << 20  # 100 MiB


class ConfigInitError(Exception):
  """Exception raised to abort config initialization."""

  def __init__(self):
    super(ConfigInitError, self).__init__(
        "Aborting config initialization. Please run 'grr_config_updater "
        "initialize' to retry initialization.")


class BinaryTooLargeError(Exception):
  """Exception raised when trying to upload overly large binaries."""


class UserAlreadyExistsError(Exception):
  """Exception raised when trying to create an already-existing user."""


class UserNotFoundError(Exception):
  """Exception raised when trying to fetch a non-existent user."""

  def __init__(self, username):
    super(UserNotFoundError,
          self).__init__("User '%s' does not exist." % username)


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

  for entry in old_config.raw_data:
    try:
      section = entry.split(".")[0]
      if section in sections_to_import or entry in entries_to_import:
        config.Set(entry, old_config.Get(entry))
        print("Imported %s." % entry)
        options_imported += 1

    except Exception as e:  # pylint: disable=broad-except
      print("Exception during import of %s: %s" % (entry, e))
  return options_imported


def RetryQuestion(question_text, output_re="", default_val=None):
  """Continually ask a question until the output_re is matched."""
  while True:
    if default_val is not None:
      new_text = "%s [%s]: " % (question_text, default_val)
    else:
      new_text = "%s: " % question_text
    # pytype: disable=wrong-arg-count
    output = builtins.input(new_text) or str(default_val)
    # pytype: enable=wrong-arg-count
    output = output.strip()
    if not output_re or re.match(output_re, output):
      break
    else:
      print("Invalid input, must match %s" % output_re)
  return output


def RetryBoolQuestion(question_text, default_bool):
  if not isinstance(default_bool, bool):
    raise ValueError("default_bool should be a boolean, not %s" %
                     type(default_bool))
  default_val = "Y" if default_bool else "N"
  prompt_suff = "[Yn]" if default_bool else "[yN]"
  return RetryQuestion("%s %s: " % (question_text, prompt_suff), "[yY]|[nN]",
                       default_val)[0].upper() == "Y"


def ConfigureHostnames(config, external_hostname = None):
  """This configures the hostnames stored in the config."""
  if not external_hostname:
    try:
      external_hostname = socket.gethostname()
    except (OSError, IOError):
      print("Sorry, we couldn't guess your hostname.\n")

    external_hostname = RetryQuestion(
        "Please enter your hostname e.g. "
        "grr.example.com", "^[\\.A-Za-z0-9-]+$", external_hostname)

  print("""\n\n-=Server URL=-
The Server URL specifies the URL that the clients will connect to
communicate with the server. For best results this should be publicly
accessible. By default this will be port 8080 with the URL ending in /control.
""")
  frontend_url = RetryQuestion("Frontend URL", "^http://.*/$",
                               "http://%s:8080/" % external_hostname)
  config.Set("Client.server_urls", [frontend_url])

  frontend_port = urlparse.urlparse(frontend_url).port or grr_config.CONFIG.Get(
      "Frontend.bind_port")
  config.Set("Frontend.bind_port", frontend_port)

  print("""\n\n-=AdminUI URL=-:
The UI URL specifies where the Administrative Web Interface can be found.
""")
  ui_url = RetryQuestion("AdminUI URL", "^http[s]*://.*$",
                         "http://%s:8000" % external_hostname)
  config.Set("AdminUI.url", ui_url)
  ui_port = urlparse.urlparse(ui_url).port or grr_config.CONFIG.Get(
      "AdminUI.port")
  config.Set("AdminUI.port", ui_port)


def CheckMySQLConnection(db_options):
  """Checks whether a connection can be established to MySQL.

  Args:
    db_options: A dict mapping GRR MySQL config options to their values.

  Returns:
    A boolean indicating whether a connection could be made to a MySQL server
    instance with the given options.
  """
  for tries_left in range(_MYSQL_MAX_RETRIES, -1, -1):
    try:
      connection_options = dict(
          host=db_options["Mysql.host"],
          port=db_options["Mysql.port"],
          db=db_options["Mysql.database_name"],
          user=db_options["Mysql.database_username"],
          passwd=db_options["Mysql.database_password"],
          charset="utf8")

      ssl_enabled = "Mysql.client_key_path" in db_options
      if ssl_enabled:
        connection_options["ssl"] = {
            "key": db_options["Mysql.client_key_path"],
            "cert": db_options["Mysql.client_cert_path"],
            "ca": db_options["Mysql.ca_cert_path"],
        }

      connection = MySQLdb.connect(**connection_options)

      if ssl_enabled:
        cursor = connection.cursor()
        cursor.execute("SHOW VARIABLES LIKE 'have_ssl'")
        res = cursor.fetchone()
        if res[0] == "have_ssl" and res[1] == "YES":
          print("SSL enabled successfully.")
        else:
          print("Unable to establish SSL connection to MySQL.")
          return False

      return True
    except MySQLdb.OperationalError as mysql_op_error:
      if len(mysql_op_error.args) < 2:
        # We expect the exception's arguments to be an error-code and
        # an error message.
        print("Unexpected exception type received from MySQL. %d attempts "
              "left: %s" % (tries_left, mysql_op_error))
        time.sleep(_MYSQL_RETRY_WAIT_SECS)
        continue
      if mysql_op_error.args[0] == mysql_conn_errors.CONNECTION_ERROR:
        print("Failed to connect to MySQL. Is it running? %d attempts left." %
              tries_left)
      elif mysql_op_error.args[0] == mysql_conn_errors.UNKNOWN_HOST:
        print("Unknown-hostname error encountered while trying to connect to "
              "MySQL.")
        return False  # No need for retry.
      elif mysql_op_error.args[0] == general_mysql_errors.BAD_DB_ERROR:
        # GRR db doesn't exist yet. That's expected if this is the initial
        # setup.
        return True
      elif mysql_op_error.args[0] in (
          general_mysql_errors.ACCESS_DENIED_ERROR,
          general_mysql_errors.DBACCESS_DENIED_ERROR):
        print("Permission error encountered while trying to connect to "
              "MySQL: %s" % mysql_op_error)
        return False  # No need for retry.
      else:
        print("Unexpected operational error encountered while trying to "
              "connect to MySQL. %d attempts left: %s" %
              (tries_left, mysql_op_error))
    except MySQLdb.Error as mysql_error:
      print("Unexpected error encountered while trying to connect to MySQL. "
            "%d attempts left: %s" % (tries_left, mysql_error))
    time.sleep(_MYSQL_RETRY_WAIT_SECS)
  return False


def ConfigureMySQLDatastore(config):
  """Prompts the user for configuration details for a MySQL datastore."""
  db_options = {}

  use_rel_db = RetryBoolQuestion(
      "Do you want to use REL_DB - the new optimized datastore "
      "implementation?\n"
      "(if not, a legacy datastore will be used)", True)
  if use_rel_db:
    db_options["Database.enabled"] = True
    db_options["Database.aff4_enabled"] = False
    db_options["Database.implementation"] = "MysqlDB"
    db_options["Blobstore.implementation"] = "DbBlobStore"

  print("GRR will use MySQL as its database backend. Enter connection details:")
  datastore_init_complete = False
  while not datastore_init_complete:
    db_options["Datastore.implementation"] = "MySQLAdvancedDataStore"
    db_options["Mysql.host"] = RetryQuestion("MySQL Host", "^[\\.A-Za-z0-9-]+$",
                                             config["Mysql.host"])
    db_options["Mysql.port"] = int(
        RetryQuestion("MySQL Port (0 for local socket)", "^[0-9]+$",
                      config["Mysql.port"]))
    db_options["Mysql.database"] = RetryQuestion("MySQL Database",
                                                 "^[A-Za-z0-9-]+$",
                                                 config["Mysql.database_name"])
    db_options["Mysql.database_name"] = db_options["Mysql.database"]
    db_options["Mysql.username"] = RetryQuestion(
        "MySQL Username", "[A-Za-z0-9-@]+$", config["Mysql.database_username"])
    db_options["Mysql.database_username"] = db_options["Mysql.username"]
    # TODO(hanuszczak): Incorrect type specification for `getpass`.
    # pytype: disable=wrong-arg-types
    db_options["Mysql.password"] = getpass.getpass(
        prompt="Please enter password for database user %s: " %
        db_options["Mysql.username"])
    db_options["Mysql.database_password"] = db_options["Mysql.password"]
    # pytype: enable=wrong-arg-types

    use_ssl = RetryBoolQuestion("Configure SSL connections for MySQL?", False)
    if use_ssl:
      db_options["Mysql.client_key_path"] = RetryQuestion(
          "Path to the client private key file",
          default_val=config["Mysql.client_key_path"])
      db_options["Mysql.client_cert_path"] = RetryQuestion(
          "Path to the client certificate file",
          default_val=config["Mysql.client_cert_path"])
      db_options["Mysql.ca_cert_path"] = RetryQuestion(
          "Path to the CA certificate file",
          default_val=config["Mysql.ca_cert_path"])

    if CheckMySQLConnection(db_options):
      print("Successfully connected to MySQL with the provided details.")
      datastore_init_complete = True
    else:
      print("Error: Could not connect to MySQL with the provided details.")
      should_retry = RetryBoolQuestion(
          "Re-enter MySQL details? Answering 'no' will abort config "
          "initialization: ", True)
      if should_retry:
        db_options.clear()
      else:
        raise ConfigInitError()

  for option, value in iteritems(db_options):
    config.Set(option, value)


def ConfigureDatastore(config):
  """Guides the user through configuration of the datastore."""
  print("\n\n-=GRR Datastore=-\n"
        "For GRR to work each GRR server has to be able to communicate with\n"
        "the datastore. To do this we need to configure a datastore.\n")

  use_rel_db = grr_config.CONFIG.Get("Database.enabled")
  existing_datastore = grr_config.CONFIG.Get("Datastore.implementation")

  if not existing_datastore or existing_datastore == "FakeDataStore":
    ConfigureMySQLDatastore(config)
    return

  if use_rel_db:
    print("Found existing settings:\n  REL_DB MySQL database")
  else:
    print("Found existing settings:\n  Datastore: %s" % existing_datastore)
  if existing_datastore == "SqliteDataStore":
    set_up_mysql = RetryBoolQuestion(
        "The SQLite datastore is no longer supported. Would you like to\n"
        "set up a MySQL datastore? Answering 'no' will abort config "
        "initialization.", True)
    if set_up_mysql:
      print("\nPlease note that no data will be migrated from SQLite to "
            "MySQL.\n")
      ConfigureMySQLDatastore(config)
    else:
      raise ConfigInitError()
  elif use_rel_db or existing_datastore == "MySQLAdvancedDataStore":
    print("  MySQL Host: %s\n  MySQL Port: %s\n  MySQL Database: %s\n"
          "  MySQL Username: %s\n" %
          (grr_config.CONFIG.Get("Mysql.host"),
           grr_config.CONFIG.Get("Mysql.port"),
           grr_config.CONFIG.Get("Mysql.database_name"),
           grr_config.CONFIG.Get("Mysql.database_username")))
    if grr_config.CONFIG.Get("Mysql.client_key_path"):
      print("  MySQL client key file: %s\n"
            "  MySQL client cert file: %s\n"
            "  MySQL ca cert file: %s\n" %
            (grr_config.CONFIG.Get("Mysql.client_key_path"),
             grr_config.CONFIG.Get("Mysql.client_cert_path"),
             grr_config.CONFIG.Get("Mysql.ca_cert_path")))

    if not RetryBoolQuestion("Do you want to keep this configuration?", True):
      ConfigureMySQLDatastore(config)


def ConfigureUrls(config, external_hostname = None):
  """Guides the user through configuration of various URLs used by GRR."""
  print("\n\n-=GRR URLs=-\n"
        "For GRR to work each client has to be able to communicate with the\n"
        "server. To do this we normally need a public dns name or IP address\n"
        "to communicate with. In the standard configuration this will be used\n"
        "to host both the client facing server and the admin user interface.\n")

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
          raise RuntimeError("Invalid existing control URL: %s" %
                             existing_control_urn)

        existing_frontend_urns.append(
            existing_control_urn.rsplit("/", 1)[0] + "/")

      config.Set("Client.server_urls", existing_frontend_urns)
      config.Set("Client.control_urls", ["deprecated use Client.server_urls"])

  if not existing_frontend_urns or not existing_ui_urn:
    ConfigureHostnames(config, external_hostname=external_hostname)
  else:
    print("Found existing settings:\n  AdminUI URL: %s\n  "
          "Frontend URL(s): %s\n" % (existing_ui_urn, existing_frontend_urns))
    if not RetryBoolQuestion("Do you want to keep this configuration?", True):
      ConfigureHostnames(config, external_hostname=external_hostname)


def ConfigureEmails(config):
  """Guides the user through email setup."""
  print("\n\n-=GRR Emails=-\n"
        "GRR needs to be able to send emails for various logging and\n"
        "alerting functions. The email domain will be appended to GRR\n"
        "usernames when sending emails to users.\n")

  existing_log_domain = grr_config.CONFIG.Get("Logging.domain", default=None)
  existing_al_email = grr_config.CONFIG.Get(
      "Monitoring.alert_email", default=None)
  existing_em_email = grr_config.CONFIG.Get(
      "Monitoring.emergency_access_email", default=None)
  if existing_log_domain and existing_al_email and existing_em_email:
    print("Found existing settings:\n"
          "  Email Domain: %s\n  Alert Email Address: %s\n"
          "  Emergency Access Email Address: %s\n" %
          (existing_log_domain, existing_al_email, existing_em_email))
    if RetryBoolQuestion("Do you want to keep this configuration?", True):
      return

  print("\n\n-=Monitoring/Email Domain=-\n"
        "Emails concerning alerts or updates must be sent to this domain.\n")
  domain = RetryQuestion("Email Domain e.g example.com",
                         "^([\\.A-Za-z0-9-]+)*$",
                         grr_config.CONFIG.Get("Logging.domain"))
  config.Set("Logging.domain", domain)

  print("\n\n-=Alert Email Address=-\n"
        "Address where monitoring events get sent, e.g. crashed clients, \n"
        "broken server, etc.\n")
  email = RetryQuestion("Alert Email Address", "", "grr-monitoring@%s" % domain)
  config.Set("Monitoring.alert_email", email)

  print("\n\n-=Emergency Email Address=-\n"
        "Address where high priority events such as an emergency ACL bypass "
        "are sent.\n")
  emergency_email = RetryQuestion("Emergency Access Email Address", "",
                                  "grr-emergency@%s" % domain)
  config.Set("Monitoring.emergency_access_email", emergency_email)


def InstallTemplatePackage():
  """Call pip to install the templates."""
  virtualenv_bin = os.path.dirname(sys.executable)
  extension = os.path.splitext(sys.executable)[1]
  pip = "%s/pip%s" % (virtualenv_bin, extension)

  # Install the GRR server component to satisfy the dependency below.
  major_minor_version = ".".join(
      pkg_resources.get_distribution("grr-response-core").version.split(".")
      [0:2])
  # Note that this version spec requires a recent version of pip
  subprocess.check_call([
      sys.executable, pip, "install", "--upgrade", "-f",
      "https://storage.googleapis.com/releases.grr-response.com/index.html",
      "grr-response-templates==%s.*" % major_minor_version
  ])


def FinalizeConfigInit(config,
                       token,
                       admin_password = None,
                       redownload_templates = False,
                       repack_templates = True,
                       prompt = True):
  """Performs the final steps of config initialization."""
  config.Set("Server.initialized", True)
  print("\nWriting configuration to %s." % config["Config.writeback"])
  config.Write()
  print("Initializing the datastore.")
  # Reload the config and initialize the GRR database.
  server_startup.Init()

  print("\nStep 3: Adding GRR Admin User")
  try:
    CreateUser("admin", password=admin_password, is_admin=True)
  except UserAlreadyExistsError:
    if prompt:
      # pytype: disable=wrong-arg-count
      if ((builtins.input("User 'admin' already exists, do you want to "
                          "reset the password? [yN]: ").upper() or "N") == "Y"):
        UpdateUser("admin", password=admin_password, is_admin=True)
      # pytype: enable=wrong-arg-count
    else:
      UpdateUser("admin", password=admin_password, is_admin=True)

  print("\nStep 4: Repackaging clients with new configuration.")
  if prompt:
    redownload_templates = RetryBoolQuestion(
        "Server debs include client templates. Re-download templates?", False)
    repack_templates = RetryBoolQuestion("Repack client templates?", True)
  if redownload_templates:
    InstallTemplatePackage()
  # Build debug binaries, then build release binaries.
  if repack_templates:
    repacking.TemplateRepacker().RepackAllTemplates(upload=True, token=token)
  print("\nGRR Initialization complete! You can edit the new configuration "
        "in %s.\n" % config["Config.writeback"])
  print("Please restart the service for the new configuration to take "
        "effect.\n")


def Initialize(config=None,
               external_hostname = None,
               admin_password = None,
               redownload_templates = False,
               repack_templates = True,
               token = None):
  """Initialize or update a GRR configuration."""

  print("Checking write access on config %s" % config["Config.writeback"])
  if not os.access(config.parser.filename, os.W_OK):
    raise IOError("Config not writeable (need sudo?)")

  print("\nStep 0: Importing Configuration from previous installation.")
  options_imported = 0
  prev_config_file = config.Get("ConfigUpdater.old_config", default=None)
  if prev_config_file and os.access(prev_config_file, os.R_OK):
    print("Found config file %s." % prev_config_file)
    # pytype: disable=wrong-arg-count
    if builtins.input("Do you want to import this configuration? "
                      "[yN]: ").upper() == "Y":
      options_imported = ImportConfig(prev_config_file, config)
    # pytype: enable=wrong-arg-count
  else:
    print("No old config file found.")

  print("\nStep 1: Setting Basic Configuration Parameters")
  print("We are now going to configure the server using a bunch of questions.")
  ConfigureDatastore(config)
  ConfigureUrls(config, external_hostname=external_hostname)
  ConfigureEmails(config)

  print("\nStep 2: Key Generation")
  if config.Get("PrivateKeys.server_key", default=None):
    if options_imported > 0:
      print("Since you have imported keys from another installation in the "
            "last step,\nyou probably do not want to generate new keys now.")
    # pytype: disable=wrong-arg-count
    if (builtins.input("You already have keys in your config, do you want to"
                       " overwrite them? [yN]: ").upper() or "N") == "Y":
      config_updater_keys_util.GenerateKeys(config, overwrite_keys=True)
    # pytype: enable=wrong-arg-count
  else:
    config_updater_keys_util.GenerateKeys(config)

  FinalizeConfigInit(
      config,
      token,
      admin_password=admin_password,
      redownload_templates=redownload_templates,
      repack_templates=repack_templates,
      prompt=True)


def InitializeNoPrompt(config=None,
                       external_hostname = None,
                       admin_password = None,
                       use_rel_db = True,
                       mysql_hostname = None,
                       mysql_port = None,
                       mysql_username = None,
                       mysql_password = None,
                       mysql_db = None,
                       mysql_client_key_path = None,
                       mysql_client_cert_path = None,
                       mysql_ca_cert_path = None,
                       redownload_templates = False,
                       repack_templates = True,
                       token = None):
  """Initialize GRR with no prompts.

  Args:
    config: config object
    external_hostname: A hostname.
    admin_password: A password used for the admin user.
    use_rel_db: If True, initialize REL_DB instead of AFF4.
    mysql_hostname: A hostname used for establishing connection to MySQL.
    mysql_port: A port used for establishing connection to MySQL.
    mysql_username: A username used for establishing connection to MySQL.
    mysql_password: A password used for establishing connection to MySQL.
    mysql_db: Name of the MySQL database to use.
    mysql_client_key_path: The path name of the client private key file.
    mysql_client_cert_path: The path name of the client public key certificate.
    mysql_ca_cert_path: The path name of the CA certificate file.
    redownload_templates: Indicates whether templates should be re-downloaded.
    repack_templates: Indicates whether templates should be re-packed.
    token: auth token

  Raises:
    ValueError: if required flags are not provided, or if the config has
      already been initialized.
    IOError: if config is not writeable
    ConfigInitError: if GRR is unable to connect to a running MySQL instance.

  This method does the minimum work necessary to configure GRR without any user
  prompting, relying heavily on config default values. User must supply the
  external hostname, admin password, and MySQL password; everything else is set
  automatically.
  """
  if config["Server.initialized"]:
    raise ValueError("Config has already been initialized.")
  if not external_hostname:
    raise ValueError(
        "--noprompt set, but --external_hostname was not provided.")
  if not admin_password:
    raise ValueError("--noprompt set, but --admin_password was not provided.")
  if mysql_password is None:
    raise ValueError("--noprompt set, but --mysql_password was not provided.")

  print("Checking write access on config %s" % config.parser)
  if not os.access(config.parser.filename, os.W_OK):
    raise IOError("Config not writeable (need sudo?)")

  config_dict = {}
  if use_rel_db:
    config_dict["Database.enabled"] = True
    config_dict["Database.aff4_enabled"] = False
    config_dict["Database.implementation"] = "MysqlDB"
    config_dict["Blobstore.implementation"] = "DbBlobStore"

  config_dict["Datastore.implementation"] = "MySQLAdvancedDataStore"
  config_dict["Mysql.host"] = mysql_hostname or config["Mysql.host"]
  config_dict["Mysql.port"] = mysql_port or config["Mysql.port"]
  config_dict["Mysql.database_name"] = config_dict[
      "Mysql.database"] = mysql_db or config["Mysql.database_name"]
  config_dict["Mysql.database_username"] = config_dict["Mysql.username"] = (
      mysql_username or config["Mysql.database_username"])
  config_dict["Client.server_urls"] = [
      "http://%s:%s/" % (external_hostname, config["Frontend.bind_port"])
  ]
  config_dict["AdminUI.url"] = "http://%s:%s" % (external_hostname,
                                                 config["AdminUI.port"])
  config_dict["Logging.domain"] = external_hostname
  config_dict["Monitoring.alert_email"] = ("grr-monitoring@%s" %
                                           external_hostname)
  config_dict["Monitoring.emergency_access_email"] = ("grr-emergency@%s" %
                                                      external_hostname)
  # Print all configuration options, except for the MySQL password.
  print("Setting configuration as:\n\n%s" % config_dict)
  config_dict["Mysql.database_password"] = config_dict[
      "Mysql.password"] = mysql_password

  if mysql_client_key_path is not None:
    config_dict["Mysql.client_key_path"] = mysql_client_key_path
    config_dict["Mysql.client_cert_path"] = mysql_client_cert_path
    config_dict["Mysql.ca_cert_path"] = mysql_ca_cert_path

  if CheckMySQLConnection(config_dict):
    print("Successfully connected to MySQL with the given configuration.")
  else:
    print("Error: Could not connect to MySQL with the given configuration.")
    raise ConfigInitError()
  for key, value in iteritems(config_dict):
    config.Set(key, value)
  config_updater_keys_util.GenerateKeys(config)
  FinalizeConfigInit(
      config,
      token,
      admin_password=admin_password,
      redownload_templates=redownload_templates,
      repack_templates=repack_templates,
      prompt=False)


def GetToken():
  # Extend for user authorization
  # SetUID is required to create and write to various aff4 paths when updating
  # config.
  return access_control.ACLToken(username="GRRConsole").SetUID()


def UploadSignedBinary(source_path,
                       binary_type,
                       platform,
                       upload_subdirectory=""):
  """Signs a binary and uploads it to the datastore.

  Args:
    source_path: Path to the binary to upload.
    binary_type: Type of the binary, e.g python-hack or executable.
    platform: Client platform where the binary is intended to be run.
    upload_subdirectory: Path of a subdirectory to upload the binary to,
      relative to the canonical path for binaries of the given type and
      platform.

  Raises:
    BinaryTooLargeError: If the binary to upload is too large.
  """
  file_size = os.path.getsize(source_path)
  if file_size > _MAX_SIGNED_BINARY_BYTES:
    raise BinaryTooLargeError(
        "File [%s] is of size %d (bytes), which exceeds the allowed maximum "
        "of %d bytes." % (source_path, file_size, _MAX_SIGNED_BINARY_BYTES))

  context = ["Platform:%s" % platform.title(), "Client Context"]
  signing_key = grr_config.CONFIG.Get(
      "PrivateKeys.executable_signing_private_key", context=context)

  root_api = maintenance_utils.InitGRRRootAPI()
  binary_path = "/".join([
      platform.lower(),
      upload_subdirectory,
      os.path.basename(source_path),
  ])
  binary = root_api.GrrBinary(binary_type, binary_path)

  with open(source_path, "rb") as fd:
    binary.Upload(
        fd,
        sign_fn=binary.DefaultUploadSigner(
            private_key=signing_key.GetRawPrivateKey()))

  print("Uploaded %s to %s" % (binary_type, binary_path))


def CreateUser(username, password=None, is_admin=False):
  """Creates a new GRR user."""
  grr_api = maintenance_utils.InitGRRRootAPI()
  try:
    user_exists = grr_api.GrrUser(username).Get() is not None
  except api_errors.ResourceNotFoundError:
    user_exists = False
  if user_exists:
    raise UserAlreadyExistsError("User '%s' already exists." % username)
  user_type, password = _GetUserTypeAndPassword(
      username, password=password, is_admin=is_admin)
  grr_api.CreateGrrUser(
      username=username, user_type=user_type, password=password)


def UpdateUser(username, password=None, is_admin=False):
  """Updates the password or privilege-level for a user."""
  user_type, password = _GetUserTypeAndPassword(
      username, password=password, is_admin=is_admin)
  grr_api = maintenance_utils.InitGRRRootAPI()
  grr_user = grr_api.GrrUser(username).Get()
  grr_user.Modify(user_type=user_type, password=password)


def GetUserSummary(username):
  """Returns a string with summary info for a user."""
  grr_api = maintenance_utils.InitGRRRootAPI()
  try:
    return _Summarize(grr_api.GrrUser(username).Get().data)
  except api_errors.ResourceNotFoundError:
    raise UserNotFoundError(username)


def GetAllUserSummaries():
  """Returns a string containing summary info for all GRR users."""
  grr_api = maintenance_utils.InitGRRRootAPI()
  user_wrappers = sorted(grr_api.ListGrrUsers(), key=lambda x: x.username)
  summaries = [_Summarize(w.data) for w in user_wrappers]
  return "\n\n".join(summaries)


def _Summarize(user_info):
  """Returns a string with summary info for a user."""
  return "Username: %s\nIs Admin: %s" % (
      user_info.username,
      user_info.user_type == api_user.ApiGrrUser.UserType.USER_TYPE_ADMIN)


def DeleteUser(username):
  """Deletes a GRR user from the datastore."""
  grr_api = maintenance_utils.InitGRRRootAPI()
  try:
    grr_api.GrrUser(username).Get().Delete()
  except api_errors.ResourceNotFoundError:
    raise UserNotFoundError(username)


def _GetUserTypeAndPassword(username, password=None, is_admin=False):
  """Returns the user-type and password for a user.

  Args:
    username: Username for the user.
    password: Password for the user. If None, or not provided, we will prompt
      for one via the terminal.
    is_admin: Indicates whether the user should have admin privileges.
  """
  if is_admin:
    user_type = api_user.ApiGrrUser.UserType.USER_TYPE_ADMIN
  else:
    user_type = api_user.ApiGrrUser.UserType.USER_TYPE_STANDARD
  if password is None:
    # TODO
    # pytype: disable=wrong-arg-types
    password = getpass.getpass(prompt="Please enter password for user '%s':" %
                               username)
    # pytype: enable=wrong-arg-types
  return user_type, password


def SwitchToRelDB(config):
  """Switches a given config from using AFF4 to using REL_DB."""
  if config["Database.enabled"]:
    print(
        "New generation datastore (REL_DB) is already enabled in the config.\n"
        "Nothing to do.")
    return

  print("***************************************************************\n"
        "Make sure to back up the existing configuration writeback file,\n"
        "you will need it if you decide to switch to the old datastore.\n"
        "Writeback file path:\n%s\n"
        "***************************************************************\n" %
        config["Config.writeback"])
  RetryBoolQuestion("Continue?", True)

  config.Set("Database.enabled", True)
  config.Set("Database.aff4_enabled", False)
  config.Set("Database.implementation", "MysqlDB")

  if (config["Blobstore.implementation"] == "MemoryStreamBlobStore" or
      RetryBoolQuestion(
          "You have a custom 'Blobstore.implementation' setting. Do you want to\n"
          "switch to DbBlobStore (default option for REL_DB, meaning that blobs\n"
          "will be stored inside the MySQL database)?", True)):
    config.Set("Blobstore.implementation", "DbBlobStore")

  if (RetryBoolQuestion(
      "Do you want to use a different MySQL database for the REL_DB datastore?",
      True)):
    db_name = RetryQuestion("MySQL Database", "^[A-Za-z0-9-]+$",
                            config["Mysql.database_name"])
  else:
    db_name = config["Mysql.database_name"]
  config.Set("Mysql.database", db_name)

  if (builtins.input(
      "Do you want to use previously set up MySQL username and password\n"
      "to connect to MySQL database '%s'? [Yn]: " % db_name).upper() or
      "Y") == "Y":
    username = config["Mysql.database_username"]
    password = config["Mysql.database_password"]
  else:
    username = RetryQuestion("MySQL Username", "[A-Za-z0-9-@]+$",
                             config["Mysql.database_username"])
    # TODO(hanuszczak): Incorrect type specification for `getpass`.
    # pytype: disable=wrong-arg-types
    password = getpass.getpass(
        prompt="Please enter password for database user %s: " % username)

  config.Set("Mysql.username", username)
  config.Set("Mysql.password", password)

  print("Configuration updated.")
