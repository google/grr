#!/usr/bin/env python
"""Run all our binaries and check the run without failing.

This runs each of our entry point binaries. Given we have a bunch of them it can
be hard to know what breaks when doing refactoring. This ensures that they at
least run without raising errors.
"""

import os
import sys


# pylint: disable=unused-import
# Matplotlib has a race condition when creating config file directories. We
# import it here once and let it create everything.
import matplotlib.pyplot as plt
# pylint: enable=unused-import

from grr.lib import config_lib
from grr.lib import flags
from grr.lib import test_lib
from grr.lib import type_info


class EntryPointTest(test_lib.GRRBaseTest):
  """This class tests GRR's code entry points run without failing."""

  def setUp(self):
    """Sets up the environment for the tests."""
    super(EntryPointTest, self).setUp()

    self.config_file = os.path.join(self.temp_dir, "writeback.yaml")
    new_config = config_lib.CONFIG.MakeNewConfig()
    new_config.SetWriteBack(self.config_file)
    for info in config_lib.CONFIG.type_infos:
      try:
        new_value = config_lib.CONFIG.GetRaw(info.name, None)
      except type_info.TypeValueError:
        continue

      if new_value is not None:
        new_config.SetRaw(info.name, config_lib.CONFIG.GetRaw(info.name))

    new_config.Write()

    self.bin_dir = os.path.join(config_lib.CONFIG["Test.srcdir"], "grr")
    self.bin_ext = ".py"
    self.extra_opts = ["--config", self.config_file, "--context",
                       "Test Context,EntryPoint Context"]
    self.default_timeout = 10
    self.interpreter = sys.executable


  @test_lib.SetLabel("large")
  def testWorker(self):
    run_bin = os.path.join(self.bin_dir, "worker", "worker" + self.bin_ext)
    self.RunForTimeWithNoExceptions(self.interpreter,
                                    [run_bin] + self.extra_opts,
                                    timeout=self.default_timeout)

  @test_lib.SetLabel("large")
  def testEnroller(self):
    run_bin = os.path.join(self.bin_dir, "worker",
                           "enroller" + self.bin_ext)
    self.RunForTimeWithNoExceptions(self.interpreter,
                                    [run_bin] + self.extra_opts,
                                    timeout=self.default_timeout)

  @test_lib.SetLabel("large")
  def testHttpServer(self):
    run_bin = os.path.join(self.bin_dir, "tools",
                           "http_server" + self.bin_ext)
    self.RunForTimeWithNoExceptions(self.interpreter,
                                    [run_bin] + self.extra_opts,
                                    timeout=self.default_timeout)

  @test_lib.SetLabel("large")
  def testAdminUI(self):
    run_bin = os.path.join(self.bin_dir, "gui",
                           "admin_ui" + self.bin_ext)
    self.RunForTimeWithNoExceptions(self.interpreter,
                                    [run_bin] + self.extra_opts,
                                    timeout=self.default_timeout)

  @test_lib.SetLabel("large")
  def testConsole(self):
    self.extra_opts.append("--code_to_execute='pass'")
    run_bin = os.path.join(self.bin_dir, "tools", "console" + self.bin_ext)
    self.RunForTimeWithNoExceptions(self.interpreter,
                                    [run_bin] + self.extra_opts,
                                    should_exit=True, check_exit_code=True,
                                    timeout=self.default_timeout*2)

  @test_lib.SetLabel("large")
  def testGrrSingleServer(self):
    run_bin = os.path.join(self.bin_dir, "tools",
                           "grr_server" + self.bin_ext)
    self.RunForTimeWithNoExceptions(self.interpreter,
                                    [run_bin] + self.extra_opts,
                                    timeout=self.default_timeout*2)

  @test_lib.SetLabel("large")
  def testFileExporter(self):
    run_bin = os.path.join(self.bin_dir, "tools",
                           "export" + self.bin_ext)
    self.RunForTimeWithNoExceptions(self.interpreter,
                                    [run_bin] + self.extra_opts,
                                    should_exit=True,
                                    timeout=self.default_timeout*2)

  @test_lib.SetLabel("large")
  def testClient(self):
    run_bin = os.path.join(self.bin_dir, "client",
                           "client" + self.bin_ext)
    self.RunForTimeWithNoExceptions(self.interpreter,
                                    [run_bin] + self.extra_opts,
                                    timeout=self.default_timeout)

  @test_lib.SetLabel("large")
  def testEndToEnd(self):
    self.extra_opts.append("--testnames=''")
    run_bin = os.path.join(self.bin_dir, "tools", "end_to_end_tests" +
                           self.bin_ext)
    self.RunForTimeWithNoExceptions(self.interpreter,
                                    [run_bin] + self.extra_opts,
                                    should_exit=True, check_exit_code=True,
                                    timeout=self.default_timeout*2)



def main(argv):

  # Run the full test suite
  test_lib.main(argv)

if __name__ == "__main__":
  flags.StartMain(main)
