#!/usr/bin/env python
"""Configuration parameters for the server side subsystems."""

from grr.lib import config_lib
from grr.lib import rdfvalue
from grr.lib.rdfvalues import crypto as rdf_crypto

# Note: Each thread adds about 8mb for stack space.
config_lib.DEFINE_integer("Threadpool.size", 50,
                          "Number of threads in the shared thread pool.")

config_lib.DEFINE_integer("Worker.flow_lease_time", 7200,
                          "Duration of a flow lease time in seconds.")

config_lib.DEFINE_integer("Worker.well_known_flow_lease_time", 600,
                          "Duration of a well known flow lease time in "
                          "seconds.")

config_lib.DEFINE_integer("Worker.compaction_lease_time", 3600,
                          "Duration of collections lease time for compaction "
                          "in seconds.")

config_lib.DEFINE_bool("Worker.enable_packed_versioned_collection_journaling",
                       False, "If True, all Add*() operations and all "
                       "compactions of PackedVersionedCollections will be "
                       "journaled so that these collections can be later "
                       "checked for integrity.")

config_lib.DEFINE_integer("Worker.queue_shards", 5,
                          "Queue notifications will be sharded across "
                          "this number of datastore subjects.")

config_lib.DEFINE_integer("Worker.notification_expiry_time", 600,
                          "The queue manager expires stale notifications "
                          "after this many seconds.")

config_lib.DEFINE_integer("Worker.notification_retry_interval", 30,
                          "The queue manager retries to work on requests it "
                          "could not complete after this many seconds.")

# We write a journal entry for the flow when it's about to be processed.
# If the journal entry is there after this time, the flow will get terminated.
config_lib.DEFINE_integer(
    "Worker.stuck_flows_timeout", 60 * 60 * 6,
    "Flows who got stuck in the worker for more than this time (in seconds) "
    "are forcibly terminated")

config_lib.DEFINE_integer("Frontend.throttle_average_interval", 60,
                          "Time interval over which average request rate is "
                          "calculated when throttling is enabled.")

config_lib.DEFINE_list("Frontend.well_known_flows",
                       ["TransferStore", "Stats"],
                       "Allow these well known flows to run directly on the "
                       "frontend. Other flows are scheduled as normal.")

config_lib.DEFINE_string(
    "Frontend.static_aff4_prefix", "aff4:/web/static/",
    "The AFF4 URN prefix for all streams served publicly from the frontend.")

config_lib.DEFINE_string(
    "Frontend.static_url_path_prefix", "/static/",
    "The URL prefix for all streams served publicly from the frontend.")

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
config_lib.DEFINE_semantic(
    rdf_crypto.PEMPrivateKey, "PrivateKeys.ca_key",
    description="CA private key. Used to sign for client enrollment.",
)

config_lib.DEFINE_semantic(
    rdf_crypto.PEMPrivateKey, "PrivateKeys.server_key",
    description="Private key for the front end server.")

config_lib.DEFINE_integer("Server.rsa_key_length", 2048,
                          "The length of the server rsa key in bits.")

config_lib.DEFINE_semantic(
    rdf_crypto.RDFX509Cert, "Frontend.certificate",
    description="An X509 certificate for the frontend server.")

config_lib.DEFINE_bool("Cron.active", False,
                       "Set to true to run a cron thread on this binary.")

config_lib.DEFINE_list("Cron.enabled_system_jobs", [],
                       "DEPRECATED: Use Cron.disabled_system_jobs instead. "
                       "If Cron.enabled_system_jobs is set, only the listed "
                       "cron flows will be run as system cron jobs. Cannot "
                       "be used together with Cron.disabled_system_jobs.")

config_lib.DEFINE_list("Cron.disabled_system_jobs", [],
                       "Normally, all subclasses of SystemCronFlow are "
                       "considered system jobs and run automatically. System "
                       "jobs listed here will not be run. Many system jobs are "
                       "important. Leave empty unless you are sure that you "
                       "know what you are doing.")

config_lib.DEFINE_string("Frontend.bind_address", "::",
                         "The ip address to bind.")

config_lib.DEFINE_integer("Frontend.bind_port", 8080, "The port to bind.")

config_lib.DEFINE_integer("Frontend.max_queue_size", 500,
                          "Maximum number of messages to queue for the client.")

config_lib.DEFINE_integer("Frontend.max_retransmission_time", 10,
                          "Maximum number of times we are allowed to "
                          "retransmit a request until it fails.")

config_lib.DEFINE_integer("Frontend.message_expiry_time", 600,
                          "Maximum time messages remain valid within the "
                          "system.")

# The Admin UI web application.
config_lib.DEFINE_integer("AdminUI.port", 8000, "port to listen on")

config_lib.DEFINE_string("AdminUI.bind", "::", "interface to bind to.")

config_lib.DEFINE_string(
    "AdminUI.webauth_manager", "NullWebAuthManager",
    "The web auth manager for controlling access to the UI.")

config_lib.DEFINE_bool("AdminUI.django_debug", True,
                       "Turn on to add django debugging")

config_lib.DEFINE_string(
    "AdminUI.django_secret_key", "CHANGE_ME",
    "This is a secret key that should be set in the server "
    "config. It is used in XSRF and session protection.")

config_lib.DEFINE_list(
    "AdminUI.django_allowed_hosts", ["*"],
    "Set the django ALLOWED_HOSTS parameter. "
    "See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts")

config_lib.DEFINE_bool("AdminUI.enable_ssl", False,
                       "Turn on SSL. This needs AdminUI.ssl_cert to be set.")

config_lib.DEFINE_string("AdminUI.ssl_cert_file", "",
                         "The SSL certificate to use.")

config_lib.DEFINE_string(
    "AdminUI.ssl_key_file", None,
    "The SSL key to use. The key may also be part of the cert file, in which "
    "case this can be omitted.")

config_lib.DEFINE_string("AdminUI.url", "http://localhost:8000/",
                         "The direct external URL for the user interface.")

config_lib.DEFINE_bool("AdminUI.use_precompiled_js", False,
                       "If True - use Closure-compiled JS bundle. This flag "
                       "is experimental and is not properly supported yet.")

config_lib.DEFINE_string("AdminUI.export_command",
                         "/usr/bin/grr_export",
                         "Command to show in the fileview for downloading the "
                         "files from the command line.")

config_lib.DEFINE_string("AdminUI.page_title",
                         "GRR Admin Console",
                         "Page title of the Admin UI.")

config_lib.DEFINE_string("AdminUI.heading", "",
                         "Dashboard heading displayed in the Admin UI.")

config_lib.DEFINE_string("AdminUI.report_url",
                         "https://github.com/google/grr/issues",
                         "URL of the 'Report a problem' link.")

config_lib.DEFINE_string("AdminUI.help_url",
                         "/help/index.html",
                         "URL of the 'Help' link.")

config_lib.DEFINE_string("AdminUI.github_docs_location",
                         "https://github.com/google/grr-doc/blob/master",
                         "Base path for GitHub-hosted GRR documentation. ")

config_lib.DEFINE_string("AdminUI.new_hunt_wizard.default_output_plugin",
                         None,
                         "Output plugin that will be added by default in the "
                         "'New Hunt' wizard output plugins selection page.")

config_lib.DEFINE_bool("AdminUI.new_hunt_wizard.use_object_oriented_hunt_rules",
                       default=True,
                       help="If True, the hunt rules configuration UI will put "
                       "the rules into the 'client_rule_set' field of the "
                       "'huntRunnerArgs' variable, instead of using "
                       "'integerRules' and 'regexRules'.")

config_lib.DEFINE_bool("AdminUI.new_hunt_wizard."
                       "use_oo_hunt_rules_in_new_cron_job_wizard",
                       default=True,
                       help="This is the same as "
                       "AdminUI.new_hunt_wizard.use_object_oriented_hunt_rules,"
                       " but regarding the new cron job wizard.")

config_lib.DEFINE_string("Server.master_watcher_class", "DefaultMasterWatcher",
                         "The master watcher class to use.")

config_lib.DEFINE_string("Server.ip_resolver_class", "IPResolver",
                         "The ip resolver class to use.")

config_lib.DEFINE_string("Server.email_alerter_class", "SMTPEmailAlerter",
                         "The email alerter class to use.")

config_lib.DEFINE_string(
    "Rekall.profile_repository",
    "https://github.com/google/rekall-profiles/raw/master",
    "The repository to use when downloading Rekall profiles.")

config_lib.DEFINE_string(
    "Rekall.profile_cache_urn", "aff4:/rekall_profiles",
    "A cache in the aff4 space to store downloaded Rekall profiles.")

config_lib.DEFINE_string(
    "Rekall.profile_server", "GRRRekallProfileServer",
    "Which Rekall profile server to use.")

config_lib.DEFINE_string(
    "StatsHunt.CollectionInterval", "10m",
    "How often to collect the StatsHunt information from each client. The "
    "minimum bound here is effectively 2 * Client.poll_max, since a new request"
    " is only scheduled after results are received in the previous poll.")

config_lib.DEFINE_string(
    "Server.username", "root",
    "System account for services to run as after initialization.")

# Email Template Values
config_lib.DEFINE_string(
    "Email.signature", "The GRR Team",
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

config_lib.DEFINE_list(
    "Email.link_regex_list", [],
    "Strings matching these regexes in approval reasons will be turned into "
    " HTML links in approval emails. Note you have to use single quoted strings"
    " when setting this variable to prevent escaping.")

config_lib.DEFINE_integer(
    "StatsHunt.ClientBatchSize", "200",
    "Batch size for client scheduling. This should be large enough that it "
    "alleviates the performance impact of database roundtrips to open the "
    "clients, but small enough that the threshold will be continuously reached "
    "to keep the hunt running.")

config_lib.DEFINE_integer(
    "StatsHunt.ClientLimit", "0",
    "The number of clients to run the StatsHunt on. This is purely to "
    "allow for testing when the cronjob is enabled, since it can be a "
    "significant amount of traffic. This should be set to 0 once you know"
    " that the server can handle it.")

config_lib.DEFINE_string("StatsStore.process_id", default="",
                         help="Id used to identify stats data of the current "
                         "process. This should be different for different GRR "
                         "processes. I.e. if you have 4 workers, for every "
                         "worker the subject should be different. For example: "
                         "worker_1, worker_2, worker_3, worker_4.")

config_lib.DEFINE_integer("StatsStore.write_interval", default=60,
                          help="Time in seconds between the dumps of stats "
                          "data into the stats store.")

config_lib.DEFINE_integer("StatsStore.ttl", default=60 * 60 * 24 * 3,
                          help="Maximum lifetime (in seconds) of data in the "
                          "stats store. Default is three days.")

config_lib.DEFINE_list("ConfigIncludes", [],
                       "List of additional config files to include. Files are "
                       "processed recursively depth-first, later values "
                       "override earlier ones.")

config_lib.DEFINE_bool("AdminUI.allow_hunt_results_delete", default=False,
                       help="If True, hunts with results can be deleted "
                       "when the delete hunt button is used. Enable with "
                       "caution as this allows erasure of historical usage for"
                       "accountability purposes.")

config_lib.DEFINE_integer("Server.max_unbound_read_size", 10000000,
                          help="The number of bytes allowed for unbounded "
                          "reads from a file object")

# Data retention policies.
config_lib.DEFINE_semantic(
    rdfvalue.Duration, "DataRetention.cron_jobs_flows_ttl", default=None,
    description="Cron job flows TTL specified as the duration string. "
    "Examples: 90d, 180d, 1y. If not set, cron jobs flows will be retained "
    "forever.")

config_lib.DEFINE_semantic(
    rdfvalue.Duration, "DataRetention.hunts_ttl", default=None,
    description="Hunts TTL specified as the duration string. Examples: 90d, "
    "180d, 1y. If not set, hunts will be retained forever.")

config_lib.DEFINE_string("DataRetention.hunts_ttl_exception_label",
                         default="retain", help="Hunts marked with this label "
                         "will be retained forever.")

config_lib.DEFINE_semantic(
    rdfvalue.Duration, "DataRetention.tmp_ttl", default=None,
    description="Temp TTL specified as the duration string. Examples: 90d, "
    "180d, 1y. If not set, temp objects will be retained forever.")

config_lib.DEFINE_string("DataRetention.tmp_ttl_exception_label",
                         default="retain", help="Temp objects marked with this "
                         "label will be retained forever.")

config_lib.DEFINE_semantic(
    rdfvalue.Duration, "DataRetention.inactive_client_ttl", default=None,
    description="Temp TTL specified as the duration string. Examples: 90d, "
    "180d, 1y. If not set, inactive clients will be retained forever.")

config_lib.DEFINE_string("DataRetention.inactive_client_ttl_exception_label",
                         default="retain", help="Inactive clients marked with "
                         "this label will be retained forever.")
