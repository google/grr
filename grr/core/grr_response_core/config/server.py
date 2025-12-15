#!/usr/bin/env python
"""Configuration parameters for the server side subsystems."""


from grr_response_core import version
from grr_response_core.lib import config_lib
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import paths as rdf_paths

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

config_lib.DEFINE_list("Frontend.well_known_flows", [], "Unused, Deprecated.")

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

config_lib.DEFINE_integer("Server.rsa_key_length", 2048,
                          "The length of the server rsa key in bits.")

config_lib.DEFINE_bool("Cron.active", False,
                       "Set to true to run a cron thread on this binary.")

config_lib.DEFINE_list(
    "Cron.disabled_cron_jobs",
    [],
    "Cron jobs listed here will not be run. Many system jobs are "
    "important. Leave empty unless you are sure that you "
    "know what you are doing.",
)

config_lib.DEFINE_integer(
    "Cron.interrogate_crash_limit", 500,
    "Maximum number of client crashes to allow for an Interrogate cron hunt "
    "before stopping the hunt.")

config_lib.DEFINE_integer(
    "Cron.interrogate_client_rate", 50,
    "Client rate setting for the periodical Interrogate cron hunt.")

config_lib.DEFINE_semantic_value(
    rdfvalue.Duration, "Cron.interrogate_duration",
    rdfvalue.Duration.From(1, rdfvalue.WEEKS),
    "Duration of the Interrogate cron hunt. The hunt is run weekly, so "
    "default duration is 1w. In certain cases the duration might be extended "
    "to accommodate for the clients that rarely show up online.")

config_lib.DEFINE_string("Frontend.bind_address", "::",
                         "The ip address to bind.")

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

config_lib.DEFINE_bool(
    "Email.enable_custom_email_address", False,
    "If true, it's possible to set a custom E-Mail address for GRR users, "
    "overriding the default <username>@<Logging.domain>.")

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
    help="The number of bytes allowed for unbounded reads from a file object")

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

config_lib.DEFINE_float(
    "Hunt.default_client_rate",
    default=20.0,
    help="Default value for HuntRunnerArgs.client_rate. Client rate "
    "determines how many clients per minute get to process a hunt")

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

# GRRafana HTTP Server settings.
config_lib.DEFINE_string(
    "GRRafana.bind", default="localhost", help="The GRRafana server address.")

config_lib.DEFINE_integer(
    "GRRafana.port", default=5000, help="The GRRafana server port.")

# Fleetspeak server-side integration flags.
config_lib.DEFINE_string(
    "Server.fleetspeak_message_listen_address", "",
    "The Fleetspeak server message listen address, formatted like "
    "localhost:6061.")

config_lib.DEFINE_string(
    "Server.fleetspeak_server", "",
    "The Fleetspeak server address, formatted like localhost:6062.")

config_lib.DEFINE_string(
    "Server.fleetspeak_label_prefix", None,
    "Prefix used to identify Fleetspeak labels that should be written to "
    "GRR's DB during Interrogation. If not given, all labels are written.")

config_lib.DEFINE_list(
    "Server.fleetspeak_label_map", [],
    "Used to override fleetspeak labels with custom labels. Entries in the "
    "list are expected to be of the form '<fleetspeak-label>:<override>'. If "
    "a Fleetspeak label is not in the map, it will be written as is to GRR's "
    "DB as part of the Interrogate flow.")

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

config_lib.DEFINE_bool(
    "Server.fleetspeak_cps_enabled",
    default=False,
    help=(
        "Enable the Google Cloud Pub/Sub communication channel from Fleetspeak."
        " When this is set to True, incoming messages from Fleetspeak are"
        " fetched from a Cloud Pub/Sub subscription instead of being received"
        " directly via GRPC."
    ),
)

config_lib.DEFINE_string(
    "Server.fleetspeak_cps_project",
    default=None,
    help=(
        "Google Cloud project name to use when communicating with Fleetspeak "
        "via Cloud Pub/Sub."
    ),
)

config_lib.DEFINE_string(
    "Server.fleetspeak_cps_subscription",
    default=None,
    help=(
        "Cloud Pub/Sub subscription name to use for reading Fleetspeak "
        "messages. This subscription must have been already created."
    ),
)

config_lib.DEFINE_integer(
    "Server.fleetspeak_cps_concurrency",
    default=20,
    help=(
        "The number of concurrent message-processing subscribers to spawn "
        "when receiving Fleetspeak messages via Cloud Pub/Sub."
    ),
)

config_lib.DEFINE_semantic_enum(
    rdf_paths.PathSpec.PathType,
    "Server.raw_filesystem_access_pathtype",
    default=rdf_paths.PathSpec.PathType.NTFS,
    help="PathType to use for raw filesystem access on Windows.")

config_lib.DEFINE_boolean(
    "Server.grr_binaries_readonly", False,
    "When set to True, uploaded GRR binaries can't be deleted or overwritten.")

config_lib.DEFINE_boolean(
    name="Interrogate.collect_crowdstrike_agent_id",
    default=False,
    help=(
        "Whether the interrogate flow should collect identifier of the "
        "endpoint's CrowdStrike agent."
    ),
)

config_lib.DEFINE_boolean(
    name="Interrogate.collect_passwd_cache_users",
    default=False,
    help=(
        "Whether the interrogate flow should collect user information using the"
        "`/etc/passwd.cache` file."
    ),
)

config_lib.DEFINE_string(
    "Server.signed_url_service_account_email",
    default=None,
    help=(
        "The email of the Service Account to use for signing the URL"
        " (https://cloud.google.com/storage/docs/access-control/signed-urls#signing-resumable)."
    ),
)

config_lib.DEFINE_string(
    "Server.signed_url_gcs_bucket_name",
    default=None,
    help=(
        "The GCS bucket name to include in the signed URL"
        " (https://cloud.google.com/storage/docs/access-control/signed-urls#signing-resumable)."
    ),
)

config_lib.DEFINE_integer(
    "Server.signed_url_expire_hours",
    default=12,
    help=(
        "The TTL until the signed URL expires"
        " (https://cloud.google.com/storage/docs/access-control/signed-urls#signing-resumable)."
    ),
)

config_lib.DEFINE_string(
    "Server.disable_rrg_support",
    default=False,
    help=(
        "Disables support for RRG agents (forces the traffic to always be "
        "routed to the Python agent)."
    ),
)

config_lib.DEFINE_string(
    name="CommandSigning.ed25519_private_key_file",
    default=None,
    help="An UTF-8 encoded Ed25519 encryption key to sign commands.",
)
