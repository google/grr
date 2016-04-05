#!/usr/bin/env python
"""Load all aff4 objects in order to populate the registry.
"""
# pylint: disable=unused-import
from grr.lib.aff4_objects import aff4_grr
from grr.lib.aff4_objects import aff4_rekall
from grr.lib.aff4_objects import collects
from grr.lib.aff4_objects import cronjobs
from grr.lib.aff4_objects import filestore
from grr.lib.aff4_objects import filetypes
from grr.lib.aff4_objects import filters
from grr.lib.aff4_objects import network
from grr.lib.aff4_objects import security
from grr.lib.aff4_objects import software
from grr.lib.aff4_objects import standard
from grr.lib.aff4_objects import stats
from grr.lib.aff4_objects import stats_store
from grr.lib.aff4_objects import timeline
from grr.lib.aff4_objects import user_managers
from grr.lib.aff4_objects import users
