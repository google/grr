#!/usr/bin/env python
"""GRR library tests.

This module loads and registers all the GRR library tests.
"""


# These need to register plugins
# pylint: disable=unused-import,g-import-not-at-top

from grr.lib import build_test
from grr.lib import communicator_test
from grr.lib import config_lib_test
from grr.lib import config_validation_test
from grr.lib import ipv6_utils_test
from grr.lib import lexer_test
from grr.lib import objectfilter_test
from grr.lib import parsers_test
from grr.lib import repacking_test
from grr.lib import stats_test
from grr.lib import type_info_test
from grr.lib import uploads_test
from grr.lib import utils_test

from grr.lib.builders import tests
from grr.lib.rdfvalues import tests

from grr.tools import frontend_test
# pylint: enable=unused-import,g-import-not-at-top
