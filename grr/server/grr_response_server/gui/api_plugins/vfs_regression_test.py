#!/usr/bin/env python
"""This modules contains regression tests for VFS API handlers."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl import app

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_server import data_store
from grr_response_server import flow
from grr_response_server import flow_base
from grr_response_server.flows.general import discovery
from grr_response_server.flows.general import filesystem
from grr_response_server.gui import api_regression_test_lib
from grr_response_server.gui.api_plugins import vfs as vfs_plugin
from grr_response_server.gui.api_plugins import vfs_test as vfs_plugin_test
from grr.test_lib import acl_test_lib
from grr.test_lib import fixture_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class ApiListFilesHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest, vfs_plugin_test.VfsTestMixin):

  api_method = "ListFiles"
  handler = vfs_plugin.ApiListFilesHandler

  def Run(self):
    client_id = self.SetupClient(0)
    with test_lib.FakeTime(42):
      fixture_test_lib.ClientFixture(client_id)
    self.Check(
        "ListFiles",
        vfs_plugin.ApiListFilesArgs(
            client_id=client_id, file_path="fs/tsk/c/bin"))
    self.Check(
        "ListFiles",
        vfs_plugin.ApiListFilesArgs(
            client_id=client_id,
            file_path="fs/tsk/c/bin",
            timestamp=self.time_2))


class ApiGetFileTextHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest, vfs_plugin_test.VfsTestMixin):

  api_method = "GetFileText"
  handler = vfs_plugin.ApiGetFileTextHandler

  def Run(self):
    client_id = self.SetupClient(0)
    self.file_path = "fs/os/c/Downloads/a.txt"
    self.CreateFileVersions(client_id, self.file_path)

    self.Check(
        "GetFileText",
        args=vfs_plugin.ApiGetFileTextArgs(
            client_id=client_id, file_path=self.file_path))
    self.Check(
        "GetFileText",
        args=vfs_plugin.ApiGetFileTextArgs(
            client_id=client_id, file_path=self.file_path, offset=3, length=3))
    self.Check(
        "GetFileText",
        args=vfs_plugin.ApiGetFileTextArgs(
            client_id=client_id,
            file_path=self.file_path,
            timestamp=self.time_1))


class ApiGetFileVersionTimesHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest, vfs_plugin_test.VfsTestMixin):

  api_method = "GetFileVersionTimes"
  handler = vfs_plugin.ApiGetFileVersionTimesHandler

  def Run(self):
    client_id = self.SetupClient(0)
    self.file_path = "fs/os/c/Downloads/a.txt"
    self.CreateFileVersions(client_id, self.file_path)

    self.Check(
        "GetFileVersionTimes",
        args=vfs_plugin.ApiGetFileVersionTimesArgs(
            client_id=client_id, file_path=self.file_path))


class ApiListKnownEncodingsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest, vfs_plugin_test.VfsTestMixin):

  api_method = "ListKnownEncodings"
  handler = vfs_plugin.ApiListKnownEncodingsHandler

  def Run(self):
    self.Check("ListKnownEncodings")


class ApiGetFileDownloadCommandHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest, vfs_plugin_test.VfsTestMixin):

  api_method = "GetFileDownloadCommand"
  handler = vfs_plugin.ApiGetFileDownloadCommandHandler

  def Run(self):
    client_id = self.SetupClient(0)
    self.file_path = "fs/os/etc"
    self.Check(
        "GetFileDownloadCommand",
        args=vfs_plugin.ApiGetFileDownloadCommandArgs(
            client_id=client_id, file_path=self.file_path))


class ApiCreateVfsRefreshOperationHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest):
  """Regression test for ApiCreateVfsRefreshOperationHandler."""

  api_method = "CreateVfsRefreshOperation"
  handler = vfs_plugin.ApiCreateVfsRefreshOperationHandler

  def Run(self):
    client_id = self.SetupClient(0)

    # Choose some directory with pathspec in the ClientFixture.
    self.file_path = "fs/os/Users/Shared"

    fixture_test_lib.ClientFixture(client_id)

    def ReplaceFlowId():
      flows = data_store.REL_DB.ReadAllFlowObjects(client_id=client_id)
      return {flows[0].flow_id: "W:ABCDEF"}

    with test_lib.FakeTime(42):
      self.Check(
          "CreateVfsRefreshOperation",
          args=vfs_plugin.ApiCreateVfsRefreshOperationArgs(
              client_id=client_id, file_path=self.file_path, max_depth=1),
          replace=ReplaceFlowId)


class ApiGetVfsRefreshOperationStateHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest, vfs_plugin_test.VfsTestMixin):
  """Regression test for ApiGetVfsRefreshOperationStateHandler."""

  api_method = "GetVfsRefreshOperationState"
  handler = vfs_plugin.ApiGetVfsRefreshOperationStateHandler

  def Run(self):
    acl_test_lib.CreateUser(self.token.username)
    client_id = self.SetupClient(0)

    # Create a running mock refresh operation.
    flow_args = filesystem.RecursiveListDirectoryArgs()

    running_flow_id = flow_test_lib.StartFlow(
        filesystem.RecursiveListDirectory,
        client_id,
        flow_args=flow_args,
        creator=self.token.username)

    # Create a mock refresh operation and complete it.
    finished_flow_id = flow_test_lib.StartFlow(
        filesystem.RecursiveListDirectory,
        client_id,
        flow_args=flow_args,
        creator=self.token.username)

    # Kill flow.
    rdf_flow = data_store.REL_DB.LeaseFlowForProcessing(
        client_id, finished_flow_id,
        rdfvalue.Duration.From(5, rdfvalue.MINUTES))
    flow_cls = registry.FlowRegistry.FlowClassByName(rdf_flow.flow_class_name)
    flow_obj = flow_cls(rdf_flow)
    flow_obj.Error("Fake error")
    data_store.REL_DB.ReleaseProcessedFlow(rdf_flow)

    # Create an arbitrary flow to check on 404s.
    non_refresh_flow_id = flow_test_lib.StartFlow(
        discovery.Interrogate, client_id, creator=self.token.username)

    # Unkonwn flow ids should also cause 404s.
    unknown_flow_id = "F:12345678"

    # Check both operations.
    self.Check(
        "GetVfsRefreshOperationState",
        args=vfs_plugin.ApiGetVfsRefreshOperationStateArgs(
            client_id=client_id, operation_id=running_flow_id),
        replace={running_flow_id: "W:ABCDEF"})
    self.Check(
        "GetVfsRefreshOperationState",
        args=vfs_plugin.ApiGetVfsRefreshOperationStateArgs(
            client_id=client_id, operation_id=finished_flow_id),
        replace={finished_flow_id: "W:ABCDEF"})
    self.Check(
        "GetVfsRefreshOperationState",
        args=vfs_plugin.ApiGetVfsRefreshOperationStateArgs(
            client_id=client_id, operation_id=non_refresh_flow_id),
        replace={non_refresh_flow_id: "W:ABCDEF"})
    self.Check(
        "GetVfsRefreshOperationState",
        args=vfs_plugin.ApiGetVfsRefreshOperationStateArgs(
            client_id=client_id, operation_id=unknown_flow_id),
        replace={unknown_flow_id: "W:ABCDEF"})


class ApiUpdateVfsFileContentHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest):
  """Regression test for ApiUpdateVfsFileContentHandler."""

  api_method = "UpdateVfsFileContent"
  handler = vfs_plugin.ApiUpdateVfsFileContentHandler

  def Run(self):
    client_id = self.SetupClient(0)
    self.file_path = "fs/os/c/bin/bash"

    fixture_test_lib.ClientFixture(client_id)

    def ReplaceFlowId():
      flows = data_store.REL_DB.ReadAllFlowObjects(client_id=client_id)
      return {flows[0].flow_id: "W:ABCDEF"}

    with test_lib.FakeTime(42):
      self.Check(
          "UpdateVfsFileContent",
          args=vfs_plugin.ApiUpdateVfsFileContentArgs(
              client_id=client_id, file_path=self.file_path),
          replace=ReplaceFlowId)


class ApiGetVfsFileContentUpdateStateHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest, vfs_plugin_test.VfsTestMixin):
  """Regression test for ApiGetVfsFileContentUpdateStateHandler."""

  api_method = "GetVfsFileContentUpdateState"
  handler = vfs_plugin.ApiGetVfsFileContentUpdateStateHandler

  def Run(self):
    client_id = self.SetupClient(0)

    acl_test_lib.CreateUser(self.token.username)

    # Create a running mock refresh operation.
    running_flow_id = self.CreateMultiGetFileFlow(
        client_id, file_path="fs/os/c/bin/bash")

    # Create a mock refresh operation and complete it.
    finished_flow_id = self.CreateMultiGetFileFlow(
        client_id, file_path="fs/os/c/bin/bash")

    flow_base.TerminateFlow(client_id, finished_flow_id, reason="Fake Error")

    # Create an arbitrary flow to check on 404s.
    non_update_flow_id = flow.StartFlow(
        client_id=client_id, flow_cls=discovery.Interrogate)

    # Unkonwn flow ids should also cause 404s.
    unknown_flow_id = "F:12345678"

    # Check both operations.
    self.Check(
        "GetVfsFileContentUpdateState",
        args=vfs_plugin.ApiGetVfsFileContentUpdateStateArgs(
            client_id=client_id, operation_id=running_flow_id),
        replace={running_flow_id: "W:ABCDEF"})
    self.Check(
        "GetVfsFileContentUpdateState",
        args=vfs_plugin.ApiGetVfsFileContentUpdateStateArgs(
            client_id=client_id, operation_id=finished_flow_id),
        replace={finished_flow_id: "W:ABCDEF"})
    self.Check(
        "GetVfsFileContentUpdateState",
        args=vfs_plugin.ApiGetVfsFileContentUpdateStateArgs(
            client_id=client_id, operation_id=non_update_flow_id),
        replace={non_update_flow_id: "W:ABCDEF"})
    self.Check(
        "GetVfsFileContentUpdateState",
        args=vfs_plugin.ApiGetVfsFileContentUpdateStateArgs(
            client_id=client_id, operation_id=unknown_flow_id),
        replace={unknown_flow_id: "W:ABCDEF"})


class ApiGetVfsTimelineHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    vfs_plugin_test.VfsTimelineTestMixin):
  """Regression test for ApiGetVfsTimelineHandler."""

  api_method = "GetVfsTimeline"
  handler = vfs_plugin.ApiGetVfsTimelineHandler

  def Run(self):
    client_id = self.SetupTestTimeline()

    self.Check(
        "GetVfsTimeline",
        args=vfs_plugin.ApiGetVfsTimelineArgs(
            client_id=client_id, file_path=self.folder_path))


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
