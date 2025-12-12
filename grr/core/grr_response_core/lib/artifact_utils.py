#!/usr/bin/env python
"""Library for processing of artifacts.

This file contains non-GRR specific pieces of artifact processing and is
intended to end up as an independent library.
"""

from collections.abc import Sequence
import re

from grr_response_proto import knowledge_base_pb2


class Error(Exception):
  """Base exception."""


class ConditionError(Error):
  """An invalid artifact condition was specified."""


class ArtifactProcessingError(Error):
  """Unable to process artifact."""


class KnowledgeBaseUninitializedError(Error):
  """Attempt to process artifact without a valid Knowledge Base."""


class KnowledgeBaseAttributesMissingError(Error):
  """Knowledge Base is missing key attributes."""


INTERPOLATED_REGEX = re.compile(r"%%([^%]+?)%%")


def ExpandKnowledgebaseWindowsEnvVars(
    unexpanded_kb: knowledge_base_pb2.KnowledgeBase,
) -> knowledge_base_pb2.KnowledgeBase:
  """Expands all Windows environment variable values in the given knowledgebase.

  Unexpanded values can contain references to other environment variables, e.g.
  `%SystemRoot/System32`. Such references are expanded using knowledgebase
  values recursively, e.g. the above could be expanded to `C:/System32`.

  If an environment variable value contains a reference that cannot be expanded,
  this function will not raise but rather leave it in unexpanded form (similarly
  to what Windows shell does).

  If unexpanded references form a cycle, this function will raise.

  Args:
    unexpanded_kb: A knowledgebase with environment variables to expand.

  Returns:
    A knowledgebase in which all environment variables are expanded.
  """
  if unexpanded_kb.os != "Windows":
    raise ValueError(f"Invalid system: {unexpanded_kb.os!r}")

  kb = knowledge_base_pb2.KnowledgeBase(
      environ_path="%SystemRoot%\\;%SystemRoot%\\System32\\;%SystemRoot%\\System32\\wbem\\",
      environ_temp="%SystemRoot%\\TEMP",
      environ_allusersappdata="%ProgramData%",
      environ_allusersprofile="%ProgramData%",
      environ_commonprogramfiles="%ProgramFiles%\\Common Files",
      environ_commonprogramfilesx86="%ProgramFiles(x86)%\\Common Files",
      environ_comspec="%SystemRoot%\\System32\\cmd.exe",
      environ_driverdata="%SystemRoot%\\System32\\Drivers\\DriverData",
      environ_programfiles="%SystemDrive%\\Program Files",
      environ_programfilesx86="%SystemDrive%\\Program Files (x86)",
      environ_programdata="%SystemDrive%\\ProgramData",
      environ_systemdrive="C:",
      environ_systemroot="%SystemDrive%\\Windows",
      environ_windir="%SystemRoot%",
  )
  kb.MergeFrom(unexpanded_kb)

  already_expanded_env_var_refs: dict[str, str] = dict()
  currently_expanded_env_var_refs: set[str] = set()

  def Expand(unexpanded: str) -> str:
    expanded = ""
    offset = 0

    for match in re.finditer("%[^%]+?%", unexpanded):
      env_var_ref = match.group(0).upper()

      expanded += unexpanded[offset : match.start()]
      offset += match.end()

      if env_var_ref in already_expanded_env_var_refs:
        expanded += already_expanded_env_var_refs[env_var_ref]
        continue

      if env_var_ref in currently_expanded_env_var_refs:
        raise ValueError(f"Circular dependency involving {env_var_ref!r}")

      if env_var_ref == "%PATH%":
        value = kb.environ_path
      elif env_var_ref == "%TEMP%":
        value = kb.environ_temp
      elif env_var_ref == "%ALLUSERSAPPDATA%":
        value = kb.environ_allusersappdata
      elif env_var_ref == "%ALLUSERSPROFILE%":
        value = kb.environ_allusersprofile
      elif env_var_ref == "%COMMONPROGRAMFILES%":
        value = kb.environ_commonprogramfiles
      elif env_var_ref == "%COMMONPROGRAMFILES(X86)%":
        value = kb.environ_commonprogramfilesx86
      elif env_var_ref == "%COMSPEC%":
        value = kb.environ_comspec
      elif env_var_ref == "%DRIVERDATA%":
        value = kb.environ_driverdata
      elif env_var_ref == "%PROGRAMFILES%":
        value = kb.environ_programfiles
      elif env_var_ref == "%PROGRAMFILES(X86)%":
        value = kb.environ_programfilesx86
      elif env_var_ref == "%PROGRAMDATA%":
        value = kb.environ_programdata
      elif env_var_ref == "%SYSTEMDRIVE%":
        value = kb.environ_systemdrive
      elif env_var_ref == "%SYSTEMROOT%":
        value = kb.environ_systemroot
      elif env_var_ref == "%WINDIR%":
        value = kb.environ_windir
      else:
        # We use original match instead of `env_var_ref` as the latter was case
        # corrected.
        expanded += match.group(0)
        continue

      currently_expanded_env_var_refs.add(env_var_ref)
      already_expanded_env_var_refs[env_var_ref] = Expand(value)
      currently_expanded_env_var_refs.remove(env_var_ref)

      expanded += already_expanded_env_var_refs[env_var_ref]

    expanded += unexpanded[offset:]
    return expanded

  kb.environ_path = Expand(kb.environ_path)
  kb.environ_temp = Expand(kb.environ_temp)
  kb.environ_allusersappdata = Expand(kb.environ_allusersappdata)
  kb.environ_allusersprofile = Expand(kb.environ_allusersprofile)
  kb.environ_commonprogramfiles = Expand(kb.environ_commonprogramfiles)
  kb.environ_commonprogramfilesx86 = Expand(kb.environ_commonprogramfilesx86)
  kb.environ_comspec = Expand(kb.environ_comspec)
  kb.environ_driverdata = Expand(kb.environ_driverdata)
  kb.environ_profilesdirectory = Expand(kb.environ_profilesdirectory)
  kb.environ_programfiles = Expand(kb.environ_programfiles)
  kb.environ_programfilesx86 = Expand(kb.environ_programfilesx86)
  kb.environ_programdata = Expand(kb.environ_programdata)
  kb.environ_systemdrive = Expand(kb.environ_systemdrive)
  kb.environ_systemroot = Expand(kb.environ_systemroot)
  kb.environ_windir = Expand(kb.environ_windir)
  return kb


class KnowledgeBaseInterpolation:
  """Interpolation of the given pattern with knowledgebase values.

  Pattern can have placeholder variables like `%%os%%` or `%%fqdn%%` that will
  be replaced by concrete values from the knowledgebase corresponding to these.

  In case of repeated knowledgebase values like `users`, every possible result
  is returned.

  Because interpolation can sometimes omit certain results or use some default
  values, this object exposes a `logs` property with messages when such steps
  were made. These messages can then be forwarded to the user specifying the
  pattern to help the debug issues in case the pattern is behaving unexpectedly.
  """

  def __init__(
      self,
      pattern: str,
      kb: knowledge_base_pb2.KnowledgeBase,
  ) -> None:
    self._results: list[str] = list()
    self._logs: list[str] = list()

    user_attrs = [
        m["attr"] for m in re.finditer(r"%%users\.(?P<attr>\w+)%%", pattern)
    ]
    non_user_attrs = [
        m["attr"] for m in re.finditer(r"%%(?P<attr>\w+)%%", pattern)
    ]

    if not user_attrs:
      # If the pattern does not contain any user attributes, loops below won't
      # yield any results. Hence, we add the pattern as-is for further expansion
      # to always have at least one to work with.
      self._results.append(pattern)
    else:
      # We start with interpolating `users` variables for each user. Because
      # there can be multiple users on the system and the pattern can contain
      # both user and non-user variables we have to then combine all possible
      # user-based interpolations with non-user-based ones.
      for user in kb.users:
        # There might be cases in which username is not strictly necessary but
        # scenario in which we do not have username but have other values is
        # very unlikely. Assuming that users do have usernames makes the logic
        # much simpler below.
        if not (username := user.username):
          self._logs.append(
              f"user {user!r} without username",
          )
          continue

        user_result = pattern

        for attr in user_attrs:
          try:
            value = getattr(user, attr)
          except AttributeError as error:
            raise ValueError(f"`%%users.{attr}%%` does not exist") from error

          if not value:
            if kb.os == "Windows":
              # `userprofile` is a base for all default values so we use various
              # heuristics to derive it in case it is not available.
              if user.userprofile:
                userprofile = user.userprofile
              elif user.homedir:
                userprofile = user.homedir
              elif kb.environ_systemdrive:
                userprofile = f"{kb.environ_systemdrive}\\Users\\{username}"
              else:
                userprofile = f"C:\\Users\\{username}"

              try:
                value = {
                    # pylint: disable=line-too-long
                    # pyformat: disable
                    "userprofile": userprofile,
                    "homedir": userprofile,
                    "temp": f"{userprofile}\\AppData\\Local\\Temp",
                    "desktop": f"{userprofile}\\Desktop",
                    "appdata": f"{userprofile}\\AppData\\Roaming",
                    "localappdata": f"{userprofile}\\AppData\\Local",
                    "cookies": f"{userprofile}\\AppData\\Local\\Microsoft\\Windows\\INetCookies",
                    "recent": f"{userprofile}\\AppData\\Roaming\\Microsoft\\Windows\\Recent",
                    "personal": f"{userprofile}\\Documents",
                    "startup": f"{userprofile}\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Startup",
                    # pylint: enable=line-too-long
                    # pyformat: enable
                }[attr]
              except KeyError:
                self._logs.append(
                    f"user {username!r} is missing {attr!r} (no Windows "
                    "default available)",
                )
                break
            else:
              self._logs.append(
                  f"user {username!r} is missing {attr!r} (no fallback "
                  "available)",
              )
              break

            self._logs.append(
                f"using default {value!r} for {attr!r} for user {username!r}",
            )

          user_result = user_result.replace(f"%%users.{attr}%%", value)
        else:
          # This will run only if we successfully filled every variable. If any
          # is missing we will break the loop and this block won't be executed.
          self._results.append(user_result)

    # At this point all results have no user variables, so there is only one way
    # to interpolate them. We do a pass for every variable in every result to
    # expand these.
    for attr in non_user_attrs:
      try:
        value = getattr(kb, attr)
      except AttributeError as error:
        raise ValueError(f"`%%{attr}%%` does not exist") from error

      if not value:
        self._logs.append(
            f"{attr!r} is missing",
        )
        # If the attribute value is missing in the knowledge base, the pattern
        # cannot be interpolated and should yield no results.
        self._results = []

      # Because strings in Python are immutable, we cannot simply iterate over
      # the elements of the list if we want to update them, so we use indices to
      # simulate references.
      for i in range(len(self._results)):
        self._results[i] = self._results[i].replace(f"%%{attr}%%", value)

  @property
  def results(self) -> Sequence[str]:
    return self._results

  @property
  def logs(self) -> Sequence[str]:
    return self._logs
