#!/usr/bin/env python
"""All the test files for API renderers plugins are imported here."""


# These need to register plugins so, pylint: disable=unused-import
from grr.gui.api_plugins import artifact_regression_test
from grr.gui.api_plugins import artifact_test
from grr.gui.api_plugins import client_regression_test
from grr.gui.api_plugins import client_test
from grr.gui.api_plugins import config_regression_test
from grr.gui.api_plugins import config_test
from grr.gui.api_plugins import cron_regression_test
from grr.gui.api_plugins import cron_test
from grr.gui.api_plugins import flow_regression_test
from grr.gui.api_plugins import flow_test
from grr.gui.api_plugins import hunt_regression_test
from grr.gui.api_plugins import hunt_test
from grr.gui.api_plugins import output_plugin_regression_test
from grr.gui.api_plugins import reflection_regression_test
from grr.gui.api_plugins import reflection_test
from grr.gui.api_plugins import stats_regression_test
from grr.gui.api_plugins import user_regression_test
from grr.gui.api_plugins import user_test
from grr.gui.api_plugins import vfs_regression_test
from grr.gui.api_plugins import vfs_test
from grr.gui.api_plugins.report_plugins import tests
