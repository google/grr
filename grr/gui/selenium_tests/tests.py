#!/usr/bin/env python
"""This module loads all the selenium tests for the GUI."""



# pylint: disable=unused-import
from grr.gui.selenium_tests import acl_manager_test
from grr.gui.selenium_tests import api_docs_test
from grr.gui.selenium_tests import artifact_manager_test
from grr.gui.selenium_tests import artifact_view_test
from grr.gui.selenium_tests import crash_view_test
from grr.gui.selenium_tests import cron_create_test
from grr.gui.selenium_tests import cron_view_test
from grr.gui.selenium_tests import dir_recursive_refresh_test
from grr.gui.selenium_tests import dir_refresh_test
from grr.gui.selenium_tests import email_links_test
from grr.gui.selenium_tests import fileview_test
from grr.gui.selenium_tests import flow_archive_test
from grr.gui.selenium_tests import flow_copy_test
from grr.gui.selenium_tests import flow_create_hunt_test
from grr.gui.selenium_tests import flow_export_test
from grr.gui.selenium_tests import flow_management_test
from grr.gui.selenium_tests import flow_notifications_test
from grr.gui.selenium_tests import forms_test
from grr.gui.selenium_tests import hostinfo_test
from grr.gui.selenium_tests import hosttable_test
from grr.gui.selenium_tests import hunt_archive_test
from grr.gui.selenium_tests import hunt_control_test
from grr.gui.selenium_tests import hunt_copy_test
from grr.gui.selenium_tests import hunt_create_test
from grr.gui.selenium_tests import hunt_results_view_test
from grr.gui.selenium_tests import hunt_view_test
from grr.gui.selenium_tests import inspect_view_test
from grr.gui.selenium_tests import main_content_view_test
from grr.gui.selenium_tests import navigator_view_test
from grr.gui.selenium_tests import notifications_test
from grr.gui.selenium_tests import rekall_flows_test
from grr.gui.selenium_tests import report_test
from grr.gui.selenium_tests import searchclient_test
from grr.gui.selenium_tests import server_load_view_test
from grr.gui.selenium_tests import settings_view_test
from grr.gui.selenium_tests import timeline_test
from grr.gui.selenium_tests import userdashboard_test
from grr.gui.selenium_tests import vfsview_test
