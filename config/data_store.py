#!/usr/bin/env python
"""Configuration parameters for the data stores."""

from grr.lib import config_lib

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

DATASTORE_PATHING = [r"%{(?P<path>files/hash/generic/sha256/...).*}",
                     r"%{(?P<path>files/hash/generic/sha1/...).*}",
                     r"%{(?P<path>files/hash/generic/md5/...).*}",
                     r"%{(?P<path>files/hash/pecoff/md5/...).*}",
                     r"%{(?P<path>files/hash/pecoff/sha1/...).*}",
                     r"%{(?P<path>files/nsrl/...).*}",
                     r"%{(?P<path>W/[^/]+).*}",
                     r"%{(?P<path>CA/[^/]+).*}",
                     r"%{(?P<path>C\..\{1,16\}?)($|/.*)}",
                     r"%{(?P<path>hunts/[^/]+).*}",
                     r"%{(?P<path>blobs/[^/]+).*}",
                     r"%{(?P<path>[^/]+).*}"]

config_lib.DEFINE_list("Datastore.pathing", DATASTORE_PATHING,
                       ("Path selection for subjects in the file-based data "
                        "stores (by priority)."))

config_lib.DEFINE_string("Datastore.location", default="/var/grr-datastore",
                         help=("Location of the data store (usually a "
                               "filesystem directory)"))

# SQLite data store.
config_lib.DEFINE_integer("SqliteDatastore.vacuum_check", default=10,
                          help=("Number of rows that need to be deleted before "
                                "checking if the sqlite file may need to be "
                                "vacuumed."))

config_lib.DEFINE_integer("SqliteDatastore.vacuum_frequency", default=60,
                          help=("Minimum interval (in seconds) between vacuum"
                                "operations on the same sqlite file."))

config_lib.DEFINE_integer("SqliteDatastore.vacuum_minsize", default=10*1024,
                          help=("Minimum size of sqlite file in bytes required"
                                " for vacuuming"))

config_lib.DEFINE_integer("SqliteDatastore.vacuum_ratio", default=50,
                          help=("Percentage of pages that are free before "
                                "vacuuming a sqlite file."))

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

# HTTP data store.
config_lib.DEFINE_string("HTTPDataStore.username", default="",
                         help="The username to connect to the http data store.")

config_lib.DEFINE_string("HTTPDataStore.password", default="",
                         help="The password to connect to the http data store.")
