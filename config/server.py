#!/usr/bin/env python
"""Configuration parameters for the server side subsystems."""

from grr.lib import config_lib
from grr.lib import rdfvalue


# Note: Each thread adds about 8mb for stack space.
config_lib.DEFINE_integer("Threadpool.size", 50,
                          "Number of threads in the shared thread pool.")

config_lib.DEFINE_integer("Worker.task_limit", 2000,
                          "Limits the number of tasks a worker retrieves "
                          "every poll")

config_lib.DEFINE_integer("Worker.flow_lease_time", 600,
                          "Duration of flow lease time in seconds.")

config_lib.DEFINE_integer("Worker.worker_process_count", 1,
                          "Number of worker processes to run. Each worker can "
                          "only use a single CPU, so scaling this up on "
                          "multiprocessor systems may make sense.")

config_lib.DEFINE_integer("Worker.queue_shards", 1,
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
                       ["aff4:/flows/W:TransferStore", "aff4:/flows/W:Stats"],
                       "Allow these well known flows to run directly on the "
                       "frontend. Other flows are scheduled as normal.")

# Smtp settings.
config_lib.DEFINE_string("Worker.smtp_server", "localhost",
                         "The smpt server for sending email alerts.")

config_lib.DEFINE_integer("Worker.smtp_port", 25, "The smtp server port.")

# Server Cryptographic settings.
config_lib.DEFINE_semantic(
    rdfvalue.PEMPrivateKey, "PrivateKeys.ca_key",
    description="CA private key. Used to sign for client enrollment.",
    )

config_lib.DEFINE_semantic(
    rdfvalue.PEMPrivateKey, "PrivateKeys.server_key",
    description="Private key for the front end server.")

config_lib.DEFINE_semantic(
    rdfvalue.RDFX509Cert, "Frontend.certificate",
    description="An X509 certificate for the frontend server.")

config_lib.DEFINE_integer("ACL.cache_age", 600, "The number of seconds "
                          "approval objects live in the cache.")

config_lib.DEFINE_integer("Datastore.maximum_blob_size",
                          15*1024*1024,
                          "Maximum blob size we may store in the datastore.")

config_lib.DEFINE_string("Datastore.security_manager",
                         "NullAccessControlManager",
                         "The ACL manager for controlling access to data.")

config_lib.DEFINE_string("Datastore.implementation", "FakeDataStore",
                         "Storage subsystem to use.")

config_lib.DEFINE_integer("Datastore.transaction_timeout", default=600,
                          help="How long do we wait for a transaction lock.")

# TDB data store.
config_lib.DEFINE_string("TDBDatastore.root_path", default="/tmp/grr-tdb",
                         help=("The root directory under which the tdb files "
                               "are created."))

# SQLite data store.
config_lib.DEFINE_string("SqliteDatastore.root_path", default="/tmp/grr-sqlite",
                         help=("The root directory under which the sqlite "
                               "files are created."))

# Mongo data store.
config_lib.DEFINE_string("Mongo.server", "localhost",
                         "The mongo server hostname.")

config_lib.DEFINE_integer("Mongo.port", 27017, "The mongo server port..")

config_lib.DEFINE_string("Mongo.db_name", "grr", "The mongo database name")

# MySQL data store.
config_lib.DEFINE_string("Mysql.host", "localhost",
                         "The MySQL server hostname.")

config_lib.DEFINE_integer("Mysql.port", 0, "The MySQL server port.")

config_lib.DEFINE_string("Mysql.database_name", default="grr",
                         help="Name of the database to use.")

config_lib.DEFINE_string("Mysql.table_name", default="aff4",
                         help="Name of the table to use.")

config_lib.DEFINE_string("Mysql.database_username", default="root",
                         help="The user to connect to the database.")

config_lib.DEFINE_string("Mysql.database_password", default="",
                         help="The password to connect to the database.")


config_lib.DEFINE_bool("Cron.active", False,
                       "Set to true to run a cron thread on this binary.")


config_lib.DEFINE_integer("ACL.approvers_required", 2,
                          "The number of approvers required for access.")

config_lib.DEFINE_string("AdminUI.url", "http://localhost:8000/",
                         "The direct external URL for the user interface.")

config_lib.DEFINE_string("Frontend.bind_address", "::",
                         "The ip address to bind.")

config_lib.DEFINE_integer("Frontend.bind_port", 8080, "The port to bind.")

config_lib.DEFINE_integer("Frontend.processes", 1,
                          "Number of processes to use for the HTTP server")

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

config_lib.DEFINE_string("AdminUI.export_command",
                         "/usr/bin/grr_export",
                         "Command to show in the fileview for downloading the "
                         "files from the command line.")

config_lib.DEFINE_string("Server.master_watcher_class", "DefaultMasterWatcher",
                         "The master watcher class to use.")

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
