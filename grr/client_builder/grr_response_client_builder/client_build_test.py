#!/usr/bin/env python
import io
import multiprocessing
import os
from unittest import mock

from absl.testing import absltest

from grr_response_client_builder import client_build
from grr_response_core.lib.util import temp


class MultiRepackTest(absltest.TestCase):

  def setUp(self):
    super().setUp()
    self.pool_obj = mock.MagicMock()
    pool_patcher = mock.patch.object(
        multiprocessing, "Pool", return_value=self.pool_obj)
    self.mock_pool = pool_patcher.start()
    self.addCleanup(pool_patcher.stop)

    config_dir = temp.TempDirPath()
    self.config_foo = os.path.join(config_dir, "foo.yaml")
    self.config_bar = os.path.join(config_dir, "bar.yaml")
    with io.open(self.config_foo, mode="w") as filedesc:
      filedesc.write("Client.company_name: foo")
    with io.open(self.config_bar, mode="w") as filedesc:
      filedesc.write("Client.company_name: bar")
    self.template_dir = temp.TempDirPath()
    self.deb_template = os.path.join(self.template_dir,
                                     "grr_3.1.0.2_amd64.deb.zip")
    self.exe_template = os.path.join(self.template_dir,
                                     "GRR_3.1.0.2_i386.exe.zip")
    self.xar_template = os.path.join(self.template_dir,
                                     "grr_3.1.0.2_amd64.xar.zip")
    with io.open(self.deb_template, mode="w") as filedesc:
      filedesc.write("linux")
    with io.open(self.exe_template, mode="w") as filedesc:
      filedesc.write("windows")
    with io.open(self.xar_template, mode="w") as filedesc:
      filedesc.write("darwin")

    self.output_dir = temp.TempDirPath()

  def testMultipleRepackingNoSigning(self):
    client_build.MultiTemplateRepacker().RepackTemplates(
        [self.config_foo, self.config_bar],
        [self.deb_template, self.exe_template, self.xar_template],
        self.output_dir,
    )

    # (3 templates + 1 debug) x 2 configs = 8 repacks
    self.assertEqual(self.pool_obj.apply_async.call_count, 8)


if __name__ == "__main__":
  absltest.main()
