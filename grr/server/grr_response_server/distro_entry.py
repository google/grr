#!/usr/bin/env python
"""This file defines the entry points for typical installations."""

from absl import app

# pylint: disable=g-import-not-at-top


def Console():
  from grr_response_server.bin import console
  app.run(console.main)


def ApiShellRawAccess():
  from grr_response_server.bin import api_shell_raw_access
  app.run(api_shell_raw_access.main)


def ConfigUpdater():
  from grr_response_server.bin import config_updater
  config_updater.Run()


def GrrServer():
  from grr_response_server.bin import grr_server
  app.run(grr_server.main)


def GrrFrontend():
  from grr_response_server.bin import fleetspeak_frontend

  app.run(fleetspeak_frontend.main)


def Worker():
  from grr_response_server.bin import worker
  app.run(worker.main)


def AdminUI():
  from grr_response_server.gui import admin_ui
  app.run(admin_ui.main)


def Grrafana():
  from grr_response_server.bin import grrafana
  app.run(grrafana.main)


def FleetspeakServer():
  from grr_response_server.bin import fleetspeak_server_wrapper
  app.run(fleetspeak_server_wrapper.main)
