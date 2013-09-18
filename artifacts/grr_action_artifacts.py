#!/usr/bin/env python
"""Artifacts that are specific to GRR implementations.

These artifacts provide for using the artifact infrastructure and UI to launch
GRR specific flows.

While these can't be used outside of the GRR system, they produce output in the
same RDFValue form as other artifacts and therefore can be used in that
infrastructure usefully.
"""

from grr.lib import artifact_lib

# Shorcut to make things cleaner.
Artifact = artifact_lib.GenericArtifact   # pylint: disable=g-bad-name
Collector = artifact_lib.Collector        # pylint: disable=g-bad-name


class ListProcessesGrr(Artifact):
  """List system processes using the GRR ListProcesses client action."""
  LABELS = ["Processes"]
  COLLECTORS = [
      Collector(action="RunGrrClientAction",
                args={"client_action": r"ListProcesses"})]


class EnumerateInterfacesGrr(Artifact):
  """List network interfaces using the GRR EnumerateInterfaces client action."""
  LABELS = ["Network"]
  COLLECTORS = [
      Collector(action="RunGrrClientAction",
                args={"client_action": r"EnumerateInterfaces"})]


class NetstatGrr(Artifact):
  """List open network connections using the GRR netstat client action."""
  LABELS = ["Network"]
  COLLECTORS = [
      Collector(action="RunGrrClientAction",
                args={"client_action": r"Netstat"})]


class HostnameGrr(Artifact):
  """Get Hostname using the GRR GetHostname client action."""
  LABELS = ["System"]
  COLLECTORS = [
      Collector(action="RunGrrClientAction",
                args={"client_action": r"GetHostname"})]


class EnumerateUsersGrr(Artifact):
  """List users using the GRR EnumerateUsers client action."""
  LABELS = ["Users"]
  COLLECTORS = [
      Collector(action="RunGrrClientAction",
                args={"client_action": r"EnumerateUsers"})]


class EnumerateFilesystemsGrr(Artifact):
  """List mounted file systems using GRR EnumerateFilesystems client action."""
  LABELS = ["System"]
  COLLECTORS = [
      Collector(action="RunGrrClientAction",
                args={"client_action": r"EnumerateFilesystems"})]
