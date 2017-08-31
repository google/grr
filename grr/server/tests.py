#!/usr/bin/env python
"""Server tests."""

import platform

# These need to register plugins so:
# pylint: disable=unused-import,g-import-not-at-top
from grr.server import aff4_test
from grr.server import artifact_test
from grr.server import artifact_utils_test
try:
  from grr.server import bigquery_test
except ImportError:
  pass
from grr.server import client_index_test
from grr.server import console_utils_test
from grr.server import data_store_test
if platform.system() == "Linux":
  # Trying to import this module on non-Linux platforms won't work.
  from grr.server import fuse_mount_test
from grr.server import email_alerts_test
from grr.server import events_test
from grr.server import export_test
from grr.server import export_utils_test
from grr.server import flow_test
from grr.server import flow_utils_test
from grr.server import front_end_test
from grr.server import hunt_test
from grr.server import instant_output_plugin_test
from grr.server import multi_type_collection_test
from grr.server import output_plugin_test
from grr.server import queue_manager_test
from grr.server import rekall_profile_server_test
from grr.server import sequential_collection_test
from grr.server import server_logging_test
from grr.server import server_stubs_test
from grr.server import stats_server_test
from grr.server import threadpool_test
from grr.server import throttle_test
from grr.server import timeseries_test
from grr.server.aff4_objects import tests
from grr.server.authorization import tests
from grr.server.checks import tests
from grr.server.data_server import tests
from grr.server.data_stores import tests
from grr.server.flows import tests
from grr.server.hunts import tests
from grr.server.output_plugins import tests
# pylint: enable=unused-import,g-import-not-at-top
