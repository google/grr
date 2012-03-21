#!/usr/bin/env python

# Copyright 2011 Google Inc.
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


"""Client utilities common to all platforms."""



import hashlib
import logging
import platform
import subprocess
import threading
import time


from M2Crypto import BIO
from M2Crypto import RSA

from grr.client import client_config
from grr.client import conf
from grr.lib import utils


FLAGS = conf.PARSER.flags


def HandleAlarm(process):
  try:
    process.kill()
  # There is a race condition here where the process terminates
  # just before it would be killed. We ignore the exception
  # in that case as the process is already gone.
  except OSError:
    pass


class Alarm (threading.Thread):
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


def Execute(cmd, args, time_limit=-1):
  """Executes commands on the client.

  This function is the only place where commands will be executed
  by the GRR client. This makes sure that all issued commands are compared to a
  white list and no malicious commands are issued on the client machine.

  Args:
    cmd: The command to be executed.
    args: List of arguments.
    time_limit: Time in seconds the process is allowed to run.

  Returns:
    A tuple of stdout, stderr and return value.
  """

  # Those whitelists could also go in the platform specific client files
  # client_utils_<platform>.py. We chose to leave the here to discourage adding
  # new commands to them which would be trivial if they were global arrays.
  if platform.system() == "Windows":
    whitelist = [
        ]
  elif platform.system() == "Linux":
    whitelist = [
        ("/bin/sleep", ["10"]),
        ("/bin/echo", ["1"]),
        ]
  elif platform.system() == "Darwin":
    whitelist = [
        ("/bin/launchctl", ["unload", client_config.LAUNCHCTL_PLIST]),
        ("/bin/echo", ["1"]),
        ]
  else:
    whitelist = []

  for (allowed_cmd, allowed_args) in whitelist:
    if cmd == allowed_cmd and args == allowed_args:
      run = [cmd]
      run.extend(args)
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

  # Whitelist doesn't contain this cmd/arg pair
  logging.info("Execution disallowed by whitelist: %s %s.", cmd, " ".join(args))
  return ("", "Execution disallowed by whitelist.", -1, -1)


LOG_THROTTLE_CACHE = utils.TimeBasedCache(max_size=10, max_age=60*60)


def ErrorOnceAnHour(msg, *args, **kwargs):
  """Logging helper function mirroring logging but reduces spam. Read notes.

  Args:
    msg: The message.

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


def VerifySignedDriver(driver_pb, pub_key=None, verify_data=True):
  """Verifies a key, returns True or False.

  Args:
    driver_pb: A SignedDriver protobuf.
    pub_key: Pub key in PEM format we are verifying against. Defaults to the
        one stored in client_config.DRIVER_SIGNING_KEY.
    verify_data: If set to false, the reported digest is checked not the actual
        data. This is useful to disable for uninstalls where we want to remove
        a driver but don't want to send the full binary content.

  Returns:
    True if verification succeeded.
  """
  if pub_key is None:
    try:
      pub_key = client_config.DRIVER_SIGNING_KEY.get(FLAGS.camode.upper())
    except KeyError:
      logging.error("Cannot verify driver due to invalid mode for signing key.")
      return False
  bio = BIO.MemoryBuffer(pub_key)
  rsa = RSA.load_pub_key_bio(bio)
  result = 0
  try:
    result = rsa.verify(driver_pb.digest, driver_pb.signature, "sha256")
  except RSA.RSAError:
    logging.warn("Could not verify driver.")
    return False
  if verify_data:
    digest = hashlib.sha256(driver_pb.data).digest()
    if digest != driver_pb.digest:
      logging.warn("Driver digest sent in proto did not match actual data.")
      return False
  return result == 1
