#!/usr/bin/env python
"""Configuration parameters for the data stores."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import config_lib
from grr_response_core.lib import rdfvalue

config_lib.DEFINE_integer("Datastore.maximum_blob_size", 512 * 1024,
                          "Maximum blob size we may store in the datastore.")

config_lib.DEFINE_string("Datastore.implementation", "FakeDataStore",
                         "Storage subsystem to use.")

config_lib.DEFINE_string("Blobstore.implementation", "MemoryStreamBlobStore",
                         "Blob storage subsystem to use.")

config_lib.DEFINE_string("Database.implementation", "",
                         "Relational database system to use.")

config_lib.DEFINE_bool(
    "Database.useForReads", False,
    "Use relational database for reading as well as for writing.")

config_lib.DEFINE_bool("Database.useForReads.audit", False,
                       "Use relational database for reading audit logs.")

config_lib.DEFINE_bool(
    "Database.useForReads.artifacts", False,
    "Enable reading artifact data from the relational database.")

config_lib.DEFINE_bool(
    "Database.useForReads.message_handlers", False,
    "Enable message handlers using the relational database.")

config_lib.DEFINE_bool("Database.useForReads.cronjobs", False,
                       "Enable storing cronjobs in the relational database.")

# Previously `Database.useForReads.flows`. This has been changed to allow
# testing relational flows separately and prevent confusion in the usage of
# RelationalDBReadEnabled(). This flag should not be True, when
# Database.useForReads is False.
config_lib.DEFINE_bool("Database.useRelationalFlows", False,
                       "Enable storing flows in the relational database.")

config_lib.DEFINE_bool(
    "Database.useForReads.client_messages", False,
    "Enable storing client messages in the relational "
    "database.")

config_lib.DEFINE_bool("Database.useForReads.foreman", False,
                       "Enable the foreman using the relational database.")

config_lib.DEFINE_bool("Database.useForReads.vfs", False,
                       "Use relational database for reading VFS information.")

config_lib.DEFINE_bool(
    "Database.useForReads.filestore", False,
    "Use relational database for reading files from filestore.")

config_lib.DEFINE_bool("Database.useForReads.stats", False,
                       "Read server metrics from the relational database.")

config_lib.DEFINE_bool("Database.useForReads.signed_binaries", False,
                       "Read signed binary data from the relational database.")

config_lib.DEFINE_bool("Database.aff4_enabled", True,
                       "Enables reading/writing to the legacy data store.")

DATASTORE_PATHING = [
    r"%{(?P<path>files/hash/generic/sha256/...).*}",
    r"%{(?P<path>files/hash/generic/sha1/...).*}",
    r"%{(?P<path>files/hash/generic/md5/...).*}",
    r"%{(?P<path>files/hash/pecoff/md5/...).*}",
    r"%{(?P<path>files/hash/pecoff/sha1/...).*}",
    r"%{(?P<path>files/nsrl/...).*}", r"%{(?P<path>W/[^/]+).*}",
    r"%{(?P<path>CA/[^/]+).*}", r"%{(?P<path>C\..\{1,16\}?)($|/.*)}",
    r"%{(?P<path>hunts/[^/]+).*}", r"%{(?P<path>blobs/[^/]+).*}",
    r"%{(?P<path>[^/]+).*}"
]

config_lib.DEFINE_list("Datastore.pathing", DATASTORE_PATHING,
                       ("Path selection for subjects in the file-based data "
                        "stores (by priority)."))

config_lib.DEFINE_string(
    "Datastore.location",
    default="%(Config.prefix)/var/grr-datastore",
    help=("Location of the data store (usually a "
          "filesystem directory)"))

# SQLite data store.
# NOTE: The SQLite datastore was obsoleted, so these options do not get
# used. We can remove them once users have migrated to MySQL.
config_lib.DEFINE_integer(
    "SqliteDatastore.vacuum_check",
    default=10,
    help=("Number of rows that need to be deleted before "
          "checking if the sqlite file may need to be "
          "vacuumed."))

config_lib.DEFINE_integer(
    "SqliteDatastore.vacuum_frequency",
    default=60,
    help=("Minimum interval (in seconds) between vacuum"
          "operations on the same sqlite file."))

config_lib.DEFINE_integer(
    "SqliteDatastore.vacuum_minsize",
    default=10 * 1024,
    help=("Minimum size of sqlite file in bytes required"
          " for vacuuming"))

config_lib.DEFINE_integer(
    "SqliteDatastore.vacuum_ratio",
    default=50,
    help=("Percentage of pages that are free before "
          "vacuuming a sqlite file."))

config_lib.DEFINE_integer(
    "SqliteDatastore.connection_cache_size",
    default=1000,
    help=("Number of file handles kept in the SQLite "
          "data_store cache."))

# MySQLAdvanced data store.
config_lib.DEFINE_string("Mysql.host", "localhost",
                         "The MySQL server hostname.")

config_lib.DEFINE_integer("Mysql.port", 0, "The MySQL server port.")

config_lib.DEFINE_string(
    "Mysql.database_name", default="grr", help="Name of the database to use.")

config_lib.DEFINE_string(
    "Mysql.table_name", default="aff4", help="Name of the table to use.")

config_lib.DEFINE_string(
    "Mysql.database_username",
    default="root",
    help="The user to connect to the database.")

config_lib.DEFINE_string(
    "Mysql.database_password",
    default="",
    help="The password to connect to the database.")

config_lib.DEFINE_integer(
    "Mysql.conn_pool_max",
    10,
    help=("The maximum number of open connections to keep"
          " available in the pool."))

config_lib.DEFINE_integer(
    "Mysql.conn_pool_min",
    5,
    help=("The minimum number of open connections to keep"
          " available in the pool."))

config_lib.DEFINE_integer(
    "Mysql.max_connect_wait",
    600,
    help=("Total number of seconds we wait for a "
          "connection before failing (0 means we wait "
          "forever)."))

config_lib.DEFINE_integer(
    "Mysql.max_query_size",
    8 * 1024 * 1024,
    help=("Maximum query size (in bytes). Queries sent by GRR to MySQL "
          "may be slightly bigger than the specified maximum. This "
          "value has to be smaller than MySQL's max_allowed_packet "
          "configuration value."))

config_lib.DEFINE_integer(
    "Mysql.max_values_per_query",
    10000,
    help=("Maximum number of subjects touched by a single query."))

config_lib.DEFINE_integer(
    "Mysql.max_retries",
    10,
    help="Maximum number of retries (happens in case a query fails).")

# CloudBigTable data store.
config_lib.DEFINE_string(
    "CloudBigtable.project_id",
    default=None,
    help="The Google cloud project ID which will hold the bigtable.")

config_lib.DEFINE_string(
    "CloudBigtable.instance_location",
    default="us-central1-c",
    help="The google cloud zone for the instance. This needs to be in "
    "a zone that has bigtable available and ideally the same zone (or at "
    "least the same region) as the server for performance and billing "
    "reasons.")

config_lib.DEFINE_string(
    "CloudBigtable.instance_id",
    default="grrbigtable",
    help="The cloud bigtable instance ID.")

config_lib.DEFINE_string(
    "CloudBigtable.test_project_id",
    default=None,
    help="Set this to run the cloud bigtable tests. Note that billing applies! "
    "Always check your project has deleted the test instances correctly after "
    "running these tests.")

config_lib.DEFINE_string(
    "CloudBigtable.instance_name",
    default="grrbigtable",
    help="The cloud bigtable instance ID.")

config_lib.DEFINE_semantic_value(rdfvalue.Duration,
                                 "CloudBigtable.retry_interval", "1s",
                                 "Time to wait before first retry.")

config_lib.DEFINE_integer(
    "CloudBigtable.retry_max_attempts",
    default=5,
    help="Maximum number of retries on RPC before we give up.")

config_lib.DEFINE_integer("CloudBigtable.retry_multiplier", 2,
                          "For each retry, multiply last delay by this value.")

config_lib.DEFINE_string(
    "CloudBigtable.table_name",
    default="grrbigtable",
    help="The cloud bigtable table name.")

config_lib.DEFINE_integer(
    "CloudBigtable.threadpool_size", 100, "The threadpool size for making"
    "parallel RPC calls.")

config_lib.DEFINE_integer(
    "CloudBigtable.serve_nodes", 3, help=("Number of bigtable serve nodes."))
