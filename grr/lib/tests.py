#!/usr/bin/env python
"""GRR library tests.

This module loads and registers all the GRR library tests.
"""


# These need to register plugins so, pylint: disable=unused-import,g-import-not-at-top
# pylint: disable=g-import-not-at-top
from grr.lib import aff4_test
from grr.lib import artifact_test
from grr.lib import artifact_utils_test
try:
  from grr.lib import bigquery_test
except ImportError:
  pass

from grr.lib import build_test
from grr.lib import client_index_test
from grr.lib import communicator_test
from grr.lib import config_lib_test
from grr.lib import config_validation_test
from grr.lib import console_utils_test
from grr.lib import data_store_test
from grr.lib import email_alerts_test
from grr.lib import export_test
from grr.lib import export_utils_test
from grr.lib import flow_test
from grr.lib import flow_utils_test
from grr.lib import front_end_test
from grr.lib import fuse_mount_test
from grr.lib import hunt_test
from grr.lib import ipv6_utils_test
from grr.lib import lexer_test
from grr.lib import objectfilter_test
from grr.lib import output_plugin_test
from grr.lib import parsers_test
from grr.lib import queue_manager_test
from grr.lib import rekall_profile_server_test
from grr.lib import repacking_test
from grr.lib import stats_test
from grr.lib import test_lib
from grr.lib import threadpool_test
from grr.lib import throttle_test
from grr.lib import type_info_test
from grr.lib import utils_test

from grr.lib.aff4_objects import tests
from grr.lib.authorization import tests
from grr.lib.builders import tests
from grr.lib.checks import tests
from grr.lib.data_stores import tests
from grr.lib.flows import tests
from grr.lib.hunts import tests
from grr.lib.local import tests
from grr.lib.output_plugins import tests
from grr.lib.rdfvalues import tests
# pylint: enable=unused-import
