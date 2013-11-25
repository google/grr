#!/usr/bin/env python
"""Cross-platform java artifacts."""

from grr.lib import artifact_lib

# Shorcut to make things cleaner.
Artifact = artifact_lib.GenericArtifact   # pylint: disable=g-bad-name
Collector = artifact_lib.Collector        # pylint: disable=g-bad-name

# pylint: disable=g-line-too-long


class JavaCacheFiles(Artifact):
  """Java Plug-in cache."""
  SUPPORTED_OS = ["Windows", "Linux", "Darwin"]
  COLLECTORS = [
      Collector(action="GetFiles",
                conditions=["os == 'Windows'"],
                args={"path_list":
                      [u"%%users.localappdata_low%%\\Sun\\Java\\Deployment\\cache\\**",
                       u"%%users.homedir%%\\AppData\\LocalLow\\Sun\\Java\\Deployment\\cache\\**",
                       u"%%users.homedir%%\\Application Data\\Sun\\Java\\Deployment\\cache\\**"]}),

      Collector(action="GetFile",
                conditions=["os == 'Darwin'"],
                args={"path": u"%%users.homedir%%/Library/Caches/Java/cache/**"}),

      Collector(action="GetFile",
                conditions=["os == 'Linux'"],
                args={"path": u"%%users.homedir%%/.java/deployment/cache/**"})]

