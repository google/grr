#!/usr/bin/env python
# Copyright 2011 Google Inc.
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

"""This is a single binary demo program."""


import threading


# pylint: disable=unused-import,g-bad-import-order
from grr.gui import admin_ui
# pylint: enable=unused-import,g-bad-import-order

from grr.client import conf
from grr.client import conf as flags

from grr.client import client
from grr.gui import runtests
from grr.lib import config_lib
from grr.lib import registry
from grr.tools import http_server
from grr.worker import enroller
from grr.worker import worker


BASE_DIR = "grr/"


def main(argv):
  """Sets up all the component in their own threads."""
  # For testing we use the test config file.
  flags.FLAGS.config = [config_lib.CONFIG["Test.config"]]

  config_lib.CONFIG.SetEnv("Environment.component", "Demo")

  config_lib.ReloadConfig()

  registry.TestInit()

  # pylint: disable=unused-import,unused-variable
  from grr.gui import gui_plugins
  # pylint: enable=unused-import,unused-variable

  # This is the worker thread.
  worker_thread = threading.Thread(target=worker.main, args=[argv],
                                   name="Worker")
  worker_thread.daemon = True
  worker_thread.start()

  # This is the enroller thread.
  enroller_thread = threading.Thread(target=enroller.main, args=[argv],
                                     name="Enroller")
  enroller_thread.daemon = True
  enroller_thread.start()

  # This is the http server Frontend that clients communicate with.
  http_thread = threading.Thread(target=http_server.main, args=[argv],
                                 name="HTTP Server")
  http_thread.daemon = True
  http_thread.start()

  client_thread = threading.Thread(target=client.main, args=[argv],
                                   name="Client")
  client_thread.daemon = True
  client_thread.start()

  # The UI is running in the main thread.
  runtests.main(argv)

if __name__ == "__main__":
  conf.StartMain(main)
