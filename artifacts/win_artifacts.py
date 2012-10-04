#!/usr/bin/env python
# Copyright 2012 Google Inc.
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


"""Artifacts that are specific to Windows."""




from grr.lib import artifact
from grr.lib import constants
from grr.lib import utils

# Shorcut to make things cleaner.
Artifact = artifact.GenericArtifact
Collector = artifact.Collector


################################################################################
#  Windows specific conditions
################################################################################


def VistaOrNewer(client):
  """Is the client newer than Windows Vista?"""
  system = client.Get(client.Schema.SYSTEM)
  if system != "Windows":
    raise artifact.ConditionError
  os_version = utils.SmartUnicode(client.Get(client.Schema.OS_VERSION, "0.0"))
  os_major_version = os_version.split(".")[0]
  return os_major_version > constants.MAJOR_VERSION_WINDOWS_VISTA


def NotVistaOrNewer(client):
  return not VistaOrNewer(client)


################################################################################
#  Event Log Artifacts for Vista + versions of Windows
################################################################################


class AbstractEventLogEvtx(Artifact):
  URL = "http://www.forensicswiki.org/wiki/Windows_XML_Event_Log_(EVTX)"
  CONDITIONS = [VistaOrNewer]
  SUPPORTED_OS = ["Windows"]
  LABELS = ["Logs"]
  PATH_VARS = {"log_path": "{systemroot}\\System32\\winevt\\Logs"}
  PROCESSORS = ["EvtxLogParser"]


class ApplicationEventLogEvtx(AbstractEventLogEvtx):
  """Windows Application Event Log for Vista or newer systems."""
  COLLECTORS = [
      Collector(action="GetFile",
                args={"path": "{log_path}\\Application.evtx"})]


class SystemEventLogEvtx(AbstractEventLogEvtx):
  """Windows System Event Log for Vista or newer systems."""
  COLLECTORS = [
      Collector(action="GetFile", args={"path": "{log_path}\\System.evtx"})]


class SecurityEventLogEvtx(AbstractEventLogEvtx):
  """Windows Security Event Log for Vista or newer systems."""
  COLLECTORS = [
      Collector(action="GetFile", args={"path": "{log_path}\\Security.evtx"})]


class TerminalServicesEventLogEvtx(AbstractEventLogEvtx):
  """Windows TerminalServices Event Log."""
  DESCRIPTION_LONG = """
Contains information about logins, connects, disconnects made via
RDP/TerminalServices to the machine.
"""
  COLLECTORS = [
      Collector(action="GetFile",
                args={"path": "{log_path}\\Microsoft-Windows-TerminalServices-"
                      "LocalSessionManager%4Operational.evtx"})]


################################################################################
#  Event Log Artifacts for older versions of Windows
################################################################################


class AbstractEventLog(Artifact):
  URL = "http://www.forensicswiki.org/wiki/Windows_Event_Log_(EVT)"
  SUPPORTED_OS = ["Windows"]
  CONDITIONS = [NotVistaOrNewer]
  LABELS = ["Logs"]
  PATH_VARS = {"log_path": "{systemroot}\\System32\\winevt\\Logs"}
  PROCESSORS = ["EvtLogParser"]


class ApplicationEventLog(AbstractEventLog):
  """Windows Application Event Log."""
  COLLECTORS = [
      Collector(action="GetFile", args={"path": "{log_path}\\AppEvent.evt"})]


class SystemEventLog(AbstractEventLog):
  """Windows System Event Log."""
  COLLECTORS = [
      Collector(action="GetFile", args={"path": "{log_path}\\SysEvent.evt"})]


class SecurityEventLog(AbstractEventLog):
  """Windows Security Event Log."""
  COLLECTORS = [
      Collector(action="GetFile", args={"path": "{log_path}\\SecEvent.evt"})]
