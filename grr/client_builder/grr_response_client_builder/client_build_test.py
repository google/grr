#!/usr/bin/env python
"""Tests for grr_response_client.client_build."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io
import multiprocessing
import os
import platform
import unittest


from absl.testing import absltest
import mock

from grr_response_client_builder import builders
from grr_response_client_builder import client_build
from grr_response_core.lib.util import temp


class ClientBuildTest(absltest.TestCase):

  @unittest.skipUnless(platform.system() == "Linux",
                       "Just test linux to avoid lots of patching")
  def testBuildingContext(self):
    with mock.patch.object(builders, "LinuxClientBuilder") as mock_builder:
      client_build.TemplateBuilder().BuildTemplate()
      self.assertEqual(mock_builder.call_count, 1)


class MultiRepackTest(absltest.TestCase):

  def setUp(self):
    super(MultiRepackTest, self).setUp()
    self.pool_obj = mock.MagicMock()
    pool_patcher = mock.patch.object(
        multiprocessing, "Pool", return_value=self.pool_obj)
    self.mock_pool = pool_patcher.start()
    self.addCleanup(pool_patcher.stop)

    config_dir = temp.TempDirPath()
    self.label1_config = os.path.join(config_dir, "label1.yaml")
    self.label2_config = os.path.join(config_dir, "label2.yaml")
    with io.open(self.label1_config, mode="w") as filedesc:
      filedesc.write("Client.labels: [label1]")
    with io.open(self.label2_config, mode="w") as filedesc:
      filedesc.write("Client.labels: [label2]")
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
        [self.label1_config, self.label2_config],
        [self.deb_template, self.exe_template, self.xar_template],
        self.output_dir)

    # (3 templates + 1 debug) x 2 labels = 8 repacks
    self.assertEqual(self.pool_obj.apply_async.call_count, 8)


if __name__ == "__main__":
  absltest.main()
