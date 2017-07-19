#!/usr/bin/env python
"""Functions for audit and logging."""



import logging
from logging import handlers
import os
import socket
import time

from grr import config
from grr.config import contexts
from grr.lib import flags

# Global Application Logger.
LOGGER = None


class GrrApplicationLogger(object):
  """The GRR application logger.

  These records are used for machine readable authentication logging of security
  critical events.
  """

  def GetNewEventId(self, event_time=None):
    """Return a unique Event ID string."""
    if event_time is None:
      event_time = long(time.time() * 1e6)

    return "%s:%s:%s" % (event_time, socket.gethostname(), os.getpid())

  def LogHttpAdminUIAccess(self, request, response):
    """Log an http based api call.

    Args:
      request: A WSGI request object.
      response: A WSGI response object.
    """
    # TODO(user): generate event_id elsewhere and use it for all the log
    # messages that have to do with handling corresponding request.
    event_id = self.GetNewEventId()

    api_method = response.headers.get("X-API-Method", "unknown")
    api_reason = response.headers.get("X-GRR-Reason", "none")
    log_msg = "%s API call [%s] by %s (reason: %s): %s [%d]" % (
        event_id, api_method, request.user, api_reason, request.full_path,
        response.status_code)
    logging.info(log_msg)

  def LogHttpFrontendAccess(self, request, source=None, message_count=None):
    """Write a log entry for a Frontend or UI Request.

    Args:
      request: A HttpRequest protobuf.
      source: Client id of the client initiating the request. Optional.
      message_count: Number of messages received from the client. Optional.
    """
    # TODO(user): generate event_id elsewhere and use it for all the log
    # messages that have to do with handling corresponding request.
    event_id = self.GetNewEventId()

    log_msg = "%s-%s [%s]: %s %s %s %s (%d)" % (event_id, request.source_ip,
                                                source or "<unknown>",
                                                request.method, request.url,
                                                request.user_agent,
                                                request.user,
                                                message_count or 0)
    logging.info(log_msg)


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
    levels = VERBOSE_LOG_LEVELS
  else:
    levels = BASE_LOG_LEVELS

  for handler in logger.handlers:
    handler.setLevel(levels[handler.__class__.__name__])


def GetLogHandlers():
  formatter = logging.Formatter(config.CONFIG["Logging.format"])
  engines = config.CONFIG["Logging.engines"]
  logging.debug("Will use logging engines %s", engines)

  for engine in engines:
    try:
      if engine == "stderr":
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        yield handler

      elif engine == "event_log":
        handler = handlers.NTEventLogHandler(
            config.CONFIG["Logging.service_name"])
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
  logging.debug("Initializing Logging subsystem.")

  if flags.FLAGS.verbose:
    # verbose flag just sets the logging verbosity level.
    config.CONFIG.AddContext(
        contexts.DEBUG_CONTEXT,
        "This context is to allow verbose and debug output from "
        "the binary.")

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


def AppLogInit():
  """Initialize the Application Log.

  This log is what will be used whenever someone does a log.LOGGER call. These
  are used for more detailed application or event logs.

  Returns:
    GrrApplicationLogger object
  """
  logging.debug("Initializing Application Logger.")
  return GrrApplicationLogger()


def ServerLoggingStartupInit():
  """Initialize the server logging configuration."""
  global LOGGER
  try:
    # pylint: disable=g-import-not-at-top
    from grr.lib.local import log as local_log
    # pylint: enable=g-import-not-at-top
    logging.debug("Using local LogInit from %s", local_log)
    local_log.LogInit()
    logging.debug("Using local AppLogInit from %s", local_log)
    LOGGER = local_log.AppLogInit()
  except ImportError:
    LogInit()
    LOGGER = AppLogInit()


# There is a catch 22 here: We need to start logging right away but we will only
# configure the logging system once the config is read. Therefore we set up a
# memory logger now and then when the log destination is configured we replay
# the logs into that. This ensures we do not lose any log messages during early
# program start up.
root_logger = logging.root
root_logger.addHandler(PreLoggingMemoryHandler(1000))
root_logger.setLevel(logging.DEBUG)
logging.info("Starting GRR Prelogging buffer.")
