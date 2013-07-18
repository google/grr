#!/usr/bin/env python
"""Run all our binaries and check the run without failing.

This runs each of our entry point binaries. Given we have a bunch of them it can
be hard to know what breaks when doing refactoring. This ensures that they at
least run without raising errors.
"""

import os
import shutil


# pylint: disable=unused-import
# Matplotlib has a race condition when creating config file directories. We
# import it here once and let it create everything.
import matplotlib.pyplot as plt
# pylint: enable=unused-import

from grr.client import conf
from grr.client import conf as flags

from grr.lib import config_lib
from grr.lib import test_lib

FLAGS = flags.FLAGS


class EntryPointTest(test_lib.GRRBaseTest):
  """This class tests the flow scheduling method in benchmark_tests.py."""

  def setUp(self):
    """Sets up the environment for the tests."""
    super(EntryPointTest, self).setUp()
    self.bin_dir = os.path.join(config_lib.CONFIG["Test.srcdir"], "grr")
    self.bin_ext = ".py"
    self.extra_opts = ""
    self.default_timeout = 4
    self.interpreter = "python "

    # Make a copy of the config so that tests don't update it.
    config_file = os.path.join(config_lib.CONFIG["Test.srcdir"],
                               "grr/test_data/grr_test.conf")
    tmp_config = os.path.join(self.temp_dir, "temp.conf")

    shutil.copy(config_file, tmp_config)

    self.extra_opts = " --config=%s" % config_file


  def testWorker(self):
    run_bin = os.path.join(self.bin_dir, "worker", "worker" + self.bin_ext +
                           self.extra_opts)
    self.RunForTimeWithNoExceptions(self.interpreter + run_bin,
                                    timeout=self.default_timeout)

  def testEnroller(self):
    run_bin = os.path.join(self.bin_dir, "worker",
                           "enroller" + self.bin_ext + self.extra_opts)
    self.RunForTimeWithNoExceptions(self.interpreter + run_bin,
                                    timeout=self.default_timeout)

  def testHttpServer(self):
    run_bin = os.path.join(self.bin_dir, "tools",
                           "http_server" + self.bin_ext + self.extra_opts)
    self.RunForTimeWithNoExceptions(self.interpreter + run_bin,
                                    timeout=self.default_timeout)

  def testAdminUI(self):
    run_bin = os.path.join(self.bin_dir, "gui",
                           "admin_ui" + self.bin_ext + self.extra_opts)
    self.RunForTimeWithNoExceptions(self.interpreter + run_bin,
                                    timeout=self.default_timeout)

  def testConsole(self):
    run_bin = os.path.join(self.bin_dir, "tools", "console" + self.bin_ext
                           + self.extra_opts + "  --code_to_execute='pass'")
    self.RunForTimeWithNoExceptions(self.interpreter +
                                    run_bin, should_exit=True,
                                    check_exit_code=True,
                                    timeout=15)

  def testGrrSingleServer(self):
    run_bin = os.path.join(self.bin_dir, "tools",
                           "grr_server" + self.bin_ext + self.extra_opts)
    self.RunForTimeWithNoExceptions(self.interpreter + run_bin,
                                    timeout=self.default_timeout*2)

  def testFileExporter(self):
    run_bin = os.path.join(self.bin_dir, "tools",
                           "file_exporter" + self.bin_ext + self.extra_opts)
    self.RunForTimeWithNoExceptions(self.interpreter + run_bin,
                                    should_exit=True,
                                    timeout=self.default_timeout)

  def testClient(self):
    run_bin = os.path.join(self.bin_dir, "client",
                           "client" + self.bin_ext + self.extra_opts)
    self.RunForTimeWithNoExceptions(self.interpreter + run_bin,
                                    timeout=self.default_timeout)



def main(argv):

  # Run the full test suite
  test_lib.main(argv)

if __name__ == "__main__":
  conf.StartMain(main)
