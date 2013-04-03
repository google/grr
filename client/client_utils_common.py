#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.

"""Client utilities common to all platforms."""



import platform
import subprocess
import threading
import time


import logging

from grr.lib import config_lib
from grr.lib import utils


# TODO(user): This should be moved into the osx only files.
config_lib.DEFINE_string("Client.launchctl_plist",
                         "/Library/LaunchDaemons/com.google.code.grrd.plist",
                         "Location of our launchctl plist.")

config_lib.DEFINE_list(
    name="Client.proxy_servers",
    help="List of valid proxy servers the client should try.",
    default=[])


def HandleAlarm(process):
  try:
    logging.info("Killing child process due to timeout")
    process.kill()
  # There is a race condition here where the process terminates
  # just before it would be killed. We ignore the exception
  # in that case as the process is already gone.
  except OSError:
    pass


class Alarm(threading.Thread):
  """A simple timeout to stop subprocess execution."""

  def __init__(self, timeout, callback, args=()):
    threading.Thread.__init__(self)
    self.timeout = timeout
    self.setDaemon(True)
    self.callback = callback
    self.args = args
    self.enabled = True

  def Disable(self):
    self.enabled = False

  def run(self):
    time.sleep(self.timeout)
    if self.enabled:
      self.callback(*self.args)


def Execute(cmd, args, time_limit=-1, bypass_whitelist=False):
  """Executes commands on the client.

  This function is the only place where commands will be executed
  by the GRR client. This makes sure that all issued commands are compared to a
  white list and no malicious commands are issued on the client machine.

  Args:
    cmd: The command to be executed.
    args: List of arguments.
    time_limit: Time in seconds the process is allowed to run.
    bypass_whitelist: Allow execution of things that are not in the whitelist.
        Note that this should only ever be called on a binary that passes the
        VerifySignedBlob check.

  Returns:
    A tuple of stdout, stderr and return value.
  """
  if not IsExecutionWhitelisted(cmd, args) and not bypass_whitelist:
    # Whitelist doesn't contain this cmd/arg pair
    logging.info("Execution disallowed by whitelist: %s %s.", cmd,
                 " ".join(args))
    return ("", "Execution disallowed by whitelist.", -1, -1)

  run = [cmd]
  run.extend(args)
  logging.info("Executing %s", " ".join(run))
  p = subprocess.Popen(run, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

  alarm = None
  if time_limit > 0:
    alarm = Alarm(time_limit, HandleAlarm, (p,))
    alarm.start()

  stdout, stderr, exit_status = "", "", -1
  start_time = time.time()
  try:
    stdout, stderr = p.communicate()
    exit_status = p.returncode
  except IOError:
    # If we end up here, the time limit was exceeded
    pass
  finally:
    if alarm:
      alarm.Disable()

  return (stdout, stderr, exit_status, time.time() - start_time)


def IsExecutionWhitelisted(cmd, args):
  """Check if a binary and args is whitelisted.

  Args:
    cmd: Canonical path to the binary.
    args: List of arguments to be passed to the binary.

  Returns:
    Bool, True if it is whitelisted.

  These whitelists could also go in the platform specific client files
  client_utils_<platform>.py. We chose to leave them here instead of putting
  them in global arrays to discourage people coding other modules from adding
  new commands to the whitelist before running them.
  The idea is to have a single place that lists every command we can run during
  normal operation (obviously doesn't catch the special cases where we bypass
  the list).
  """
  if platform.system() == "Windows":
    whitelist = []
  elif platform.system() == "Linux":
    whitelist = [
        ("/bin/sleep", ["10"]),
        ("/bin/echo", ["1"]),
        ]
  elif platform.system() == "Darwin":
    whitelist = [
        ("/bin/launchctl", ["unload",
                            config_lib.CONFIG["Client.launchctl_plist"]]),
        ("/bin/echo", ["1"]),
        ("/usr/sbin/screencapture", ["-x", "-t", "jpg", "/tmp/ss.dat"]),
        ("/bin/rm", ["-f", "/tmp/ss.dat"])
        ]
  else:
    whitelist = []

  for (allowed_cmd, allowed_args) in whitelist:
    if cmd == allowed_cmd and args == allowed_args:
      return True

  return False


LOG_THROTTLE_CACHE = utils.TimeBasedCache(max_size=10, max_age=60*60)


def ErrorOnceAnHour(msg, *args, **kwargs):
  """Logging helper function mirroring logging but reduces spam. Read notes.

  Args:
    msg: The message.
    *args: Passthrough to logging function.
    **kwargs: Passthrough to logging function.

  Note:
    The same msg will only be logged once per hour. Note that args will be
    ignored so the following will only output one line.
      ThrottledLog(logging.WARN, "oh no %s", "joe")
      ThrottledLog(logging.WARN, "oh no %s", "bob")
  """
  try:
    LOG_THROTTLE_CACHE.Get(msg)
  except KeyError:
    logging.error(msg, *args, **kwargs)
    LOG_THROTTLE_CACHE.Put(msg, msg)
