#!/usr/bin/env python
"""This file defines the entry points for typical installations."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import flags

# pylint: disable=g-import-not-at-top


def Console():
  from grr_response_server.bin import console
  flags.StartMain(console.main)


def ApiShellRawAccess():
  from grr_response_server.bin import api_shell_raw_access
  flags.StartMain(api_shell_raw_access.main)


def ConfigUpdater():
  from grr_response_server.bin import config_updater
  flags.StartMain(config_updater.main)


def GrrServer():
  from grr_response_server.bin import grr_server
  flags.StartMain(grr_server.main)


def GrrFrontend():
  from grr_response_server.bin import frontend
  flags.StartMain(frontend.main)


def Worker():
  from grr_response_server.bin import worker
  flags.StartMain(worker.main)


def GRRFuse():
  from grr_response_server.bin import fuse_mount
  flags.StartMain(fuse_mount.main)


def AdminUI():
  from grr_response_server.gui import admin_ui
  flags.StartMain(admin_ui.main)
