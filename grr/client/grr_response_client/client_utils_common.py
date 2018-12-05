#!/usr/bin/env python
"""Client utilities common to all platforms."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import hashlib
import logging
import os
import platform
import subprocess
import threading
import time


from future.utils import itervalues

from grr_response_client.local import binary_whitelist
from grr_response_core import config
from grr_response_core.lib import constants
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto


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
            use_client_context=False,
            cwd=None):
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
    cwd: Current working directory for the command.

  Returns:
    A tuple of stdout, stderr, return value and time taken.
  """
  if not bypass_whitelist and not IsExecutionWhitelisted(cmd, args):
    # Whitelist doesn't contain this cmd/arg pair
    logging.info("Execution disallowed by whitelist: %s %s.", cmd,
                 " ".join(args))
    return (b"", b"Execution disallowed by whitelist.", -1, -1)

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
      _Execute(
          cmd, args, time_limit, use_client_context=use_client_context, cwd=cwd)
      os._exit(0)  # pylint: disable=protected-access
  else:
    return _Execute(
        cmd, args, time_limit, use_client_context=use_client_context, cwd=cwd)


def _Execute(cmd, args, time_limit=-1, use_client_context=False, cwd=None):
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
  p = subprocess.Popen(
      run,
      stdin=subprocess.PIPE,
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
      env=env,
      cwd=cwd)

  alarm = None
  if time_limit > 0:
    alarm = threading.Timer(time_limit, HandleAlarm, (p,))
    alarm.setDaemon(True)
    alarm.start()

  stdout, stderr, exit_status = b"", b"", -1
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
      alarm.join()

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
  A deployment-specific list is also checked (see local/binary_whitelist.py).
  """
  if platform.system() == "Windows":
    whitelist = [
        ("arp.exe", ["-a"]),
        ("driverquery.exe", ["/v"]),
        ("ipconfig.exe", ["/all"]),
        ("netsh.exe", ["advfirewall", "firewall", "show", "rule", "name=all"]),
        ("netsh.exe",
         ["advfirewall", "monitor", "show", "firewall", "rule", "name=all"]),
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
        ("/usr/sbin/arp", ["-a"]),
        ("/usr/sbin/dmidecode", ["-q"]),
        ("/usr/sbin/sshd", ["-T"]),
    ]
  elif platform.system() == "Darwin":
    whitelist = [
        ("/bin/echo", ["1"]),
        ("/bin/launchctl", ["unload", config.CONFIG["Client.plist_path"]]),
        ("/usr/bin/hdiutil", ["info"]),
        ("/usr/bin/last", []),
        ("/usr/bin/who", []),
        ("/usr/sbin/arp", ["-a"]),
        ("/usr/sbin/kextstat", []),
        ("/usr/sbin/system_profiler", ["-xml", "SPHardwareDataType"]),
        ("/usr/libexec/firmwarecheckers/ethcheck/ethcheck", ["--show-hashes"]),
    ]
  else:
    whitelist = []

  for (allowed_cmd, allowed_args) in whitelist:
    if cmd == allowed_cmd and args == allowed_args:
      return True

  # Check if this is whitelisted locally.
  if binary_whitelist.IsExecutionWhitelisted(cmd, args):
    return True

  return False


class MultiHasher(object):
  """An utility class that is able to applies multiple hash algorithms.

  Objects that need to construct `Hash` object with multiple hash values need
  to apply multiple hash algorithms to the given data. This class removes some
  boilerplate associated with it and provides a readable API similar to the one
  exposed by Python's `hashlib` module.

  Args:
    algorithms: List of names of the algorithms from the `hashlib` module that
      need to be applied.
    progress: An (optional) progress callback called when hashing functions are
      applied to the data.
  """

  def __init__(self, algorithms=None, progress=None):
    if not algorithms:
      algorithms = ["md5", "sha1", "sha256"]

    self._hashers = {}
    for algorithm in algorithms:
      self._hashers[algorithm] = hashlib.new(algorithm)
    self._bytes_read = 0

    self._progress = progress

  def HashFilePath(self, path, byte_count):
    """Updates underlying hashers with file on a given path.

    Args:
      path: A path to the file that is going to be fed to the hashers.
      byte_count: A maximum numbers of bytes that are going to be processed.
    """
    with open(path, "rb") as fd:
      self.HashFile(fd, byte_count)

  def HashFile(self, fd, byte_count):
    """Updates underlying hashers with a given file.

    Args:
      fd: A file object that is going to be fed to the hashers.
      byte_count: A maximum number of bytes that are going to be processed.
    """
    while byte_count > 0:
      buf_size = min(byte_count, constants.CLIENT_MAX_BUFFER_SIZE)
      buf = fd.read(buf_size)
      if not buf:
        break

      self.HashBuffer(buf)
      byte_count -= buf_size

  def HashBuffer(self, buf):
    """Updates underlying hashers with a given buffer.

    Args:
      buf: A byte buffer (string object) that is going to be fed to the hashers.
    """
    for hasher in itervalues(self._hashers):
      hasher.update(buf)
      if self._progress:
        self._progress()

    self._bytes_read += len(buf)

  def GetHashObject(self):
    """Returns a `Hash` object with appropriate fields filled-in."""
    hash_object = rdf_crypto.Hash()
    hash_object.num_bytes = self._bytes_read
    for algorithm in self._hashers:
      setattr(hash_object, algorithm, self._hashers[algorithm].digest())
    return hash_object
