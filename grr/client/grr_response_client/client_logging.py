#!/usr/bin/env python
"""Functions for client logging."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
from logging import handlers
import os
import socket

from grr_response_core import config
from grr_response_core.lib import flags


class PreLoggingMemoryHandler(handlers.BufferingHandler):
  """Handler used before logging subsystem is initialized."""

  def shouldFlush(self, record):
    return len(self.buffer) >= self.capacity

  def flush(self):
    """Flush the buffer.

    This is called when the buffer is really full, we just just drop one oldest
    message.
    """
    self.buffer = self.buffer[-self.capacity:]


class RobustSysLogHandler(handlers.SysLogHandler):
  """A handler which does not raise if it fails to connect."""

  def __init__(self, *args, **kwargs):
    self.formatter = None
    try:
      super(RobustSysLogHandler, self).__init__(*args, **kwargs)
    except socket.error:
      pass

  def handleError(self, record):
    """Just ignore socket errors - the syslog server might come back."""


BASE_LOG_LEVELS = {
    "FileHandler": logging.ERROR,
    "NTEventLogHandler": logging.CRITICAL,
    "StreamHandler": logging.ERROR,
    "RobustSysLogHandler": logging.CRITICAL,
}

VERBOSE_LOG_LEVELS = {
    "FileHandler": logging.DEBUG,
    "NTEventLogHandler": logging.INFO,
    "StreamHandler": logging.DEBUG,
    "RobustSysLogHandler": logging.INFO,
}


def SetLogLevels():
  logger = logging.getLogger()

  if config.CONFIG["Logging.verbose"] or flags.FLAGS.verbose:
    logging.root.setLevel(logging.DEBUG)
    levels = VERBOSE_LOG_LEVELS
  else:
    levels = BASE_LOG_LEVELS

  for handler in logger.handlers:
    handler.setLevel(levels[handler.__class__.__name__])


LOG_FORMAT = "%(levelname)s:%(asctime)s %(module)s:%(lineno)s] %(message)s"


def GetLogHandlers():
  formatter = logging.Formatter(LOG_FORMAT)
  engines = config.CONFIG["Logging.engines"]
  logging.debug("Will use logging engines %s", engines)

  for engine in engines:
    try:
      if engine == "stderr":
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        yield handler

      elif engine == "event_log":
        handler = handlers.NTEventLogHandler("GRR")
        handler.setFormatter(formatter)
        yield handler

      elif engine == "syslog":
        # Allow the specification of UDP sockets.
        socket_name = config.CONFIG["Logging.syslog_path"]
        if ":" in socket_name:
          addr, port = socket_name.split(":", 1)
          handler = RobustSysLogHandler((addr, int(port)))
        else:
          handler = RobustSysLogHandler(socket_name)

        handler.setFormatter(formatter)
        yield handler

      elif engine == "file":
        # Create a logfile if needed.
        path = config.CONFIG["Logging.filename"]
        logging.info("Writing log file to %s", path)

        if not os.path.isdir(os.path.dirname(path)):
          os.makedirs(os.path.dirname(path))
        handler = logging.FileHandler(path, mode="ab")
        handler.setFormatter(formatter)
        yield handler

      else:
        logging.error("Unknown logging engine %s", engine)

    except Exception:  # pylint:disable=broad-except
      # Failure to log should not be fatal.
      logging.exception("Unable to create logger %s", engine)


def LogInit():
  """Configure the logging subsystem."""
  logging.debug("Initializing client logging subsystem.")

  # The root logger.
  logger = logging.getLogger()
  memory_handlers = [
      m for m in logger.handlers
      if m.__class__.__name__ == "PreLoggingMemoryHandler"
  ]

  # Clear all handers.
  logger.handlers = list(GetLogHandlers())
  SetLogLevels()

  # Now flush the old messages into the log files.
  for handler in memory_handlers:
    for record in handler.buffer:
      logger.handle(record)


# There is a catch 22 here: We need to start logging right away but we will only
# configure the logging system once the config is read. Therefore we set up a
# memory logger now and then when the log destination is configured we replay
# the logs into that. This ensures we do not lose any log messages during early
# program start up.
root_logger = logging.root
memory_logger = PreLoggingMemoryHandler(1000)
root_logger.addHandler(memory_logger)
memory_logger.setLevel(logging.DEBUG)
logging.debug("Starting GRR Prelogging buffer.")
