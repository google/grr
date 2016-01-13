#!/usr/bin/env python
"""GRR GUI plugins simplify the task of displaying different GUI elements."""

# pylint: disable=unused-import
# TODO(user): automate the generation of this file
from grr.gui.plugins import acl_manager
from grr.gui.plugins import artifact_view
from grr.gui.plugins import configuration_view
from grr.gui.plugins import container_viewer
from grr.gui.plugins import crash_view
from grr.gui.plugins import cron_view
from grr.gui.plugins import docs_view
from grr.gui.plugins import fileview
from grr.gui.plugins import flow_management
from grr.gui.plugins import foreman
from grr.gui.plugins import forms
from grr.gui.plugins import hunt_view
from grr.gui.plugins import inspect_view
from grr.gui.plugins import new_hunt
from grr.gui.plugins import notifications
from grr.gui.plugins import reports_view
from grr.gui.plugins import searchclient
from grr.gui.plugins import semantic
from grr.gui.plugins import server_load_view
from grr.gui.plugins import statistics
from grr.gui.plugins import timeline_view
from grr.gui.plugins import usage
from grr.gui.plugins import wizards

# pylint: disable=g-import-not-at-top
try:
  from grr.gui.plugins import rekall_viewer
except ImportError:
  pass
