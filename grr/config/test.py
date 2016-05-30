#!/usr/bin/env python
"""Configuration parameters for the test subsystem."""
from grr.lib import config_lib

# Default for running in the current directory
config_lib.DEFINE_constant_string("Test.srcdir",
                                  "%(grr|module_path)/../",
                                  "The directory containing the source code.")

config_lib.DEFINE_constant_string(
    "Test.data_dir",
    default="%(test_data@grr-response-test|resource)",
    help="The directory where test data exist.")

config_lib.DEFINE_constant_string(
    "Test.additional_test_config",
    default="%(Test.data_dir)/localtest.yaml",
    help="The path to a test config with local customizations.")

config_lib.DEFINE_string("Test.tmpdir",
                         "/tmp/",
                         help="Somewhere to write temporary files.")

config_lib.DEFINE_string("Test.data_store", "FakeDataStore",
                         "The data store to run the tests against.")

config_lib.DEFINE_integer("Test.remote_pdb_port", 2525, "Remote debugger port.")

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

config_lib.DEFINE_string("Test.end_to_end_data_dir", "%(Test.data_dir)",
                         "The directory containing test data used in end to "
                         "end tests.")

config_lib.DEFINE_string("PrivateKeys.ca_key_raw_data", "",
                         "For testing purposes.")
