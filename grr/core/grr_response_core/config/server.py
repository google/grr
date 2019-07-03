#!/usr/bin/env python
"""Configuration parameters for the server side subsystems."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core import version
from grr_response_core.lib import config_lib
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto

VERSION = version.Version()

config_lib.DEFINE_integer("Source.version_major", VERSION["major"],
                          "Major version number of client binary.")

config_lib.DEFINE_integer("Source.version_minor", VERSION["minor"],
                          "Minor version number of client binary.")

config_lib.DEFINE_integer("Source.version_revision", VERSION["revision"],
                          "Revision number of client binary.")

config_lib.DEFINE_integer("Source.version_release", VERSION["release"],
                          "Release number of client binary.")

config_lib.DEFINE_string(
    "Source.version_string", "%(version_major).%(version_minor)."
    "%(version_revision).%(version_release)", "Version string of the client.")

config_lib.DEFINE_integer(
    "Source.version_numeric", "%(version_major)%(version_minor)"
    "%(version_revision)%(version_release)",
    "Version string of the client as an integer.")

# Note: Each thread adds about 8mb for stack space.
config_lib.DEFINE_integer("Threadpool.size", 50,
                          "Number of threads in the shared thread pool.")

config_lib.DEFINE_integer(
    "Worker.queue_shards", 5, "Queue notifications will be sharded across "
    "this number of datastore subjects.")

config_lib.DEFINE_list(
    "Frontend.well_known_flows", ["TransferStore"],
    "Allow these well known flows to run directly on the "
    "frontend. Other flows are scheduled as normal.")

# Smtp settings.
config_lib.DEFINE_string("Worker.smtp_server", "localhost",
                         "The smtp server for sending email alerts.")

config_lib.DEFINE_integer("Worker.smtp_port", 25, "The smtp server port.")

config_lib.DEFINE_bool("Worker.smtp_starttls", False,
                       "Enable TLS for the smtp connection.")

config_lib.DEFINE_string("Worker.smtp_user", None,
                         "Username for the smtp connection.")

config_lib.DEFINE_string("Worker.smtp_password", None,
                         "Password for the smtp connection.")

# Server Cryptographic settings.
config_lib.DEFINE_semantic_value(
    rdf_crypto.RSAPrivateKey,
    "PrivateKeys.ca_key",
    help="CA private key. Used to sign for client enrollment.")

config_lib.DEFINE_semantic_value(
    rdf_crypto.RSAPrivateKey,
    "PrivateKeys.server_key",
    help="Private key for the front end server.")

config_lib.DEFINE_integer("Server.rsa_key_length", 2048,
                          "The length of the server rsa key in bits.")

config_lib.DEFINE_semantic_value(
    rdf_crypto.RDFX509Cert,
    "Frontend.certificate",
    help="An X509 certificate for the frontend server.")

config_lib.DEFINE_bool("Cron.active", False,
                       "Set to true to run a cron thread on this binary.")

config_lib.DEFINE_list(
    "Cron.disabled_system_jobs", [],
    "Normally, all subclasses of SystemCronFlow are "
    "considered system jobs and run automatically. System "
    "jobs listed here will not be run. Many system jobs are "
    "important. Leave empty unless you are sure that you "
    "know what you are doing.")

config_lib.DEFINE_list(
    "Cron.disabled_cron_jobs", [],
    "This is the equivalent setting to disabled_system_jobs "
    "when using the relational database.")

config_lib.DEFINE_integer(
    "Cron.interrogate_crash_limit", 500,
    "Maximum number of client crashes to allow for an Interrogate cron hunt "
    "before stopping the hunt.")

config_lib.DEFINE_string("Frontend.bind_address", "::",
                         "The ip address to bind.")

config_lib.DEFINE_integer("Frontend.bind_port", 8080, "The port to bind.")

config_lib.DEFINE_integer(
    "Frontend.port_max", None,
    "If set and Frontend.bind_port is in use, attempt to "
    "use ports between Frontend.bind_port and "
    "Frontend.port_max.")

config_lib.DEFINE_integer(
    "Frontend.max_queue_size", 500,
    "Maximum number of messages to queue for the client.")

config_lib.DEFINE_integer(
    "Frontend.max_retransmission_time", 10,
    "Maximum number of times we are allowed to "
    "retransmit a request until it fails.")

config_lib.DEFINE_integer(
    "Frontend.message_expiry_time", 600,
    "Maximum time messages remain valid within the "
    "system.")

config_lib.DEFINE_bool(
    "Server.initialized", False, "True once config_updater initialize has been "
    "run at least once.")

config_lib.DEFINE_string("Server.master_watcher_class", "",
                         "Unused, deprecated.")

config_lib.DEFINE_string("Server.ip_resolver_class", "IPResolver",
                         "The ip resolver class to use.")

config_lib.DEFINE_string("Server.email_alerter_class", "SMTPEmailAlerter",
                         "The email alerter class to use.")

config_lib.DEFINE_string(
    "Server.username", None,
    "System account for services to run as after initialization. Note that "
    "GRR must be running as root first before being able to switch to another "
    "username. You would normally only need this if you want to bind to a low "
    "port for some reason.")

# Email Template Values
config_lib.DEFINE_string("Email.signature", "The GRR Team",
                         "The default signature block for template emails")

config_lib.DEFINE_string(
    "Email.approval_cc_address", None,
    "A single email address or comma separated list of addresses to CC on all "
    "approval emails. Will be added"
    " to all emails and can't be changed or removed by the user.")

config_lib.DEFINE_boolean(
    "Email.send_approval_emails", True,
    "Approval emails are sent for approvals in addition to notifications "
    "in the web UI.")

config_lib.DEFINE_string(
    "Email.approval_optional_cc_address", None,
    "A single email address or comma separated list of addresses to CC on all "
    "approval emails. The user has the option to"
    " remove this CC address .")

config_lib.DEFINE_string(
    "Email.approval_signature", None,
    "If you feel like it, you can add a funny cat picture to approval mails. "
    "Needs full html: <img src=\"https://imgur.com/path/to/cat.jpg\">.")

config_lib.DEFINE_string(
    "StatsStore.process_id", default="", help="Unused, Deprecated.")

config_lib.DEFINE_integer(
    "StatsStore.write_interval", default=60, help="Unused, Deprecated")

config_lib.DEFINE_integer(
    "StatsStore.stats_ttl_hours", default=72, help="Unused, Deprecated.")

config_lib.DEFINE_bool(
    "AdminUI.allow_hunt_results_delete",
    default=False,
    help="If True, hunts with results can be deleted "
    "when the delete hunt button is used. Enable with "
    "caution as this allows erasure of historical usage for"
    "accountability purposes.")

config_lib.DEFINE_integer(
    "Server.max_unbound_read_size",
    10000000,
    help="The number of bytes allowed for unbounded "
    "reads from a file object")

# Data retention policies.
config_lib.DEFINE_semantic_value(
    rdfvalue.Duration,
    "DataRetention.cron_jobs_flows_ttl",
    default=None,
    help="Cron job flows TTL specified as the duration string. "
    "Examples: 90d, 180d, 1y. If not set, cron jobs flows will be retained "
    "forever.")

config_lib.DEFINE_semantic_value(
    rdfvalue.Duration,
    "DataRetention.hunts_ttl",
    default=None,
    help="Hunts TTL specified as the duration string. Examples: 90d, "
    "180d, 1y. If not set, hunts will be retained forever.")

config_lib.DEFINE_string(
    "DataRetention.hunts_ttl_exception_label",
    default="retain",
    help="Hunts marked with this label "
    "will be retained forever.")

config_lib.DEFINE_semantic_value(
    rdfvalue.Duration,
    "DataRetention.tmp_ttl",
    default=None,
    help="Temp TTL specified as the duration string. Examples: 90d, "
    "180d, 1y. If not set, temp objects will be retained forever.")

config_lib.DEFINE_string(
    "DataRetention.tmp_ttl_exception_label",
    default="retain",
    help="Temp objects marked with this "
    "label will be retained forever.")

config_lib.DEFINE_semantic_value(
    rdfvalue.Duration,
    "DataRetention.inactive_client_ttl",
    default=None,
    help="Temp TTL specified as the duration string. Examples: 90d, "
    "180d, 1y. If not set, inactive clients will be retained forever.")

config_lib.DEFINE_string(
    "DataRetention.inactive_client_ttl_exception_label",
    default="retain",
    help="Inactive clients marked with "
    "this label will be retained forever.")

config_lib.DEFINE_integer(
    "Hunt.default_crash_limit",
    default=100,
    help="Default value for HuntRunnerArgs.crash_limit. crash_limit is a "
    "maximum number of clients that are allowed to crash before the hunt is "
    "automatically hard-stopped.")

config_lib.DEFINE_integer(
    "Hunt.default_avg_results_per_client_limit",
    default=1000,
    help="Default value for HuntRunnerArgs.avg_results_per_client_limit. "
    "If the average number of results per client is greater than "
    "avg_results_per_client_limit, the hunt gets stopped.")

config_lib.DEFINE_integer(
    "Hunt.default_avg_cpu_seconds_per_client_limit",
    default=60,
    help="Default value for HuntRunnerArgs.avg_cpu_seconds_per_client_limit. "
    "If the average CPU usage seconds per client becomes "
    "greater than this limit, the hunt gets stopped.")

config_lib.DEFINE_integer(
    "Hunt.default_avg_network_bytes_per_client_limit",
    default=10 * 1024 * 1024,  # 10Mb
    help="Default value for HuntRunnerArgs.avg_network_bytes_per_client_limit. "
    "If the average network usage per client becomes "
    "greater than this limit, the hunt gets stopped.")

# Fleetspeak server-side integration flags.
config_lib.DEFINE_string(
    "Server.fleetspeak_message_listen_address", "",
    "The Fleetspeak server message listen address, formatted like "
    "localhost:6061.")

config_lib.DEFINE_string(
    "Server.fleetspeak_server", "",
    "The Fleetspeak server address, formatted like localhost:6062.")

config_lib.DEFINE_list(
    "Server.fleetspeak_label_map", [],
    "Used to map fleetspeak labels to GRR labels. "
    "A list of entries of the form '<fleetspeak-label>:<grr-primary-label>.")

config_lib.DEFINE_string(
    "Server.fleetspeak_unknown_label", "fleetspeak-unknown",
    "The primary GRR label to use for FS clients which do not match any entry "
    "of fleetspeak_label_map.")

config_lib.DEFINE_semantic_value(
    rdfvalue.Duration,
    "Server.fleetspeak_last_ping_threshold",
    default="2h",
    help="Age above which to consider last-ping timestamps for Fleetspeak "
    "clients as stale, and in need of updating (by querying Fleetspeak "
    "servers).")

config_lib.DEFINE_integer(
    "Server.fleetspeak_list_clients_batch_size",
    default=5000,
    help="Maximum number of client ids to place in a single Fleetspeak "
    "ListClients() API request.")

