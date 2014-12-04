#!/usr/bin/env python
"""Configuration parameters for the data servers."""

from grr.lib import config_lib

# The Data Store server.
config_lib.DEFINE_integer("Dataserver.stats_frequency", 60,
                          ("Time interval in seconds for data server "
                           "statistics updates"))

config_lib.DEFINE_list("Dataserver.server_list",
                       ["http://127.0.0.1:7000", "http://127.0.0.1:7001"],
                       "List of allowed data servers (first is the master).")

config_lib.DEFINE_integer("Dataserver.max_connections", 5,
                          ("Maximum number of connections to the data server "
                           "per process."))

config_lib.DEFINE_integer("Dataserver.port", 7000,
                          "Port for a specific data server.")

# Login information for clients of the data servers.
config_lib.DEFINE_list("Dataserver.client_credentials", ["user:pass:rw"],
                       "List of data server client credentials, given as "
                       "<username>:<password>:<mode> where mode is r or rw.")

# Login information used by data servers when registering with the master.
config_lib.DEFINE_string("Dataserver.server_username", "server",
                         "Username for servers.")

config_lib.DEFINE_string("Dataserver.server_password", "server",
                         "Password for servers.")
