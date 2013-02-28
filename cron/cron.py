#!/usr/bin/env python
# Copyright 2010 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""This is the main cron program to perform various housekeeping tasks."""



import re
import sys

from grr.client import conf

from grr.lib import config_lib
# pylint: disable=W0611
from grr.lib import registry
from grr.lib import server_plugins
# pylint: enable=W0611

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
  registry.Init()

  cronjobs.RunAllCronJobs(
      override_frequency=config_lib.CONFIG["Cron.override_frequency"])

if __name__ == "__main__":
  ConsoleMain()
