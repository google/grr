#!/usr/bin/env python
"""GRR data store tests.

This module loads and registers all the data store tests.
"""


# These need to register plugins so, pylint: disable=W0611

from grr.lib.data_stores import fake_data_store_test
from grr.lib.data_stores import mongo_data_store_test
