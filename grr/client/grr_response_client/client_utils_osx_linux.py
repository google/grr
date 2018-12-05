#!/usr/bin/env python
"""Utils common to macOS and Linux."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
import os
import threading
import time

from builtins import range  # pylint: disable=redefined-builtin
import psutil
import xattr

from google.protobuf import message

from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import flows as rdf_flows


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


def GetExtAttrs(filepath):
  """Fetches extended file attributes.

  Args:
    filepath: A path to the file.

  Yields:
    `ExtAttr` pairs.
  """
  path = CanonicalPathToLocalPath(filepath)

  try:
    attr_names = xattr.listxattr(path)
  except (IOError, OSError, UnicodeDecodeError) as error:
    msg = "Failed to retrieve extended attributes for '%s': %s"
    logging.error(msg, path, error)
    return

  # `xattr` (version 0.9.2) decodes names as UTF-8. Since we (and the system)
  # allows for names and values to be arbitrary byte strings, we use `bytes`
  # rather than `unicode` objects here. Therefore we have to re-encode what
  # `xattr` has decoded. Additionally, because the decoding that `xattr` does
  # may fail, we additionally guard against such exceptions.
  def EncodeUtf8(attr_name):
    if isinstance(attr_name, unicode):
      return attr_name.encode("utf-8")
    if isinstance(attr_name, bytes):
      return attr_name
    raise TypeError("Unexpected type `%s`" % type(attr_name))

  for attr_name in attr_names:
    attr_name = EncodeUtf8(attr_name)
    try:
      attr_value = xattr.getxattr(path, attr_name)
    except (IOError, OSError) as error:
      msg = "Failed to retrieve attribute '%s' for '%s': %s"
      logging.error(msg, attr_name, path, error)
      continue

    yield rdf_client_fs.ExtAttr(name=attr_name, value=attr_value)


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
    for _ in range(int(seconds)):
      time.sleep(1)
      # Check that we do not exceeded our memory allowance.
      if self.GetMemoryUsage() > self.memory_quota:
        raise MemoryError("Exceeded memory allowance.")
      if not self.running:
        break

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
  max_log_size = 100000000

  def StartNanny(self, unresponsive_kill_period=None):
    # The nanny thread is a singleton.
    if NannyController.nanny is None:
      if unresponsive_kill_period is None:
        unresponsive_kill_period = config.CONFIG[
            "Nanny.unresponsive_kill_period"]

      NannyController.nanny = NannyThread(unresponsive_kill_period)
      NannyController.nanny.start()

  def StopNanny(self):
    if NannyController.nanny:
      NannyController.nanny.Stop()
      NannyController.nanny.join()
      NannyController.nanny = None

  def Heartbeat(self):
    """Notifies the nanny of a heartbeat."""
    if self.nanny:
      self.nanny.Heartbeat()

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


class TransactionLog(object):
  """A class to manage a transaction log for client processing."""

  max_log_size = 100000000

  def __init__(self, logfile=None):
    self.logfile = logfile or config.CONFIG["Client.transaction_log_file"]

  def Write(self, grr_message):
    """Write the message into the transaction log."""
    grr_message = grr_message.SerializeToString()

    try:
      with open(self.logfile, "wb") as fd:
        fd.write(grr_message)
    except (IOError, OSError):
      # Check if we're missing directories and try to create them.
      if not os.path.isdir(os.path.dirname(self.logfile)):
        try:
          os.makedirs(os.path.dirname(self.logfile))
          with open(self.logfile, "wb") as fd:
            fd.write(grr_message)
        except (IOError, OSError):
          logging.exception("Couldn't write nanny transaction log to %s",
                            self.logfile)

  def Sync(self):
    # Not implemented on Linux.
    pass

  def Clear(self):
    """Wipes the transaction log."""
    try:
      with open(self.logfile, "wb") as fd:
        fd.write("")
    except (IOError, OSError):
      pass

  def Get(self):
    """Return a GrrMessage instance from the transaction log or None."""
    try:
      with open(self.logfile, "rb") as fd:
        data = fd.read(self.max_log_size)
    except (IOError, OSError):
      return

    try:
      if data:
        return rdf_flows.GrrMessage.FromSerializedString(data)
    except (message.Error, rdfvalue.Error):
      return
