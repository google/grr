#!/usr/bin/env python
"""Configuration parameters for the client."""

from grr.lib import config_lib
from grr.lib import rdfvalue


# General Client options.
config_lib.DEFINE_string("Client.name", "GRR",
                         "The name of the client. This will be used as a base "
                         "name to generate many other default parameters such "
                         "as binary names and service names. Note that on "
                         "Linux we lowercase the name to confirm with most "
                         "linux naming conventions.")

config_lib.DEFINE_string("Client.binary_name", "%(Client.name)",
                         "The name of the client binary.")

config_lib.DEFINE_list("Client.labels", [],
                       "Labels for this client.")

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

config_lib.DEFINE_string(
    name="Client.install_path",
    default=r"%(SystemRoot|env)\\System32\\%(name)\\%(version_string)",
    help="Where the client binaries are installed.")

config_lib.DEFINE_string(
    name="Client.rekall_profile_cache_path",
    default=r"%(Client.install_path)\\rekall_profiles",
    help="Where GRR stores cached Rekall profiles needed for memory analysis")

config_lib.DEFINE_list("Client.control_urls",
                       ["http://www.example.com/control"],
                       "List of URLs of the controlling server.")

config_lib.DEFINE_string("Client.plist_path",
                         "/Library/LaunchDaemons/com.google.code.grrd.plist",
                         "Location of our launchctl plist.")

config_lib.DEFINE_float("Client.poll_min", 0.2,
                        "Minimum time between polls in seconds.")

config_lib.DEFINE_float("Client.poll_max", 600,
                        "Maximum time between polls in seconds.")

config_lib.DEFINE_float("Client.error_poll_min", 15,
                        "Minimum time between polls in seconds if the server "
                        "reported an error.")

config_lib.DEFINE_float("Client.poll_slew", 1.15,
                        "Slew of poll time.")

config_lib.DEFINE_integer("Client.connection_error_limit", 60 * 24,
                          "If the client encounters this many connection "
                          "errors, it exits and restarts. Retries are one "
                          "minute apart.")

config_lib.DEFINE_list(
    name="Client.proxy_servers",
    help="List of valid proxy servers the client should try.",
    default=[])

config_lib.DEFINE_integer("Client.max_post_size", 8000000,
                          "Maximum size of the post.")

config_lib.DEFINE_integer("Client.max_out_queue", 10240000,
                          "Maximum size of the output queue.")

config_lib.DEFINE_integer("Client.foreman_check_frequency", 1800,
                          "The minimum number of seconds before checking with "
                          "the foreman for new work.")

config_lib.DEFINE_float("Client.rss_max", 500,
                        "Maximum memory footprint in MB.")

config_lib.DEFINE_string(
    name="Client.tempfile_prefix",
    help="Prefix to use for temp files created by the GRR client.",
    default="tmp%(Client.name)")

config_lib.DEFINE_string(
    name="Client.tempdir",
    help="Default temporary directory to use on the client.",
    default="/var/tmp/%(Client.name)/")

config_lib.DEFINE_integer("Client.version_major", 0,
                          "Major version number of client binary.")

config_lib.DEFINE_integer("Client.version_minor", 0,
                          "Minor version number of client binary.")

config_lib.DEFINE_integer("Client.version_revision", 0,
                          "Revision number of client binary.")

config_lib.DEFINE_integer("Client.version_release", 0,
                          "Release number of client binary.")

config_lib.DEFINE_string("Client.version_string",
                         "%(version_major).%(version_minor)."
                         "%(version_revision).%(version_release)",
                         "Version string of the client.")

config_lib.DEFINE_integer("Client.version_numeric",
                          "%(version_major)%(version_minor)"
                          "%(version_revision)%(version_release)",
                          "Version string of the client as an integer.")

config_lib.DEFINE_list("Client.plugins", [],
                       help="Additional Plugin paths loaded by the client.")

# Windows client specific options.
config_lib.DEFINE_string("Client.config_hive", r"HKEY_LOCAL_MACHINE",
                         help="The registry hive where the client "
                         "configuration will be stored.")

config_lib.DEFINE_string("Client.config_key", r"Software\\GRR",
                         help="The registry key where  client configuration "
                         "will be stored.")

# Client Cryptographic options.
config_lib.DEFINE_semantic(
    rdfvalue.PEMPrivateKey, "Client.private_key",
    description="Client private key in pem format. If not provided this "
    "will be generated by the enrollment process.",
    )

config_lib.DEFINE_semantic(
    rdfvalue.RDFX509Cert, "CA.certificate",
    description="Trusted CA certificate in X509 pem format",
    )

config_lib.DEFINE_semantic(
    rdfvalue.PEMPublicKey, "Client.executable_signing_public_key",
    description="public key for verifying executable signing.")

config_lib.DEFINE_semantic(
    rdfvalue.PEMPrivateKey, "PrivateKeys.executable_signing_private_key",
    description="Private keys for signing executables. NOTE: This "
    "key is usually kept offline and is thus not present in the "
    "configuration file.")

config_lib.DEFINE_semantic(
    rdfvalue.PEMPublicKey, "Client.driver_signing_public_key",
    description="public key for verifying driver signing.")

config_lib.DEFINE_semantic(
    rdfvalue.PEMPrivateKey, "PrivateKeys.driver_signing_private_key",
    description="Private keys for signing drivers. NOTE: This "
    "key is usually kept offline and is thus not present in the "
    "configuration file.")

config_lib.DEFINE_integer("Client.server_serial_number", 0,
                          "Minimal serial number we accept for server cert.")


# The following configuration options are defined here but are used in
# the windows nanny code (grr/client/nanny/windows_nanny.h).
config_lib.DEFINE_string("Nanny.child_binary", "GRR.exe",
                         help="The location to the client binary.")

config_lib.DEFINE_string("Nanny.child_command_line", "%(Nanny.child_binary)",
                         help="The command line to launch the client binary.")

config_lib.DEFINE_string("Nanny.logfile", "%(Logging.path)/nanny.log",
                         "The file where we write the nanny transaction log.")

config_lib.DEFINE_string("Nanny.service_name", "GRR Service",
                         help="The name of the nanny.")

config_lib.DEFINE_string("Nanny.service_description", "GRR Service",
                         help="The description of the nanny service.")

config_lib.DEFINE_string("Nanny.service_key", r"%(Client.config_key)",
                         help="The registry key of the nanny service.")

config_lib.DEFINE_string("Nanny.service_key_hive", r"%(Client.config_hive)",
                         help="The registry key of the nanny service.")

config_lib.DEFINE_string("Nanny.statusfile", "%(Logging.path)/nanny.status",
                         "The file where we write the nanny status.")

config_lib.DEFINE_string("Nanny.binary",
                         r"%(Client.install_path)\\%(service_binary_name)",
                         help="The full location to the nanny binary.")

config_lib.DEFINE_string("Nanny.service_binary_name",
                         "%(Client.name)service.exe",
                         help="The executable name of the nanny binary.")

config_lib.DEFINE_integer("Nanny.unresponsive_kill_period", 60,
                          "The time in seconds after which the nanny kills us.")

config_lib.DEFINE_integer("Network.api", 3,
                          "The version of the network protocol the client "
                          "uses.")

config_lib.DEFINE_string("Network.compression", default="ZCOMPRESS",
                         help="Type of compression (ZCOMPRESS, UNCOMPRESSED)")


# Installer options.
config_lib.DEFINE_string(
    name="Installer.logfile",
    default="%(Logging.path)/%(Client.name)_installer.txt",
    help=("A specific log file which is used for logging the "
          "installation process."))

config_lib.DEFINE_list(
    "Installer.old_key_map", [
        "HKEY_LOCAL_MACHINE\\Software\\GRR\\certificate->Client.private_key",
        "HKEY_LOCAL_MACHINE\\Software\\GRR\\server_serial_number"
        "->Client.server_serial_number",
        ],
    """
A mapping of old registry values which will be copied to new values. The old
value location must start with a valid hive name, followed by a key name, and
end with the value name. The source location must be separated from the new
parameter name by a -> symbol.

This setting allows to carry over settings from obsolete client installations to
newer versions of the client which may store the same information in other
locations.

For example:

  HKEY_LOCAL_MACHINE\\Software\\GRR\\certificate -> Client.private_key
""")
