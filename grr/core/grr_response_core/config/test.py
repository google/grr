#!/usr/bin/env python
"""Configuration parameters for the test subsystem."""

from grr_response_core.lib import config_lib

config_lib.DEFINE_constant_string(
    "Test.data_dir",
    default="%(grr_response_test/test_data@grr-response-test|resource)",
    help="The directory where test data exist.")

config_lib.DEFINE_constant_string(
    "Test.additional_test_config",
    default="%(Test.data_dir)/localtest.yaml",
    help="The path to a test config with local customizations.")

config_lib.DEFINE_integer("SharedMemoryDB.port", 0,
                          "Port used to connect to SharedMemoryDB server.")

config_lib.DEFINE_string(
    "Mysql.schema_dump_path", "%(grr_response_server/databases/mysql.ddl@"
    "grr-response-server|resource)",
    "Location of the dumped MySQL schema path.")
