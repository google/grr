#!/usr/bin/env python
"""This module will load all the configuration parameters."""

# pylint: disable=unused-import
from grr.core.grr_response_core.config import acls
from grr.core.grr_response_core.config import api
from grr.core.grr_response_core.config import artifacts
from grr.core.grr_response_core.config import build
from grr.core.grr_response_core.config import checks
from grr.core.grr_response_core.config import client
from grr.core.grr_response_core.config import config
from grr.core.grr_response_core.config import contexts
from grr.core.grr_response_core.config import data_store
from grr.core.grr_response_core.config import gui
from grr.core.grr_response_core.config import local
from grr.core.grr_response_core.config import logging
from grr.core.grr_response_core.config import output_plugins
from grr.core.grr_response_core.config import server
from grr.core.grr_response_core.config import test
# pylint: enable=unused-import

from grr.core.grr_response_core.lib import config_lib

# By this time it's guaranteed that all configuration options
# and filters are imported and known to the config system.
CONFIG = config_lib._CONFIG  # pylint: disable=protected-access
