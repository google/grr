#!/usr/bin/env python
"""Configuration parameters for the client."""


from grr_response_core.lib import config_lib
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto

# General Client options.
config_lib.DEFINE_string(
    "Client.name", "GRR", "The name of the client. This will be used as a base "
    "name to generate many other default parameters such "
    "as binary names and service names. Note that on "
    "Linux we lowercase the name to confirm with most "
    "linux naming conventions.")

config_lib.DEFINE_string("Client.binary_name", "%(Client.name)",
                         "The name of the client binary.")

config_lib.DEFINE_string("Client.company_name", "GRR Project",
                         "The name of the company which made the client.")

config_lib.DEFINE_string("Client.description", "%(name) %(platform) %(arch)",
                         "A description of this specific client build.")

config_lib.DEFINE_string("Client.platform", "windows",
                         "The platform we are running on.")

config_lib.DEFINE_string("Client.arch", "amd64",
                         "The architecture we are running on.")

config_lib.DEFINE_string("Client.build_time", "Unknown",
                         "The time the client was built.")

config_lib.DEFINE_string("Client.deploy_time", "Unknown",
                         "The time the client was deployed.")

config_lib.DEFINE_string(
    "Client.build_environment", None,
    "The output of Uname.FromCurrentSystem.signature() "
    "on the system the client was built on.")

config_lib.DEFINE_integer("Client.rsa_key_length", 2048,
                          "The key length of the client keys in bits.")

config_lib.DEFINE_string(
    name="Client.install_path",
    default=r"%(SystemRoot|env)\\System32\\%(name)\\%(Template.version_string)",
    help="Where the client binaries are installed.")

config_lib.DEFINE_integer("Client.http_timeout", 100,
                          "Timeout for HTTP requests.")

config_lib.DEFINE_string("Client.plist_path",
                         "/Library/LaunchDaemons/%(Client.plist_filename)",
                         "Location of our launchctl plist.")

config_lib.DEFINE_string("Client.plist_filename", "%(Client.plist_label).plist",
                         "Filename of launchctl plist.")

config_lib.DEFINE_string(
    "Client.plist_label",
    "%(Client.plist_label_prefix).google.code.%(Client.name)",
    "Identifier label for launchd")

config_lib.DEFINE_string("Client.plist_label_prefix", "com",
                         "Domain for launchd label.")

config_lib.DEFINE_list(
    name="Client.proxy_servers",
    help="List of valid proxy servers the client should try.",
    default=[])

config_lib.DEFINE_integer("Client.max_post_size", 40000000,
                          "Maximum size of the post.")

config_lib.DEFINE_integer("Client.max_out_queue", 51200000,
                          "Maximum size of the output queue.")

config_lib.DEFINE_integer(
    "Client.foreman_check_frequency", 1800,
    "The minimum number of seconds before checking with "
    "the foreman for new work.")

config_lib.DEFINE_string(
    name="Client.tempfile_prefix",
    help="Prefix to use for temp files created by the GRR client.",
    default="tmp%(Client.name)")

config_lib.DEFINE_list(
    name="Client.tempdir_roots",
    help="List of temporary directories to use on the client.",
    default=["/var/tmp/"])

config_lib.DEFINE_string(
    name="Client.grr_tempdir",
    help="Default subdirectory in the temp directory to use for GRR.",
    default="%(Client.name)")

config_lib.DEFINE_list(
    name="Client.vfs_virtualroots",
    help=("If this is set for a VFS type, client VFS operations will always be"
          " relative to the given root. Format is os:/mount/disk."),
    default=[])

config_lib.DEFINE_bool(
    name="Client.use_filesystem_sandboxing",
    help="Whether to use the sandboxed implementation for filesystem parsing.",
    default=False)

config_lib.DEFINE_bool(
    name="Client.use_memory_sandboxing",
    help="Whether to use the sandboxed implementation for memory scanning.",
    default=False)

config_lib.DEFINE_string(
    name="Client.unprivileged_user",
    help="Name of (UNIX) user to run sandboxed code as.",
    default="")

config_lib.DEFINE_string(
    name="Client.unprivileged_group",
    help="Name of (UNIX) group to run sandboxed code as.",
    default="")

# Windows client specific options.
config_lib.DEFINE_string(
    "Client.config_hive",
    "HKEY_LOCAL_MACHINE",
    help="The registry hive where the client "
    "configuration will be stored.")

config_lib.DEFINE_string(
    "Client.config_key",
    r"Software\\%(Client.name)",
    help="The registry key where  client configuration "
    "will be stored.")

config_lib.DEFINE_semantic_value(
    rdf_crypto.RSAPublicKey,
    "Client.executable_signing_public_key",
    help="public key for verifying executable signing.")

config_lib.DEFINE_semantic_value(
    rdf_crypto.RSAPrivateKey,
    "PrivateKeys.executable_signing_private_key",
    help="Private keys for signing executables. NOTE: This "
    "key is usually kept offline and is thus not present in the "
    "configuration file.")

config_lib.DEFINE_integer(
    "Client.gc_frequency", 10,
    "Defines how often the client calls garbage collection (seconds).")

config_lib.DEFINE_string(
    "Client.transaction_log_file",
    "%(Logging.path)/transaction.log",
    "The file where we write the agent transaction log.",
)

config_lib.DEFINE_integer(
    "Network.api", 3, "The version of the network protocol the client "
    "uses.")

# Installer options.
config_lib.DEFINE_string(
    name="Installer.logfile",
    default="%(Logging.path)/%(Client.name)_installer.txt",
    help=("A specific log file which is used for logging the "
          "installation process."))

config_lib.DEFINE_string(
    "Client.fleetspeak_unsigned_services_regkey",
    "HKEY_LOCAL_MACHINE\\Software\\FleetspeakClient\\textservices",
    "Registry key (on Windows) where Fleetspeak expects services "
    "to write their unsigned configs to.")

config_lib.DEFINE_string(
    "Client.fleetspeak_unsigned_config_fname",
    "%(Client.name)_fleetspeak_service_config.txt",
    "File-name for the Fleetspeak service config generated "
    "when repacking templates.")

config_lib.DEFINE_list(
    "Client.allowed_commands",
    default=[],
    help="Commands that the client is allowed to execute. Each command must be "
    "specified in the format that is supported by the Python's `shlex` module.")

config_lib.DEFINE_string(
    "Client.interrogate_trigger_path",
    default="",
    help="When set, the client will check for the presence of this file at "
    "every startup and, if the file is present, will remove it and trigger "
    "an interrogate on the server.")

# osquery options.

config_lib.DEFINE_string(
    "Osquery.path", default="", help="A path to the osquery executable.")

config_lib.DEFINE_integer(
    "Osquery.max_chunk_size",
    default=1024 * 1024,  # 1 MiB.
    help=("A size (in bytes) of maximum response size. Queries for which the "
          "output exceedes the specified limit are going to be divided into "
          "multiple responses."))
