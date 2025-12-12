#!/usr/bin/env python
"""Functions for server logging."""

import logging
from logging import handlers
import os
import socket
import time

from absl import flags

from grr_response_core import config
from grr_response_core.stats import metrics
from grr_response_server import data_store
from grr_response_server.models import events as models_events

try:
  # pylint: disable=g-import-not-at-top
  from grr_response_server.local import log as local_log
  # pylint: enable=g-import-not-at-top
except ImportError:
  local_log = None

# Global Application Logger.
LOGGER = None

_VERBOSE = flags.DEFINE_bool(
    "verbose",
    default=False,
    help="Turn on verbose logging.",
    allow_override=True,
)

LOG_CALLS_COUNTER = metrics.Counter("log_calls", fields=[("level", str)])


class GrrApplicationLogger(object):
  """The GRR application logger.

  These records are used for machine readable authentication logging of security
  critical events.
  """

  def GetNewEventId(self, event_time=None):
    """Return a unique Event ID string."""
    if event_time is None:
      event_time = int(time.time() * 1e6)

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
    api_reason = "none"
    if response.context:
      approval = response.context.approval
      if approval:
        api_reason = approval.reason

    log_msg = "%s API call [%s] by %s (reason: %s): %s [%d]" % (
        event_id,
        api_method,
        request.user,
        api_reason,
        request.full_path,
        response.status_code,
    )
    logging.info(log_msg)

    if response.headers.get("X-No-Log") != "True":
      entry = models_events.APIAuditEntryFromHttpRequestResponse(
          request, response
      )
      data_store.REL_DB.WriteAPIAuditEntry(entry)

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

    log_msg = "%s-%s [%s]: %s %s %s %s (%d)" % (
        event_id,
        request.source_ip,
        source or "<unknown>",
        request.method,
        request.url,
        request.user_agent,
        request.user,
        message_count or 0,
    )
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
    self.buffer = self.buffer[-self.capacity :]


class RobustSysLogHandler(handlers.SysLogHandler):
  """A handler which does not raise if it fails to connect."""

  def __init__(self, *args, **kwargs):
    self.formatter = None
    try:
      super().__init__(*args, **kwargs)
    except socket.error:
      pass

  def handleError(self, record):
    """Just ignore socket errors - the syslog server might come back."""


class ErrorLogsHandler(logging.Handler):
  """Logging Handler that exposes error log count in metrics."""

  def __init__(self, *args, **kwargs):
    """Initializes LogMetricsHandler."""
    super().__init__(*args, **kwargs)

    self.setLevel(logging.ERROR)

  def emit(self, record: logging.LogRecord):
    """Overrides Handler.emit()."""
    # From https://docs.python.org/3/library/logging.html#logging.Logger
    # logging.error() and logging.exception() log with level ERROR.
    # logging.critical() logs with level CRITICAL.
    if record.levelno == logging.ERROR:
      LOG_CALLS_COUNTER.Increment(fields=["ERROR"])
    elif record.levelno == logging.CRITICAL:
      LOG_CALLS_COUNTER.Increment(fields=["CRITICAL"])


def InitErrorLogsMonitoring():
  """Sets up error logs monitoring."""
  logging.root.addHandler(ErrorLogsHandler())
  logging.info("Initialized ErrorLogsHandler.")


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
  """Initializes logging levels."""
  logger = logging.getLogger()

  if config.CONFIG["Logging.verbose"] or _VERBOSE.value:
    logging.root.setLevel(logging.DEBUG)
    levels = VERBOSE_LOG_LEVELS
  else:
    levels = BASE_LOG_LEVELS

  logging.info("Root logging level set to %s", logging.root.level)

  for handler in logger.handlers:
    handler.setLevel(levels[handler.__class__.__name__])
    logging.info("Logging handler %s level set to %s", handler, handler.level)

LOG_FORMAT = (
    "%(levelname)s:%(asctime)s %(process)d "
    "%(processName)s %(thread)d %(threadName)s "
    "%(module)s:%(lineno)s] %(message)s"
)


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
        handler = logging.FileHandler(path, mode="a", encoding="utf-8")
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

  # The root logger.
  logger = logging.getLogger()
  memory_handlers = [
      m
      for m in logger.handlers
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
  # `local_log` requires `Logging.path` configuration variable to be set. If it
  # is not, we fallback to normal logging (as specified in the config or flags).
  if local_log and config.CONFIG["Logging.path"]:
    logging.debug("Using local LogInit from %s", local_log)
    local_log.LogInit()
    logging.debug("Using local AppLogInit from %s", local_log)
    LOGGER = local_log.AppLogInit()
  else:
    LogInit()
    LOGGER = AppLogInit()

  InitErrorLogsMonitoring()


def SetTestVerbosity():
  if local_log:
    local_log.SetTestVerbosity()
    return

  # Test logging. This is only to stderr, adjust the levels according to flags
  if _VERBOSE.value:
    logging.root.setLevel(logging.DEBUG)
  else:
    logging.root.setLevel(logging.WARN)


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
