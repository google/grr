#!/usr/bin/env python
"""Configuration parameters for the data stores."""


from grr_response_core.lib import config_lib

config_lib.DEFINE_integer("Datastore.maximum_blob_size", 512 * 1024,
                          "Maximum blob size we may store in the datastore.")

config_lib.DEFINE_string("Blobstore.implementation", "DbBlobStore",
                         "Blob storage subsystem to use.")

config_lib.DEFINE_string("Database.implementation", "",
                         "Relational database system to use.")

# MySQL configuration.
config_lib.DEFINE_string("Mysql.host", "localhost",
                         "The MySQL server hostname.")

config_lib.DEFINE_integer("Mysql.port", 0, "The MySQL server port.")

config_lib.DEFINE_string(
    "Mysql.username",
    default="root",
    help="The user to connect to the database.")

config_lib.DEFINE_string(
    "Mysql.password",
    default="",
    help="The password to connect to the database.")

config_lib.DEFINE_string(
    "Mysql.database", default="grr_db", help="Name of the database to use.")

config_lib.DEFINE_integer(
    "Mysql.conn_pool_max",
    default=10,
    help="The maximum number of open connections to keep available in the pool."
)

config_lib.DEFINE_string(
    "Mysql.migrations_dir", "%(grr_response_server/databases/mysql_migrations@"
    "grr-response-server|resource)", "Folder with MySQL migrations files.")

# Support for MySQL SSL connections.

config_lib.DEFINE_string(
    "Mysql.client_key_path",
    default="",
    help="The path name of the client private key file.")

config_lib.DEFINE_string(
    "Mysql.client_cert_path",
    default="",
    help="The path name of the client public key certificate file.")

config_lib.DEFINE_string(
    "Mysql.ca_cert_path",
    default="",
    help="The path name of the Certificate Authority (CA) certificate file. "
    "This option, if used, must specify the same certificate used by the "
    "server.")

# Legacy MySQLAdvancedDataStore used as AFF4 backend.
config_lib.DEFINE_string(
    "Mysql.database_name", default="grr", help="Deprecated.")

config_lib.DEFINE_string("Mysql.table_name", default="aff4", help="Deprecated.")

config_lib.DEFINE_string(
    "Mysql.database_username", default="root", help="Deprecated.")

config_lib.DEFINE_string(
    "Mysql.database_password", default="", help="Deprecated.")

config_lib.DEFINE_integer("Mysql.conn_pool_min", 5, help="Deprecated.")

config_lib.DEFINE_integer("Mysql.max_connect_wait", 600, help="Deprecated.")

config_lib.DEFINE_integer(
    "Mysql.max_query_size", 8 * 1024 * 1024, help="Deprecated.")

config_lib.DEFINE_integer(
    "Mysql.max_values_per_query", 10000, help="Deprecated.")

config_lib.DEFINE_integer("Mysql.max_retries", 10, help="Deprecated.")
