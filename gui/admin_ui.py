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

"""This is a development server for running the admin ui."""


import logging
import os
import SocketServer
import sys
from wsgiref import simple_server

from django.core.handlers import wsgi
from django.core.management import setup_environ
from grr.client import conf
from grr.client import conf as flags

from grr.gui import settings
from grr.lib import registry

# This needs to happen so that django can pre-import all the plugins
SITE_SETTINGS = "grr.gui.settings"
os.environ["DJANGO_SETTINGS_MODULE"] = SITE_SETTINGS

from grr.lib import access_control
# Support mongo storage
from grr.lib import mongo_data_store

# Support grr plugins (These only need to be imported here)
from grr.lib.flows import general
from grr.gui import plugins

flags.DEFINE_integer("port", 8000,
                     "port to listen on")

flags.DEFINE_string("bind", "0.0.0.0",
                    "interface to bind to.")

# This allows users to specify access controls for the gui.
flags.DEFINE_string("htpasswd", None,
                    "An apache style htpasswd file for gui access control.")

FLAGS = flags.FLAGS


if settings.SECRET_KEY == "CHANGE_ME":
  logging.error("Please change the secret key in the settings module.")


class ThreadingDjango(SocketServer.ThreadingMixIn, simple_server.WSGIServer):
  pass


def main(_):
  """Run the main test harness."""
  registry.Init()

  setup_environ(settings)

  if FLAGS.htpasswd is None:
    logging.error("Please specify the --htpasswd option to enable "
                  "security on the admin interface.")
    sys.exit(-1)

  # Start up a server in another thread
  base_url = "http://%s:%d" % (FLAGS.bind, FLAGS.port)
  logging.info("Base URL is %s", base_url)

  # Make a simple reference implementation WSGI server
  server = simple_server.make_server(FLAGS.bind, FLAGS.port,
                                     wsgi.WSGIHandler(),
                                     server_class=ThreadingDjango)

  server.serve_forever()


if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO)

  conf.StartMain(main)
