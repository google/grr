#!/usr/bin/env python
"""Configuration parameters for the test subsystem."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import config_lib

# Default for running in the current directory
config_lib.DEFINE_constant_string(
    "Test.srcdir",
    "%(grr_response_core|module_path)/../../../",
    "The directory containing the source code.")

config_lib.DEFINE_constant_string(
    "Test.data_dir",
    default="%(grr_response_test/test_data@grr-response-test|resource)",
    help="The directory where test data exist.")

config_lib.DEFINE_constant_string(
    "Test.additional_test_config",
    default="%(Test.data_dir)/localtest.yaml",
    help="The path to a test config with local customizations.")

config_lib.DEFINE_string(
    "Test.tmpdir", "/tmp/", help="Somewhere to write temporary files.")

config_lib.DEFINE_string("Test.data_store", "FakeDataStore",
                         "The data store to run the tests against.")

config_lib.DEFINE_integer("Test.remote_pdb_port", 2525, "Remote debugger port.")

config_lib.DEFINE_string("PrivateKeys.ca_key_raw_data", "",
                         "For testing purposes.")

config_lib.DEFINE_integer(
    "SharedFakeDataStore.port", 0,
    "Port used to connect to SharedFakeDataStore server.")
