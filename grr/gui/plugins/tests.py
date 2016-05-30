#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.
"""This module loads all the selenium tests for the GUI."""



# pylint: disable=unused-import
from grr.gui.plugins import acl_manager_test
from grr.gui.plugins import api_docs_test
from grr.gui.plugins import artifact_manager_test
from grr.gui.plugins import artifact_view_test
from grr.gui.plugins import container_viewer_test
from grr.gui.plugins import crash_view_test
from grr.gui.plugins import cron_view_test
from grr.gui.plugins import fileview_test
from grr.gui.plugins import flow_management_test
from grr.gui.plugins import forms_test
from grr.gui.plugins import hunt_view_test
from grr.gui.plugins import inspect_view_test
from grr.gui.plugins import new_hunt_test
from grr.gui.plugins import notifications_test
from grr.gui.plugins import rekall_viewer_test
from grr.gui.plugins import searchclient_test
from grr.gui.plugins import server_load_view_test
from grr.gui.plugins import statistics_test
from grr.gui.plugins import timeline_view_test
from grr.gui.plugins import usage_test
