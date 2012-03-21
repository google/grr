#!/usr/bin/env python

# Copyright 2010 Google Inc.
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

"""This is the GRR windows client."""


# Usage:
# win32api.exe install
# win32api.exe start
# win32api.exe stop
# win32api.exe remove

import logging
from logging.handlers import NTEventLogHandler

import multiprocessing
import os
import sys
import time
import urllib2
import servicemanager
import win32event
import win32evtlogutil
import win32service
import win32serviceutil
import winerror


from grr.client import conf as flags

from grr.client import client
from grr.client import client_config
from grr.client import client_utils
from grr.client import comms
from grr.client import conf
from grr.lib import registry


# Those args are set by Windows when GRR is started as a service. We
# just ignore them.
for flag in ["password", "username", "startup", "perfmonini", "perfmondll",
             "interactive"]:
  flags.DEFINE_string(flag, "", "")

FLAGS = client.FLAGS


class GRRMonitor(win32serviceutil.ServiceFramework):
  """The GRR Monitoring service."""
  _svc_name_ = client_config.SERVICE_NAME
  _svc_display_name_ = client_config.SERVICE_DISPLAY_NAME
  _svc_deps_ = ["EventLog"]

  def __init__(self, args):
    logging.debug("FLAGS are %s", FLAGS)
    proxies = client_utils.FindProxies()

    # For now we just set the first one in the environment - in future
    # we should test to see if it actually works.
    if proxies:
      os.environ["http_proxy"] = proxies[0]

    win32serviceutil.ServiceFramework.__init__(self, args)
    self.wait_event = win32event.CreateEvent(None, 0, 0, None)
    self.active = True

    win32evtlogutil.AddSourceToRegistry(self._svc_name_)

    ca_cert = client_config.CACERTS.get(FLAGS.camode.upper())
    if not ca_cert:
      raise RuntimeError("Invalid camode specified.")

    if FLAGS.process_separate:
      self.context = comms.ProcessSeparatedContext(ca_cert=ca_cert)
    else:
      self.context = comms.GRRHTTPContext(ca_cert=ca_cert)

    self.context.LoadCertificates()

    # Start off with a maximum poling interval
    self.sleep_time = FLAGS.poll_max

  def SvcStop(self):
    """This method will be called when the service is required to stop."""
    self.active = False

    # tell Service Manager we are trying to stop (required)
    self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
    logging.debug("Stopping")

    # set the event to call
    waitstop = win32event.CreateEvent(None, 0, 0, None)
    win32event.SetEvent(waitstop)

  def _Sleep(self, timeout):
    """A helper function which can sleep for a long time.

    We can interactively stop the service during the sleep by raising
    StopIteration.

    Args:
      timeout: A time to sleep in sec.

    Raises:
      StopIteration if the service is stopped during the sleep.
    """
    start = time.time()
    while self.active:
      now = time.time()
      if now > start + timeout:
        return

      # Wait for one sec
      win32event.WaitForSingleObject(self.wait_event, 1000)

    raise StopIteration()

  def SvcDoRun(self):
    """This method will be called when the service starts."""
    logging.debug("Will use proxies %s", urllib2.getproxies())

    logging.info("Starting")

    registry.Init()

    logging.debug("Starting mainloop")
    for status in self.context.Run():
      if not self.active: break

      # If we communicated this time we want to continue aggressively
      if status.sent_count > 0 or status.received_count > 0:
        self.sleep_time = 0

      logging.debug("Sending %s, Received %s messages. Sleeping for %s",
                    status.sent_count, status.received_count, self.sleep_time)
      try:
        self._Sleep(self.sleep_time)
      except StopIteration:
        break

      # Back off slowly at first and fast if no answer.
      self.sleep_time = min(
          FLAGS.poll_max,
          max(FLAGS.poll_min, self.sleep_time) * FLAGS.poll_slew)

    logging.info("Stopping service")


def SetupLogging(logger):
  """Configure logging for the service."""
  log_level = logging.INFO
  if FLAGS.verbose: log_level = logging.DEBUG
  logger.setLevel(log_level)

  formatter = logging.Formatter("%(asctime)s %(levelname)s %(module)s"
                                ":%(lineno)d] %(message)s")

  # If debug enabled, add debug file logging.
  if FLAGS.verbose:
    try:
      # Create the directory if it doesn't exist.
      if not os.path.isdir(os.path.dirname(client_config.LOGFILE_PATH)):
        os.makedirs(os.path.dirname(client_config.LOGFILE_PATH))

      filehandler = logging.FileHandler(client_config.LOGFILE_PATH, mode="ab")
      filehandler.setLevel(logging.DEBUG)
      filehandler.setFormatter(formatter)
      logger.addHandler(filehandler)
    except OSError:
      pass

  # Add Windows Event logging for anything WARN or above.
  evt_log_level = logging.WARN
  if FLAGS.verbose: evt_log_level = logging.INFO
  evt_handler = NTEventLogHandler(client_config.SERVICE_NAME)
  evt_handler.setLevel(evt_log_level)
  logger.addHandler(evt_handler)

  # Used when running in debug mode e.g. grrservice.exe debug
  stream_handler = logging.StreamHandler()
  stream_handler.setFormatter(formatter)
  logger.addHandler(stream_handler)


def main():
  """Main function."""
  conf.RUNNING_AS_SERVICE = True

  if len(sys.argv) == 1:
    try:
      evtsrc_dll = os.path.abspath(servicemanager.__file__)
      servicemanager.PrepareToHostSingle(GRRMonitor)
      servicemanager.Initialize(client_config.SERVICE_NAME, evtsrc_dll)
      servicemanager.StartServiceCtrlDispatcher()
    except win32service.error, details:
      print details

      if details[0] == winerror.ERROR_FAILED_SERVICE_CONTROLLER_CONNECT:
        win32serviceutil.usage()
  else:
    win32serviceutil.HandleCommandLine(GRRMonitor)


if __name__ == "__main__":
  multiprocessing.freeze_support()
  conf.PARSER.parse_args()
  SetupLogging(logging.getLogger())
  main()
