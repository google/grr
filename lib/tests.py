#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.

"""GRR library tests.

This module loads and registers all the GRR library tests.
"""


# These need to register plugins so, pylint: disable=unused-import
from grr.lib import access_control_test
from grr.lib import aff4_test
from grr.lib import build_test
from grr.lib import communicator_test
from grr.lib import config_lib_test
from grr.lib import config_validation_test
from grr.lib import cron_test
from grr.lib import data_store_test
from grr.lib import export_utils_test
from grr.lib import flow_test
from grr.lib import flow_utils_test
from grr.lib import front_end_test
from grr.lib import hunt_test
from grr.lib import lexer_test
from grr.lib import objectfilter_test
from grr.lib import scheduler_test
from grr.lib import search_test
from grr.lib import stats_test
from grr.lib import test_lib
from grr.lib import threadpool_test
from grr.lib import type_info_test
from grr.lib import utils_test

from grr.lib.aff4_objects import tests
from grr.lib.data_stores import tests
from grr.lib.flows import tests
from grr.lib.rdfvalues import tests
from grr.tools import entry_point_test
# pylint: enable=unused-import
