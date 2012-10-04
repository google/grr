#!/usr/bin/env python
# Copyright 2012 Google Inc.
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


"""This sets up log levels for the client."""



from logging import handlers
import os
import platform

from grr.client import conf as flags
import logging

from grr.client import client_config
from grr.client import conf

FLAGS = flags.FLAGS


conf.PARSER.add_option("", "--clientlog", default=client_config.LOGFILE_PATH,
                       help="Path to log file.")


def SetLogLevels():
  """This sets the correct log levels for all the client loggers."""

  levels = {
      "FileHandler": logging.ERROR,
      "NTEventLogHandler": logging.CRITICAL,
      "StreamHandler": logging.ERROR,
      "SysLogHandler": logging.CRITICAL,
      }

  verbose_levels = {
      "FileHandler": logging.DEBUG,
      "NTEventLogHandler": logging.INFO,
      "StreamHandler": logging.DEBUG,
      "SysLogHandler": logging.INFO,
      }

  logger = logging.getLogger()

  act_levels = levels

  if FLAGS.verbose:

    act_levels = verbose_levels

    if "FileHandler" not in [handler.__class__.__name__
                             for handler in logger.handlers]:
      # Create a logfile.
      path = FLAGS.clientlog
      if not os.path.isdir(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))
      filehandler = logging.FileHandler(path, mode="ab")
      logger.addHandler(filehandler)

  # Standard log level, has to be higher than all handler levels.
  logger.setLevel(act_levels["StreamHandler"])

  for handler in logger.handlers:
    handler.setLevel(act_levels[handler.__class__.__name__])


def SetUpClientLogging():
  """This sets up all the client loggers."""

  logging.basicConfig(level=logging.INFO,
                      format="[%(levelname)s "
                      "%(module)s:%(lineno)s] %(message)s")

  logger = logging.getLogger()
  # Set general debug logging.
  logger.setLevel(logging.DEBUG)

  system = platform.system()
  if system == "Linux":
    # Log to Syslog.
    handler = handlers.SysLogHandler("/dev/log")
    logger.addHandler(handler)
  elif system == "Darwin":
    # Log to Syslog using UDP.
    handler = handlers.SysLogHandler()
    logger.addHandler(handler)
  elif system == "Windows":
    # Log to EventLog.
    handler = handlers.NTEventLogHandler(client_config.SERVICE_NAME)
    logger.addHandler(handler)

  SetLogLevels()
