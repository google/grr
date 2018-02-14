#!/usr/bin/env python
"""Utils common to macOS and Linux."""

import logging
import os
import threading
import time

import psutil
import xattr

from google.protobuf import message

from grr import config
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import flows as rdf_flows


def VerifyFileOwner(filename):
  stat_info = os.lstat(filename)
  return os.getuid() == stat_info.st_uid


def CanonicalPathToLocalPath(path):
  """Linux uses a normal path.

  We always want to encode as UTF-8 here. If the environment for the
  client is broken, Python might assume an ASCII based filesystem
  (those should be rare nowadays) and things will go wrong if we let
  Python decide what to do. If the filesystem actually is ASCII,
  encoding and decoding will not change anything so things will still
  work as expected.

  Args:
    path: the canonical path as an Unicode string

  Returns:
    a unicode string or an encoded (narrow) string dependent on
    system settings

  """
  return utils.SmartStr(utils.NormalizePath(path))


def LocalPathToCanonicalPath(path):
  """Linux uses a normal path."""
  return utils.NormalizePath(path)


def AddStatEntryExtAttrs(stat_entry):
  """Fills `ext_attrs` field of the `StatEntry` object.

  Args:
    stat_entry: A `StatEntry` object to fill-in.
  """
  path = CanonicalPathToLocalPath(stat_entry.pathspec.path)

  for attr_name in xattr.listxattr(path):
    attr_value = xattr.getxattr(path, attr_name)

    attr = rdf_client.ExtAttr(name=attr_name, value=attr_value)
    stat_entry.ext_attrs.append(attr)


class NannyThread(threading.Thread):
  """This is the thread which watches the nanny running."""

  def __init__(self, unresponsive_kill_period):
    """Constructor.

    Args:
      unresponsive_kill_period: The time in seconds which we wait for a
      heartbeat.
    """
    super(NannyThread, self).__init__(name="Nanny")
    self.last_heart_beat_time = time.time()
    self.unresponsive_kill_period = unresponsive_kill_period
    self.running = True
    self.daemon = True
    self.proc = psutil.Process()
    self.memory_quota = config.CONFIG["Client.rss_max_hard"] * 1024 * 1024

  def run(self):
    self.WriteNannyStatus("Nanny running.")
    while self.running:
      now = time.time()

      # When should we check the next heartbeat?
      check_time = self.last_heart_beat_time + self.unresponsive_kill_period

      # Missed the deadline, we need to die.
      if check_time < now:
        msg = "Suicide by nanny thread."
        logging.error(msg)
        self.WriteNannyStatus(msg)

        # Die hard here to prevent hangs due to non daemonized threads.
        os._exit(-1)  # pylint: disable=protected-access
      else:
        # Sleep until the next heartbeat is due.
        self.Sleep(check_time - now)

  def Sleep(self, seconds):
    """Sleep a given time in 1 second intervals.

    When a machine is suspended during a time.sleep(n) call for more
    than n seconds, sometimes the sleep is interrupted and all threads
    wake up at the same time. This leads to race conditions between
    the threads issuing the heartbeat and the one checking for it. By
    sleeping in small intervals, we make sure that even if one sleep
    call is interrupted, we do not check for the heartbeat too early.

    Args:
      seconds: Number of seconds to sleep.

    Raises:
      MemoryError: if the process exceeds memory quota.
    """
    time.sleep(seconds - int(seconds))
    for _ in xrange(int(seconds)):
      time.sleep(1)
      # Check that we do not exceeded our memory allowance.
      if self.GetMemoryUsage() > self.memory_quota:
        raise MemoryError("Exceeded memory allowance.")

  def Stop(self):
    """Exits the main thread."""
    self.running = False
    self.WriteNannyStatus("Nanny stopping.")

  def GetMemoryUsage(self):
    return self.proc.memory_info().rss

  def Heartbeat(self):
    self.last_heart_beat_time = time.time()

  def WriteNannyStatus(self, status):
    try:
      with open(config.CONFIG["Nanny.statusfile"], "wb") as fd:
        fd.write(status)
    except (IOError, OSError):
      pass


class NannyController(object):
  """Controls communication with the nanny."""

  # Nanny should be a global singleton thread.
  nanny = None
  nanny_logfile = None
  max_log_size = 100000000

  def StartNanny(self, unresponsive_kill_period=None, nanny_logfile=None):
    # The nanny thread is a singleton.
    if NannyController.nanny is None:
      if unresponsive_kill_period is None:
        unresponsive_kill_period = config.CONFIG[
            "Nanny.unresponsive_kill_period"]

      NannyController.nanny_logfile = nanny_logfile
      NannyController.nanny = NannyThread(unresponsive_kill_period)
      NannyController.nanny.start()

  def StopNanny(self):
    if NannyController.nanny:
      NannyController.nanny.Stop()
      NannyController.nanny = None

  def Heartbeat(self):
    """Notifies the nanny of a heartbeat."""
    if self.nanny:
      self.nanny.Heartbeat()

  def _GetLogFilename(self):
    return self.nanny_logfile or config.CONFIG["Nanny.logfile"]

  def WriteTransactionLog(self, grr_message):
    """Write the message into the transaction log."""
    grr_message = grr_message.SerializeToString()

    logfile = self._GetLogFilename()

    try:
      with open(logfile, "wb") as fd:
        fd.write(grr_message)
    except (IOError, OSError):
      # Check if we're missing directories and try to create them.
      if not os.path.isdir(os.path.dirname(logfile)):
        try:
          os.makedirs(os.path.dirname(logfile))
          with open(logfile, "wb") as fd:
            fd.write(grr_message)
        except (IOError, OSError):
          logging.exception("Couldn't write nanny transaction log to %s",
                            logfile)

  def SyncTransactionLog(self):
    # Not implemented on Linux.
    pass

  def CleanTransactionLog(self):
    """Wipes the transaction log."""
    try:
      with open(self._GetLogFilename(), "wb") as fd:
        fd.write("")
    except (IOError, OSError):
      pass

  def GetTransactionLog(self):
    """Return a GrrMessage instance from the transaction log or None."""
    try:
      with open(self._GetLogFilename(), "rb") as fd:
        data = fd.read(self.max_log_size)
    except (IOError, OSError):
      return

    try:
      if data:
        return rdf_flows.GrrMessage.FromSerializedString(data)
    except (message.Error, rdfvalue.Error):
      return

  def GetNannyMessage(self):
    # Not implemented on Linux.
    return None

  def ClearNannyMessage(self):
    # Not implemented on Linux.
    pass

  def GetNannyStatus(self):
    try:
      with open(config.CONFIG["Nanny.statusfile"], "rb") as fd:
        return fd.read(self.max_log_size)
    except (IOError, OSError):
      return None
