#!/usr/bin/env python
"""GRR check tests.

This module loads and registers all the check tests.
"""


# These need to register plugins so,
# pylint: disable=unused-import,g-import-not-at-top

from grr.lib.checks import checks_test
from grr.lib.checks import checks_test_lib_test
from grr.lib.checks import filters_test
from grr.lib.checks import hints_test
from grr.lib.checks import triggers_test
