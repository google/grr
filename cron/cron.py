#!/usr/bin/env python
# Copyright 2010 Google Inc. All Rights Reserved.

"""This is the main cron program to perform various housekeeping tasks."""



import re
import sys

from grr.client import conf

from grr.lib import config_lib
# pylint: disable=W0611
from grr.lib import server_plugins
# pylint: enable=W0611
from grr.lib import startup
from grr.lib.aff4_objects import cronjobs

config_lib.DEFINE_integer("Cron.override_frequency", None,
                          "Force the cron to run at this frequency. None "
                          "means use the default.")


def ConsoleMain():
  """Helper function for calling with setup tools entry points."""
  conf.StartMain(main)


def main(unused_argv):
  config_lib.CONFIG.SetEnv("Environment.component", "Cron")

  # Initialize everything
  startup.Init()

  cronjobs.RunAllCronJobs(
      override_frequency=config_lib.CONFIG["Cron.override_frequency"])

if __name__ == "__main__":
  ConsoleMain()
