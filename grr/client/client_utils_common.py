#!/usr/bin/env python
"""Client utilities common to all platforms."""



import os
import platform
import subprocess
import threading
import time


import logging

from grr.lib import config_lib
from grr.lib import utils


def HandleAlarm(process):
  try:
    logging.info("Killing child process due to timeout")
    process.kill()
  # There is a race condition here where the process terminates
  # just before it would be killed. We ignore the exception
  # in that case as the process is already gone.
  except OSError:
    pass


def Execute(cmd,
            args,
            time_limit=-1,
            bypass_whitelist=False,
            daemon=False,
            use_client_context=False):
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
    daemon: Start the new process in the background.
    use_client_context: Run this script in the client's context. Defaults to
                        system context.

  Returns:
    A tuple of stdout, stderr, return value and time taken.
  """
  if not bypass_whitelist and not IsExecutionWhitelisted(cmd, args):
    # Whitelist doesn't contain this cmd/arg pair
    logging.info("Execution disallowed by whitelist: %s %s.", cmd,
                 " ".join(args))
    return ("", "Execution disallowed by whitelist.", -1, -1)

  if daemon:
    pid = os.fork()
    if pid == 0:
      # This is the child, it will run the daemon process. We call os.setsid
      # here to become the session leader of this new session and the process
      # group leader of the new process group so we don't get killed when the
      # main process exits.
      try:
        os.setsid()
      except OSError:
        # This only works if the process is running as root.
        pass
      _Execute(cmd, args, time_limit, use_client_context=use_client_context)
      os._exit(0)  # pylint: disable=protected-access
  else:
    return _Execute(cmd,
                    args,
                    time_limit,
                    use_client_context=use_client_context)


def _Execute(cmd, args, time_limit=-1, use_client_context=False):
  """Executes cmd."""
  run = [cmd]
  run.extend(args)
  env = os.environ.copy()
  if use_client_context:
    env.pop("LD_LIBRARY_PATH", None)
    env.pop("PYTHON_PATH", None)
    context = "client"
  else:
    context = "system"
  logging.info("Executing %s in %s context.", " ".join(run), context)
  p = subprocess.Popen(run,
                       stdin=subprocess.PIPE,
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE,
                       env=env)

  alarm = None
  if time_limit > 0:
    alarm = threading.Timer(time_limit, HandleAlarm, (p,))
    alarm.setDaemon(True)
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
      alarm.cancel()

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
    whitelist = [
        ("driverquery.exe", ["/v"]),
        ("ipconfig.exe", ["/all"]),
        ("tasklist.exe", ["/SVC"]),
        ("tasklist.exe", ["/v"]),
    ]
  elif platform.system() == "Linux":
    whitelist = [
        ("/bin/df", []),
        ("/bin/echo", ["1"]),
        ("/bin/rpm", ["-qa"]),
        ("/bin/sleep", ["10"]),
        ("/sbin/auditctl", ["-l"]),
        ("/sbin/ifconfig", ["-a"]),
        ("/sbin/iptables", ["-L", "-n", "-v"]),
        ("/sbin/lsmod", []),
        ("/usr/bin/dpkg", ["--list"]),
        ("/usr/bin/last", []),
        ("/usr/bin/yum", ["list", "installed", "-q"]),
        ("/usr/bin/yum", ["repolist", "-v", "-q"]),
        ("/usr/bin/who", []),
        ("/usr/sbin/dmidecode", ["-q"]),
        ("/usr/sbin/sshd", ["-T"]),
    ]
  elif platform.system() == "Darwin":
    whitelist = [
        ("/bin/echo", ["1"]),
        ("/bin/launchctl", ["unload", config_lib.CONFIG["Client.plist_path"]]),
        ("/usr/bin/hdiutil", ["info"]),
        ("/usr/bin/last", []),
        ("/usr/bin/who", []),
        ("/usr/sbin/kextstat", []),
        ("/usr/sbin/system_profiler", ["-xml", "SPHardwareDataType"]),
    ]
  else:
    whitelist = []

  for (allowed_cmd, allowed_args) in whitelist:
    if cmd == allowed_cmd and args == allowed_args:
      return True

  return False


LOG_THROTTLE_CACHE = utils.TimeBasedCache(max_size=10, max_age=60 * 60)


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
