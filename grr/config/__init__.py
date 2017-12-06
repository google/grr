#!/usr/bin/env python
"""This module will load all the configuration parameters."""

# pylint: disable=unused-import
from grr.config import acls
from grr.config import api
from grr.config import artifacts
from grr.config import build
from grr.config import checks
from grr.config import client
from grr.config import config
from grr.config import contexts
from grr.config import data_store
from grr.config import gui
from grr.config import local
from grr.config import logging
from grr.config import output_plugins
from grr.config import server
from grr.config import test
# pylint: enable=unused-import

from grr.lib import config_lib

# By this time it's guaranteed that all configuration options
# and filters are imported and known to the config system.
CONFIG = config_lib._CONFIG  # pylint: disable=protected-access
