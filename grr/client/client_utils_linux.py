#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

"""Linux specific utils."""


import locale
import os
import subprocess
import sys
import threading
import time

from google.protobuf import message
import logging

from grr.lib import config_lib
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import paths as rdf_paths


# TODO(user): Find a reliable way to do this for Linux.
def LinFindProxies():
  return []

MOUNTPOINT_CACHE = [0, None]


def GetMountpoints(data=None):
  """List all the filesystems mounted on the system."""
  expiry = 60  # 1 min

  insert_time = MOUNTPOINT_CACHE[0]
  if insert_time + expiry > time.time():
    return MOUNTPOINT_CACHE[1]

  devices = {}

  # Check all the mounted filesystems.
  if data is None:
    data = "\n".join([open(x).read() for x in ["/proc/mounts", "/etc/mtab"]])

  for line in data.splitlines():
    try:
      device, mnt_point, fs_type, _ = line.split(" ", 3)
      mnt_point = os.path.normpath(mnt_point)

      # What if several devices are mounted on the same mount point?
      devices[mnt_point] = (device, fs_type)
    except ValueError:
      pass

  MOUNTPOINT_CACHE[0] = time.time()
  MOUNTPOINT_CACHE[1] = devices

  return devices


def LinGetRawDevice(path):
  """Resolve the raw device that contains the path."""
  device_map = GetMountpoints()

  path = utils.SmartUnicode(path)
  mount_point = path = utils.NormalizePath(path, "/")

  result = rdf_paths.PathSpec(pathtype=rdf_paths.PathSpec.PathType.OS)

  # Assign the most specific mount point to the result
  while mount_point:
    try:
      result.path, fs_type = device_map[mount_point]
      if fs_type in ["ext2", "ext3", "ext4", "vfat", "ntfs"]:
        # These are read filesystems
        result.pathtype = rdf_paths.PathSpec.PathType.OS
      else:
        result.pathtype = rdf_paths.PathSpec.PathType.UNSET

      # Drop the mount point
      path = utils.NormalizePath(path[len(mount_point):])
      result.mount_point = mount_point

      return result, path
    except KeyError:
      mount_point = os.path.dirname(mount_point)


def CanonicalPathToLocalPath(path):
  """Linux uses a normal path.

  If sys.getfilesystemencoding() returns None normally any call to
  a system function will try to encode the string to ASCII.
  A modern version of Linux will use UTF-8 as (narrow) string encoding.
  locale.getpreferredencoding() seems to return ASCII at this point.
  So for older versions of Linux we'll need to rely on
  locale.getdefaultlocale()[1]. If everything fails we fallback to UTF-8.

  Args:
    path: the canonical path as an Unicode string

  Returns:
    a unicode string or an encoded (narrow) string dependent on
    system settings
  """
  canonical_path = utils.NormalizePath(path)

  if sys.getfilesystemencoding():
    return canonical_path

  encoding = locale.getdefaultlocale()[1] or "UTF-8"
  return canonical_path.encode(encoding)


def LocalPathToCanonicalPath(path):
  """Linux uses a normal path."""
  return utils.NormalizePath(path)


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

    """
    time.sleep(seconds - int(seconds))
    for _ in range(int(seconds)):
      time.sleep(1)

  def Stop(self):
    """Exits the main thread."""
    self.running = False
    self.WriteNannyStatus("Nanny stopping.")

  def Heartbeat(self):
    self.last_heart_beat_time = time.time()

  def WriteNannyStatus(self, status):
    try:
      with open(config_lib.CONFIG["Nanny.statusfile"], "w") as fd:
        fd.write(status)
    except (IOError, OSError):
      pass


class NannyController(object):
  """Controls communication with the nanny."""

  # Nanny should be a global singleton thread.
  nanny = None

  max_log_size = 100000000

  def StartNanny(self, unresponsive_kill_period=None, nanny_logfile=None):
    # The nanny thread is a singleton.
    if NannyController.nanny is None:
      if unresponsive_kill_period is None:
        unresponsive_kill_period = config_lib.CONFIG[
            "Nanny.unresponsive_kill_period"]

      NannyController.nanny_logfile = (nanny_logfile or
                                       config_lib.CONFIG["Nanny.logfile"])
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

  def WriteTransactionLog(self, grr_message):
    """Write the message into the transaction log."""
    try:
      grr_message = grr_message.SerializeToString()
    except AttributeError:
      grr_message = str(grr_message)

    try:
      with open(self.nanny_logfile, "w") as fd:
        fd.write(grr_message)
    except (IOError, OSError):
      pass

  def SyncTransactionLog(self):
    # Not implemented on Linux.
    pass

  def CleanTransactionLog(self):
    """Wipes the transaction log."""
    try:
      with open(self.nanny_logfile, "w") as fd:
        fd.write("")
    except (IOError, OSError):
      pass

  def GetTransactionLog(self):
    """Return a GrrMessage instance from the transaction log or None."""
    try:
      with open(self.nanny_logfile, "r") as fd:
        data = fd.read(self.max_log_size)
    except (IOError, OSError):
      return

    try:
      if data:
        return rdf_flows.GrrMessage(data)
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
      with open(config_lib.CONFIG["Nanny.statusfile"], "r") as fd:
        return fd.read(self.max_log_size)
    except (IOError, OSError):
      return None


def InstallDriver(driver_path):
  """Loads a driver and starts it."""

  cmd = ["/sbin/insmod", driver_path]

  p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  p.communicate()
  exit_status = p.returncode
  logging.info("Loading driver finished, status: %d.", exit_status)
  if exit_status != 0:
    raise OSError("Failed to load driver, may already be installed.")


def UninstallDriver(driver_name):
  """Unloads the driver.

  Args:
    driver_name: Name of the driver.

  Raises:
    OSError: On failure to uninstall.
  """
  cmd = ["/sbin/rmmod", driver_name]

  p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  p.communicate()
  exit_status = p.returncode
  logging.info("Unloading driver finished, status: %d.", exit_status)
  if exit_status != 0:
    raise OSError("Failed to unload driver.")


def KeepAlive():
  # Not yet supported for Linux.
  pass
