#!/usr/bin/env python
"""Configuration parameters for the test subsystem."""
import os
from grr.lib import config_lib

# Default for running in the current directory
config_lib.DEFINE_string("Test.srcdir",
                         os.path.normpath(os.path.dirname(__file__) + "/../.."),
                         "The directory containing the source code.")

config_lib.DEFINE_string("Test.tmpdir", "/tmp/",
                         help="Somewhere to write temporary files.")

config_lib.DEFINE_string("Test.data_dir",
                         default="%(Test.srcdir)/grr/test_data",
                         help="The directory where test data exist.")

config_lib.DEFINE_string(
    "Test.config",
    default="%(Test.srcdir)/grr/config/grr-server.yaml",
    help="The path where the test configuration file "
    "exists.")

config_lib.DEFINE_string("Test.data_store", "FakeDataStore",
                         "The data store to run the tests against.")

config_lib.DEFINE_integer("Test.remote_pdb_port", 2525,
                          "Remote debugger port.")

config_lib.DEFINE_list("Test.end_to_end_client_ids", [],
                       "List of client ids to perform regular end_to_end tests"
                       " on.  These clients should be always on and connected"
                       " to the network.")

config_lib.DEFINE_list("Test.end_to_end_client_hostnames", [],
                       "List of hostnames to perform regular end_to_end tests"
                       " on.  These clients should be always on and connected"
                       " to the network.")

config_lib.DEFINE_string("Test.end_to_end_result_check_wait", "50m",
                         "rdfvalue.Duration string that determines how long we "
                         "wait after starting the endtoend test hunt before we "
                         "check the results. Should be long enough that all "
                         "clients will have picked up the hunt, but not so "
                         "long that the flow gets timed out.")
