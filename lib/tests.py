#!/usr/bin/env python
# Copyright 2012 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""GRR library tests.

This module loads and registers all the GRR library tests.
"""


# These need to register plugins so, pylint: disable=W0611
from grr.lib import access_control_test
from grr.lib import aff4_test
from grr.lib import communicator_test
from grr.lib import config_lib_test
from grr.lib import data_store_test
from grr.lib import flow_test
from grr.lib import flow_utils_test
from grr.lib import front_end_test
from grr.lib import hunt_test
from grr.lib import lexer_test
from grr.lib import objectfilter_test
from grr.lib import scheduler_test
from grr.lib import stats_test
from grr.lib import test_lib
from grr.lib import threadpool_test
from grr.lib import type_info_test
from grr.lib import utils_test

from grr.lib.data_stores import tests
from grr.lib.flows import tests
from grr.lib.rdfvalues import tests
# pylint: enable=W0611
