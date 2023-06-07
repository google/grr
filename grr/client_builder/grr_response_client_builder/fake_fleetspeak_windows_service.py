#!/usr/bin/env python
"""A Windows Service which only logs start/stop events for test cases."""

import subprocess
import sys
from typing import Optional

from absl import app
from absl import flags
import servicemanager
import win32event
import win32service
import win32serviceutil

_COMMAND = flags.DEFINE_string(
    "command",
    "",
    "Command passed directly to win32serviceutil.HandleCommandLine.",
)

_LOGFILE = flags.DEFINE_string(
    "logfile", "", "File to log start/stop events to."
)

_SERVICE_NAME = flags.DEFINE_string("service_name", "", "Windows service name,")


class FakeFleetspeakSvc(win32serviceutil.ServiceFramework):
  """Fake fleetspeak service."""

  # These attributes are needed by the parent class.
  _svc_name_: Optional[str] = None
  _svc_display_name_: Optional[str] = None
  _exe_name_: str = sys.executable
  _exe_args_: Optional[str] = None

  @classmethod
  def ParseFlags(cls):
    cls._svc_name_ = _SERVICE_NAME.value
    cls._svc_display_name_ = _SERVICE_NAME.value
    cls._exe_args_ = subprocess.list2cmdline([
        "-m",
        "grr_response_client_builder.fake_fleetspeak_windows_service",
        "--logfile",
        _LOGFILE.value,
        "--service_name",
        _SERVICE_NAME.value,
    ])

  def __init__(self, args):
    win32serviceutil.ServiceFramework.__init__(self, args)
    self._h_wait_stop = win32event.CreateEvent(None, 0, 0, None)

  def SvcStop(self):
    self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
    win32event.SetEvent(self._h_wait_stop)

  def SvcDoRun(self):
    servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                          servicemanager.PYS_SERVICE_STARTED,
                          (self._svc_name_, ""))
    self.main()

  def main(self):
    with open(_LOGFILE.value, "a") as f:
      print("start", file=f)
    rc = None
    while rc != win32event.WAIT_OBJECT_0:
      rc = win32event.WaitForSingleObject(self._h_wait_stop, (20 * 1000))
    with open(_LOGFILE.value, "a") as f:
      print("stop", file=f)


def main(argv):
  del argv  # Unused
  FakeFleetspeakSvc.ParseFlags()
  if _COMMAND.value:
    win32serviceutil.HandleCommandLine(
        FakeFleetspeakSvc, argv=[sys.argv[0], _COMMAND.value]
    )
  else:
    servicemanager.Initialize()
    servicemanager.PrepareToHostSingle(FakeFleetspeakSvc)
    servicemanager.StartServiceCtrlDispatcher()


if __name__ == "__main__":
  app.run(main)
