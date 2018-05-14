#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Tests for API client and VFS-related API calls."""

import StringIO
import threading
import time
import zipfile


from grr.lib import flags
from grr.lib import rdfvalue
from grr_response_proto.api import vfs_pb2
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server.gui import api_e2e_test_lib
from grr.test_lib import fixture_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class ApiClientLibVfsTest(api_e2e_test_lib.ApiE2ETest):
  """Tests VFS operations part of GRR Python API client library."""

  def setUp(self):
    super(ApiClientLibVfsTest, self).setUp()
    self.client_urn = self.SetupClient(0)
    fixture_test_lib.ClientFixture(self.client_urn, self.token)

  def testGetFileFromRef(self):
    file_ref = self.api.Client(
        client_id=self.client_urn.Basename()).File("fs/os/c/Downloads/a.txt")
    self.assertEqual(file_ref.path, "fs/os/c/Downloads/a.txt")

    file_obj = file_ref.Get()
    self.assertEqual(file_obj.path, "fs/os/c/Downloads/a.txt")
    self.assertFalse(file_obj.is_directory)
    self.assertEqual(file_obj.data.name, "a.txt")

  def testGetFileForDirectory(self):
    file_obj = self.api.Client(
        client_id=self.client_urn.Basename()).File("fs/os/c/Downloads").Get()
    self.assertEqual(file_obj.path, "fs/os/c/Downloads")
    self.assertTrue(file_obj.is_directory)

  def testListFiles(self):
    files_iter = self.api.Client(client_id=self.client_urn.Basename()).File(
        "fs/os/c/Downloads").ListFiles()
    files_list = list(files_iter)

    self.assertEqual(
        sorted(f.data.name for f in files_list),
        sorted(
            [u"a.txt", u"b.txt", u"c.txt", u"d.txt", u"sub1", u"中国新闻网新闻中.txt"]))

  def testGetBlob(self):
    out = StringIO.StringIO()
    self.api.Client(client_id=self.client_urn.Basename()).File(
        "fs/tsk/c/bin/rbash").GetBlob().WriteToStream(out)

    self.assertEqual(out.getvalue(), "Hello world")

  def testGetBlobUnicode(self):
    aff4.FACTORY.Copy("aff4:/C.1000000000000000/fs/tsk/c/bin/bash",
                      "aff4:/C.1000000000000000/fs/tsk/c/bin/中国新闻网新闻中")

    out = StringIO.StringIO()
    self.api.Client(client_id=self.client_urn.Basename()).File(
        u"fs/tsk/c/bin/中国新闻网新闻中").GetBlob().WriteToStream(out)

    self.assertEqual(out.getvalue(), "Hello world")

  def testGetFilesArchive(self):
    zip_stream = StringIO.StringIO()
    self.api.Client(client_id=self.client_urn.Basename()).File(
        "fs/tsk/c/bin").GetFilesArchive().WriteToStream(zip_stream)
    zip_fd = zipfile.ZipFile(zip_stream)

    namelist = zip_fd.namelist()
    self.assertEqual(
        sorted(namelist),
        sorted([
            "vfs_C_1000000000000000_fs_tsk_c_bin/fs/tsk/c/bin/rbash",
            "vfs_C_1000000000000000_fs_tsk_c_bin/fs/tsk/c/bin/bash"
        ]))

  def testGetVersionTimes(self):
    vtimes = self.api.Client(client_id=self.client_urn.Basename()).File(
        "fs/os/c/Downloads/a.txt").GetVersionTimes()
    self.assertEqual(len(vtimes), 1)

  def testRefresh(self):
    operation = self.api.Client(client_id=self.client_urn.Basename()).File(
        "fs/os/c/Downloads").Refresh()
    self.assertTrue(operation.operation_id)
    self.assertEqual(operation.GetState(), operation.STATE_RUNNING)

  def testRefreshWaitUntilDone(self):
    f = self.api.Client(
        client_id=self.client_urn.Basename()).File("fs/os/c/Downloads")
    operation = f.Refresh()
    self.assertEqual(operation.GetState(), operation.STATE_RUNNING)

    def ProcessOperation():
      time.sleep(1)
      # We assume that the operation id is the URN of a flow.
      flow_test_lib.TestFlowHelper(
          rdfvalue.RDFURN(operation.operation_id),
          client_id=self.client_urn,
          token=self.token)

    threading.Thread(target=ProcessOperation).start()
    result_f = operation.WaitUntilDone().target_file
    self.assertEqual(f.path, result_f.path)
    self.assertEqual(operation.GetState(), operation.STATE_FINISHED)

  def testCollect(self):
    operation = self.api.Client(client_id=self.client_urn.Basename()).File(
        "fs/os/c/Downloads/a.txt").Collect()
    self.assertTrue(operation.operation_id)
    self.assertEqual(operation.GetState(), operation.STATE_RUNNING)

  def testCollectWaitUntilDone(self):
    f = self.api.Client(
        client_id=self.client_urn.Basename()).File("fs/os/c/Downloads/a.txt")
    operation = f.Collect()
    self.assertEqual(operation.GetState(), operation.STATE_RUNNING)

    def ProcessOperation():
      time.sleep(1)
      # We assume that the operation id is the URN of a flow.
      flow_test_lib.TestFlowHelper(
          rdfvalue.RDFURN(operation.operation_id),
          client_id=self.client_urn,
          token=self.token)

    threading.Thread(target=ProcessOperation).start()
    result_f = operation.WaitUntilDone().target_file
    self.assertEqual(f.path, result_f.path)
    self.assertEqual(operation.GetState(), operation.STATE_FINISHED)

  def testGetTimeline(self):
    timeline = self.api.Client(
        client_id=self.client_urn.Basename()).File("fs").GetTimeline()
    self.assertTrue(timeline)
    for item in timeline:
      self.assertTrue(isinstance(item, vfs_pb2.ApiVfsTimelineItem))

  def testGetTimelineAsCsv(self):
    out = StringIO.StringIO()
    self.api.Client(client_id=self.client_urn.Basename()).File(
        "fs").GetTimelineAsCsv().WriteToStream(out)
    self.assertTrue(out.getvalue())


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
