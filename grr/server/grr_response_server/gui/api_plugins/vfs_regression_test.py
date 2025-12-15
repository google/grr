#!/usr/bin/env python
"""This modules contains regression tests for VFS API handlers."""

from absl import app

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_proto.api import vfs_pb2 as api_vfs_pb2
from grr_response_server import data_store
from grr_response_server import flow
from grr_response_server import flow_base
from grr_response_server.flows.general import discovery
from grr_response_server.flows.general import filesystem
from grr_response_server.gui import api_regression_test_lib
from grr_response_server.gui.api_plugins import vfs as vfs_plugin
from grr_response_server.gui.api_plugins import vfs_test as vfs_plugin_test
from grr_response_server.rdfvalues import mig_flow_objects
from grr.test_lib import acl_test_lib
from grr.test_lib import fixture_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class ApiListFilesHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest, vfs_plugin_test.VfsTestMixin
):

  api_method = "ListFiles"
  handler = vfs_plugin.ApiListFilesHandler

  def Run(self):
    client_id = self.SetupClient(0)
    with test_lib.FakeTime(42):
      fixture_test_lib.ClientFixture(client_id)
    self.Check(
        "ListFiles",
        api_vfs_pb2.ApiListFilesArgs(
            client_id=client_id, file_path="fs/tsk/c/bin"
        ),
    )
    self.Check(
        "ListFiles",
        api_vfs_pb2.ApiListFilesArgs(
            client_id=client_id,
            file_path="fs/tsk/c/bin",
            timestamp=self.time_2.AsMicrosecondsSinceEpoch(),
        ),
    )


class ApiGetFileTextHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest, vfs_plugin_test.VfsTestMixin
):

  api_method = "GetFileText"
  handler = vfs_plugin.ApiGetFileTextHandler

  def Run(self):
    client_id = self.SetupClient(0)
    self.file_path = "fs/os/c/Downloads/a.txt"
    self.CreateFileVersions(client_id, self.file_path)

    self.Check(
        "GetFileText",
        args=api_vfs_pb2.ApiGetFileTextArgs(
            client_id=client_id, file_path=self.file_path
        ),
    )
    self.Check(
        "GetFileText",
        args=api_vfs_pb2.ApiGetFileTextArgs(
            client_id=client_id, file_path=self.file_path, offset=3, length=3
        ),
    )
    self.Check(
        "GetFileText",
        args=api_vfs_pb2.ApiGetFileTextArgs(
            client_id=client_id,
            file_path=self.file_path,
            timestamp=self.time_1.AsMicrosecondsSinceEpoch(),
        ),
    )


class ApiGetFileVersionTimesHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest, vfs_plugin_test.VfsTestMixin
):

  api_method = "GetFileVersionTimes"
  handler = vfs_plugin.ApiGetFileVersionTimesHandler

  def Run(self):
    client_id = self.SetupClient(0)
    self.file_path = "fs/os/c/Downloads/a.txt"
    self.CreateFileVersions(client_id, self.file_path)

    self.Check(
        "GetFileVersionTimes",
        args=api_vfs_pb2.ApiGetFileVersionTimesArgs(
            client_id=client_id, file_path=self.file_path
        ),
    )


class ApiGetFileDownloadCommandHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest, vfs_plugin_test.VfsTestMixin
):

  api_method = "GetFileDownloadCommand"
  handler = vfs_plugin.ApiGetFileDownloadCommandHandler

  def Run(self):
    client_id = self.SetupClient(0)
    self.file_path = "fs/os/etc"
    self.Check(
        "GetFileDownloadCommand",
        args=api_vfs_pb2.ApiGetFileDownloadCommandArgs(
            client_id=client_id, file_path=self.file_path
        ),
    )


class ApiCreateVfsRefreshOperationHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest
):
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
      return {flows[0].flow_id: "ABCDEF"}

    with test_lib.FakeTime(42):
      self.Check(
          "CreateVfsRefreshOperation",
          args=api_vfs_pb2.ApiCreateVfsRefreshOperationArgs(
              client_id=client_id, file_path=self.file_path, max_depth=1
          ),
          replace=ReplaceFlowId,
      )


class ApiGetVfsRefreshOperationStateHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest, vfs_plugin_test.VfsTestMixin
):
  """Regression test for ApiGetVfsRefreshOperationStateHandler."""

  api_method = "GetVfsRefreshOperationState"
  handler = vfs_plugin.ApiGetVfsRefreshOperationStateHandler

  def Run(self):
    acl_test_lib.CreateUser(self.test_username)
    client_id = self.SetupClient(0)

    # Create a running mock refresh operation.
    flow_args = filesystem.RecursiveListDirectoryArgs()

    running_flow_id = flow_test_lib.StartFlow(
        filesystem.RecursiveListDirectory,
        client_id,
        flow_args=flow_args,
        creator=self.test_username,
    )

    # Create a mock refresh operation and complete it.
    finished_flow_id = flow_test_lib.StartFlow(
        filesystem.RecursiveListDirectory,
        client_id,
        flow_args=flow_args,
        creator=self.test_username,
    )

    # Kill flow.
    proto_flow = data_store.REL_DB.LeaseFlowForProcessing(
        client_id, finished_flow_id, rdfvalue.Duration.From(5, rdfvalue.MINUTES)
    )
    rdf_flow = mig_flow_objects.ToRDFFlow(proto_flow)
    flow_cls = registry.FlowRegistry.FlowClassByName(rdf_flow.flow_class_name)
    flow_obj = flow_cls(rdf_flow)
    flow_obj.Error("Fake error")
    proto_flow = mig_flow_objects.ToProtoFlow(rdf_flow)
    data_store.REL_DB.ReleaseProcessedFlow(proto_flow)

    # Create an arbitrary flow to check on 404s.
    non_refresh_flow_id = flow_test_lib.StartFlow(
        discovery.Interrogate, client_id, creator=self.test_username
    )

    # Unknown flow ids should also cause 404s.
    unknown_flow_id = "12345678"

    # Check both operations.
    self.Check(
        "GetVfsRefreshOperationState",
        args=api_vfs_pb2.ApiGetVfsRefreshOperationStateArgs(
            client_id=client_id, operation_id=running_flow_id
        ),
        replace={running_flow_id: "ABCDEF"},
    )
    self.Check(
        "GetVfsRefreshOperationState",
        args=api_vfs_pb2.ApiGetVfsRefreshOperationStateArgs(
            client_id=client_id, operation_id=finished_flow_id
        ),
        replace={finished_flow_id: "ABCDEF"},
    )
    self.Check(
        "GetVfsRefreshOperationState",
        args=api_vfs_pb2.ApiGetVfsRefreshOperationStateArgs(
            client_id=client_id, operation_id=non_refresh_flow_id
        ),
        replace={non_refresh_flow_id: "ABCDEF"},
    )
    self.Check(
        "GetVfsRefreshOperationState",
        args=api_vfs_pb2.ApiGetVfsRefreshOperationStateArgs(
            client_id=client_id, operation_id=unknown_flow_id
        ),
        replace={unknown_flow_id: "ABCDEF"},
    )


class ApiUpdateVfsFileContentHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest
):
  """Regression test for ApiUpdateVfsFileContentHandler."""

  api_method = "UpdateVfsFileContent"
  handler = vfs_plugin.ApiUpdateVfsFileContentHandler

  def Run(self):
    client_id = self.SetupClient(0)
    self.file_path = "fs/os/c/bin/bash"

    fixture_test_lib.ClientFixture(client_id)

    def ReplaceFlowId():
      flows = data_store.REL_DB.ReadAllFlowObjects(client_id=client_id)
      return {flows[0].flow_id: "ABCDEF"}

    with test_lib.FakeTime(42):
      self.Check(
          "UpdateVfsFileContent",
          args=api_vfs_pb2.ApiUpdateVfsFileContentArgs(
              client_id=client_id, file_path=self.file_path
          ),
          replace=ReplaceFlowId,
      )


class ApiGetVfsFileContentUpdateStateHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest, vfs_plugin_test.VfsTestMixin
):
  """Regression test for ApiGetVfsFileContentUpdateStateHandler."""

  api_method = "GetVfsFileContentUpdateState"
  handler = vfs_plugin.ApiGetVfsFileContentUpdateStateHandler

  def Run(self):
    client_id = self.SetupClient(0)

    acl_test_lib.CreateUser(self.test_username)

    # Create a running mock refresh operation.
    running_flow_id = self.CreateMultiGetFileFlow(
        client_id, file_path="fs/os/c/bin/bash"
    )

    # Create a mock refresh operation and complete it.
    finished_flow_id = self.CreateMultiGetFileFlow(
        client_id, file_path="fs/os/c/bin/bash"
    )

    flow_base.TerminateFlow(client_id, finished_flow_id, reason="Fake Error")

    # Create an arbitrary flow to check on 404s.
    non_update_flow_id = flow.StartFlow(
        client_id=client_id, flow_cls=discovery.Interrogate
    )

    # Unknown flow ids should also cause 404s.
    unknown_flow_id = "F:12345678"

    # Check both operations.
    self.Check(
        "GetVfsFileContentUpdateState",
        args=api_vfs_pb2.ApiGetVfsFileContentUpdateStateArgs(
            client_id=client_id, operation_id=running_flow_id
        ),
        replace={running_flow_id: "ABCDEF"},
    )
    self.Check(
        "GetVfsFileContentUpdateState",
        args=api_vfs_pb2.ApiGetVfsFileContentUpdateStateArgs(
            client_id=client_id, operation_id=finished_flow_id
        ),
        replace={finished_flow_id: "ABCDEF"},
    )
    self.Check(
        "GetVfsFileContentUpdateState",
        args=api_vfs_pb2.ApiGetVfsFileContentUpdateStateArgs(
            client_id=client_id, operation_id=non_update_flow_id
        ),
        replace={non_update_flow_id: "ABCDEF"},
    )
    self.Check(
        "GetVfsFileContentUpdateState",
        args=api_vfs_pb2.ApiGetVfsFileContentUpdateStateArgs(
            client_id=client_id, operation_id=unknown_flow_id
        ),
        replace={unknown_flow_id: "ABCDEF"},
    )


class ApiGetVfsTimelineHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    vfs_plugin_test.VfsTimelineTestMixin,
):
  """Regression test for ApiGetVfsTimelineHandler."""

  api_method = "GetVfsTimeline"
  handler = vfs_plugin.ApiGetVfsTimelineHandler

  def Run(self):
    client_id = self.SetupTestTimeline()

    self.Check(
        "GetVfsTimeline",
        args=api_vfs_pb2.ApiGetVfsTimelineArgs(
            client_id=client_id, file_path=self.folder_path
        ),
    )


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
