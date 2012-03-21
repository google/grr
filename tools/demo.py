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

from grr.client import conf
from grr.client import conf as flags
from grr.client import client
from grr.gui import runtests
from grr.lib import registry
from grr.tools import http_server
from grr.worker import enroller
from grr.worker import worker


BASE_DIR = "grr/"
FLAGS = flags.FLAGS


def main(argv):
  """Sets up all the component in their own threads."""
  registry.Init()
  FLAGS.storage = "FakeDataStore"
  FLAGS.server_cert = BASE_DIR + "keys/test/server.pem"
  FLAGS.server_private_key = BASE_DIR + "keys/test/server-priv.pem"

  # This is the worker thread.
  worker_thread = threading.Thread(target=worker.main, args=[argv])
  worker_thread.daemon = True
  worker_thread.start()

  FLAGS.ca = BASE_DIR + "keys/test/ca-priv.pem"
  # This is the enroller thread.
  enroller_thread = threading.Thread(target=enroller.main, args=[argv])
  enroller_thread.daemon = True
  enroller_thread.start()

  # This is the http server that clients communicate with.
  FLAGS.http_bind_address = "127.0.0.1"
  FLAGS.http_bind_port = 8001
  http_thread = threading.Thread(target=http_server.main, args=[argv])
  http_thread.daemon = True
  http_thread.start()

  # Finally we start up a client too.
  FLAGS.location = "http://localhost:8001/control"
  FLAGS.camode = "test"
  FLAGS.config = "/tmp/grr_config.txt"
  FLAGS.poll_max = 5

  client_thread = threading.Thread(target=client.main, args=[argv])
  client_thread.daemon = True
  client_thread.start()

  # The admin ui is running in the main thread.
  runtests.main(argv)

if __name__ == "__main__":
  conf.StartMain(main)
