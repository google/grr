#!/usr/bin/env python
"""GRR check tests.

This module loads and registers tests of check configurations.
"""


# These need to register plugins so,
# pylint: disable=unused-import,g-import-not-at-top
from grr.checks import cron_test
from grr.checks import format_test
from grr.checks import mounts_test
from grr.checks import nfs_test
from grr.checks import pam_test
from grr.checks import paths_test
from grr.checks import pkg_sources_test
from grr.checks import rsyslog_test
from grr.checks import services_test
from grr.checks import sshd_test
from grr.checks import stat_test
from grr.checks import sysctl_test
from grr.checks import time_test
from grr.checks import unix_login_test
