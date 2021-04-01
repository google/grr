#!/usr/bin/env python
# pylint: mode=test

from absl.testing import flagsaver
from grr_response_core.lib import config_lib
from grr_response_core.lib.util import temp


def SetUpDummyConfig():
  with temp.AutoTempFilePath(suffix="yaml") as dummy_config_path:
    with flagsaver.flagsaver(config=dummy_config_path):
      config_lib.ParseConfigCommandLine()
