#!/usr/bin/env python
from typing import Optional

from absl import app

from google.protobuf import any_pb2
from google.protobuf import message
from grr_response_core.lib.rdfvalues import artifacts as rdf_artifacts
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_proto import api_call_router_pb2
from grr_response_proto import flows_pb2
from grr_response_proto import timeline_pb2
from grr_response_proto.api import flow_pb2 as api_flow_pb2
from grr_response_proto.api import timeline_pb2 as api_timeline_pb2
from grr_response_server import access_control
from grr_response_server import flow_base
from grr_response_server.flows.general import collectors
from grr_response_server.flows.general import file_finder
from grr_response_server.flows.general import timeline
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_call_robot_router as rr
from grr.test_lib import acl_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class AnotherFileFinder(flow_base.FlowBase):
  args_type = rdf_file_finder.FileFinderArgs


class AnotherArtifactCollector(flow_base.FlowBase):
  args_type = rdf_artifacts.ArtifactCollectorFlowArgs


class ApiRobotCreateFlowHandlerTest(test_lib.GRRBaseTest):
  """Tests for ApiRobotCreateFlowHandler."""

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)
    self.context = api_call_context.ApiCallContext("test")

  def testPassesFlowArgsThroughIfNoOverridesSpecified(self):
    h = rr.ApiRobotCreateFlowHandler()

    args = api_flow_pb2.ApiCreateFlowArgs(client_id=self.client_id)
    args.flow.name = file_finder.FileFinder.__name__
    args.flow.args.Pack(flows_pb2.FileFinderArgs(paths=["foo"]))

    f = h.Handle(args=args, context=self.context)
    flow_args = flows_pb2.FileFinderArgs()
    f.args.Unpack(flow_args)
    self.assertEqual(flow_args.paths, ["foo"])

  def testOverridesFlowNameIfOverrideArgIsSpecified(self):
    h = rr.ApiRobotCreateFlowHandler(
        override_flow_name=AnotherFileFinder.__name__
    )  # pylint: disable=undefined-variable

    args = api_flow_pb2.ApiCreateFlowArgs(client_id=self.client_id)
    args.flow.name = file_finder.FileFinder.__name__
    args.flow.args.Pack(flows_pb2.FileFinderArgs(paths=["foo"]))

    f = h.Handle(args=args, context=self.context)
    self.assertEqual(f.name, AnotherFileFinder.__name__)  # pylint: disable=undefined-variable

  def testOverridesFlowArgsThroughIfOverridesSpecified(self):
    override_flow_args = any_pb2.Any()
    override_flow_args.Pack(flows_pb2.FileFinderArgs(paths=["bar"]))
    h = rr.ApiRobotCreateFlowHandler(override_flow_args=override_flow_args)

    args = api_flow_pb2.ApiCreateFlowArgs(client_id=self.client_id)
    args.flow.name = file_finder.FileFinder.__name__
    args.flow.args.Pack(flows_pb2.FileFinderArgs(paths=["foo"]))

    f = h.Handle(args=args, context=self.context)
    flow_args = flows_pb2.FileFinderArgs()
    f.args.Unpack(flow_args)
    self.assertEqual(flow_args.paths, ["bar"])


class ApiCallRobotRouterTest(acl_test_lib.AclTestMixin, test_lib.GRRBaseTest):
  """Tests for ApiCallRobotRouter."""

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)
    self.context = api_call_context.ApiCallContext("test")
    self.another_username = "someotherguy"
    self.CreateUser(self.another_username)

  def testSearchClientsIsDisabledByDefault(self):
    router = rr.ApiCallRobotRouter(
        params=api_call_router_pb2.ApiCallRobotRouterParams()
    )
    with self.assertRaises(access_control.UnauthorizedAccess):
      router.SearchClients(None, context=self.context)

  def testSearchClientsWorksWhenExplicitlyEnabled(self):
    router = rr.ApiCallRobotRouter(
        params=api_call_router_pb2.ApiCallRobotRouterParams(
            search_clients=api_call_router_pb2.RobotRouterSearchClientsParams(
                enabled=True
            )
        )
    )
    router.SearchClients(None, context=self.context)

  def testCreateFlowRaisesIfClientIdNotSpecified(self):
    router = rr.ApiCallRobotRouter(
        params=api_call_router_pb2.ApiCallRobotRouterParams()
    )
    with self.assertRaises(ValueError):
      router.CreateFlow(api_flow_pb2.ApiCreateFlowArgs(), context=self.context)

  def testCreateFlowIsDisabledByDefault(self):
    router = rr.ApiCallRobotRouter(
        params=api_call_router_pb2.ApiCallRobotRouterParams()
    )
    with self.assertRaises(access_control.UnauthorizedAccess):
      router.CreateFlow(
          api_flow_pb2.ApiCreateFlowArgs(client_id=self.client_id),
          context=self.context,
      )

  def testFileFinderWorksWhenEnabledAndArgumentsAreCorrect(self):
    router = None

    def Check(path):
      flow = api_flow_pb2.ApiFlow(
          name=file_finder.FileFinder.__name__,
      )
      flow.args.Pack(flows_pb2.FileFinderArgs(paths=[path]))
      router.CreateFlow(
          api_flow_pb2.ApiCreateFlowArgs(
              flow=flow,
              client_id=self.client_id,
          ),
          context=self.context,
      )

    router = rr.ApiCallRobotRouter(
        params=api_call_router_pb2.ApiCallRobotRouterParams(
            file_finder_flow=api_call_router_pb2.RobotRouterFileFinderFlowParams(
                enabled=True
            )
        )
    )
    Check("/foo/bar")

    router = rr.ApiCallRobotRouter(
        params=api_call_router_pb2.ApiCallRobotRouterParams(
            file_finder_flow=api_call_router_pb2.RobotRouterFileFinderFlowParams(
                enabled=True, globs_allowed=True
            )
        )
    )
    Check("/foo/bar/**/*")

    router = rr.ApiCallRobotRouter(
        params=api_call_router_pb2.ApiCallRobotRouterParams(
            file_finder_flow=api_call_router_pb2.RobotRouterFileFinderFlowParams(
                enabled=True, interpolations_allowed=True
            )
        )
    )
    Check("%%users.homedir%%/foo")

    router = rr.ApiCallRobotRouter(
        params=api_call_router_pb2.ApiCallRobotRouterParams(
            file_finder_flow=api_call_router_pb2.RobotRouterFileFinderFlowParams(
                enabled=True, globs_allowed=True, interpolations_allowed=True
            )
        )
    )
    Check("%%users.homedir%%/foo/**/*")

  def testFileFinderRaisesWhenEnabledButArgumentsNotCorrect(self):
    router = None

    def Check(path):
      with self.assertRaises(access_control.UnauthorizedAccess):
        flow = api_flow_pb2.ApiFlow(
            name=file_finder.FileFinder.__name__,
        )
        flow.args.Pack(flows_pb2.FileFinderArgs(paths=[path]))
        router.CreateFlow(
            api_flow_pb2.ApiCreateFlowArgs(
                flow=flow,
                client_id=self.client_id,
            ),
            context=self.context,
        )

    router = rr.ApiCallRobotRouter(
        params=api_call_router_pb2.ApiCallRobotRouterParams(
            file_finder_flow=api_call_router_pb2.RobotRouterFileFinderFlowParams(
                enabled=True
            )
        )
    )
    Check("/foo/bar/**/*")

    router = rr.ApiCallRobotRouter(
        params=api_call_router_pb2.ApiCallRobotRouterParams(
            file_finder_flow=api_call_router_pb2.RobotRouterFileFinderFlowParams(
                enabled=True
            )
        )
    )
    Check("%%users.homedir%%/foo")

  def testFileFinderFlowNameCanBeOverridden(self):
    router = rr.ApiCallRobotRouter(
        params=api_call_router_pb2.ApiCallRobotRouterParams(
            file_finder_flow=api_call_router_pb2.RobotRouterFileFinderFlowParams(
                enabled=True, file_finder_flow_name=AnotherFileFinder.__name__
            )
        )
    )  # pylint: disable=undefined-variable

    handler = router.CreateFlow(
        api_flow_pb2.ApiCreateFlowArgs(
            flow=api_flow_pb2.ApiFlow(name=AnotherFileFinder.__name__),  # pylint: disable=undefined-variable
            client_id=self.client_id,
        ),
        context=self.context,
    )

    self.assertEqual(handler.override_flow_name, AnotherFileFinder.__name__)  # pylint: disable=undefined-variable

  def testOverriddenFileFinderFlowCanBeCreatedUsingOriginalFileFinderName(self):
    router = rr.ApiCallRobotRouter(
        params=api_call_router_pb2.ApiCallRobotRouterParams(
            file_finder_flow=api_call_router_pb2.RobotRouterFileFinderFlowParams(
                enabled=True, file_finder_flow_name=AnotherFileFinder.__name__
            )
        )
    )  # pylint: disable=undefined-variable

    handler = router.CreateFlow(
        api_flow_pb2.ApiCreateFlowArgs(
            flow=api_flow_pb2.ApiFlow(name=file_finder.FileFinder.__name__),
            client_id=self.client_id,
        ),
        context=self.context,
    )

    self.assertEqual(handler.override_flow_name, AnotherFileFinder.__name__)  # pylint: disable=undefined-variable

  def testFileFinderHashMaxFileSizeCanBeOverridden(self):
    router = rr.ApiCallRobotRouter(
        params=api_call_router_pb2.ApiCallRobotRouterParams(
            file_finder_flow=api_call_router_pb2.RobotRouterFileFinderFlowParams(
                enabled=True, max_file_size=42
            )
        )
    )

    ha = flows_pb2.FileFinderHashActionOptions()
    ha.max_size = 80
    ha.oversized_file_policy = (
        flows_pb2.FileFinderHashActionOptions.OversizedFilePolicy.HASH_TRUNCATED
    )

    path = "/foo/bar"
    flow = api_flow_pb2.ApiFlow(
        name=file_finder.FileFinder.__name__,
    )
    flow.args.Pack(
        flows_pb2.FileFinderArgs(
            paths=[path],
            action=flows_pb2.FileFinderAction(
                action_type=flows_pb2.FileFinderAction.Action.HASH,
                hash=ha,
            ),
        )
    )
    handler = router.CreateFlow(
        api_flow_pb2.ApiCreateFlowArgs(
            flow=flow,
            client_id=self.client_id,
        ),
        context=self.context,
    )

    override_flow_args = flows_pb2.FileFinderArgs()
    handler.override_flow_args.Unpack(override_flow_args)
    ha = override_flow_args.action.hash
    self.assertEqual(
        ha.oversized_file_policy,
        flows_pb2.FileFinderHashActionOptions.OversizedFilePolicy.SKIP,
    )
    self.assertEqual(ha.max_size, 42)

  def testFileFinderDownloadMaxFileSizeCanBeOverridden(self):
    router = rr.ApiCallRobotRouter(
        params=api_call_router_pb2.ApiCallRobotRouterParams(
            file_finder_flow=api_call_router_pb2.RobotRouterFileFinderFlowParams(
                enabled=True, max_file_size=42
            )
        )
    )

    da = flows_pb2.FileFinderDownloadActionOptions()
    da.max_size = 80
    da.oversized_file_policy = (
        flows_pb2.FileFinderDownloadActionOptions.OversizedFilePolicy.DOWNLOAD_TRUNCATED
    )

    path = "/foo/bar"
    flow = api_flow_pb2.ApiFlow(
        name=file_finder.FileFinder.__name__,
    )
    flow.args.Pack(
        flows_pb2.FileFinderArgs(
            paths=[path],
            action=flows_pb2.FileFinderAction(
                action_type=flows_pb2.FileFinderAction.Action.DOWNLOAD,
                download=da,
            ),
        )
    )
    handler = router.CreateFlow(
        api_flow_pb2.ApiCreateFlowArgs(
            flow=flow,
            client_id=self.client_id,
        ),
        context=self.context,
    )

    override_flow_args = flows_pb2.FileFinderArgs()
    handler.override_flow_args.Unpack(override_flow_args)
    override_da = override_flow_args.action.download
    self.assertEqual(
        override_da.oversized_file_policy,
        flows_pb2.FileFinderHashActionOptions.OversizedFilePolicy.SKIP,
    )
    self.assertEqual(override_da.max_size, 42)

  def testArtifactCollectorWorksWhenEnabledAndArgumentsAreCorrect(self):
    router = None

    def Check(artifacts):
      flow = api_flow_pb2.ApiFlow(
          name=collectors.ArtifactCollectorFlow.__name__,
      )
      flow.args.Pack(
          flows_pb2.ArtifactCollectorFlowArgs(artifact_list=artifacts)
      )
      router.CreateFlow(
          api_flow_pb2.ApiCreateFlowArgs(
              flow=flow,
              client_id=self.client_id,
          ),
          context=self.context,
      )

    router = rr.ApiCallRobotRouter(
        params=api_call_router_pb2.ApiCallRobotRouterParams(
            artifact_collector_flow=api_call_router_pb2.RobotRouterArtifactCollectorFlowParams(
                enabled=True
            )
        )
    )
    Check([])

    router = rr.ApiCallRobotRouter(
        params=api_call_router_pb2.ApiCallRobotRouterParams(
            artifact_collector_flow=api_call_router_pb2.RobotRouterArtifactCollectorFlowParams(
                enabled=True, allow_artifacts=["foo"]
            )
        )
    )
    Check(["foo"])

    router = rr.ApiCallRobotRouter(
        params=api_call_router_pb2.ApiCallRobotRouterParams(
            artifact_collector_flow=api_call_router_pb2.RobotRouterArtifactCollectorFlowParams(
                enabled=True, allow_artifacts=["foo", "bar", "blah"]
            )
        )
    )
    Check(["foo", "blah"])

  def testTimelineFlowDisabledByDefault(self):
    router = rr.ApiCallRobotRouter(
        params=api_call_router_pb2.ApiCallRobotRouterParams()
    )
    with self.assertRaises(access_control.UnauthorizedAccess):
      flow = api_flow_pb2.ApiFlow(
          name=timeline.TimelineFlow.__name__,
      )
      flow.args.Pack(timeline_pb2.TimelineArgs())
      router.CreateFlow(
          api_flow_pb2.ApiCreateFlowArgs(
              flow=flow,
              client_id=self.client_id,
          ),
          context=self.context,
      )

  def testTimelineFlowWorksWhenEnabled(self):
    router = rr.ApiCallRobotRouter(
        params=api_call_router_pb2.ApiCallRobotRouterParams(
            timeline_flow=api_call_router_pb2.RobotRouterTimelineFlowParams(
                enabled=True
            )
        )
    )
    flow = api_flow_pb2.ApiFlow(
        name=timeline.TimelineFlow.__name__,
    )
    flow.args.Pack(timeline_pb2.TimelineArgs())
    router.CreateFlow(
        api_flow_pb2.ApiCreateFlowArgs(
            flow=flow,
            client_id=self.client_id,
        ),
        context=self.context,
    )

  def testGetCollectedTimelineDisabledByDefault(self):
    router = rr.ApiCallRobotRouter(
        params=api_call_router_pb2.ApiCallRobotRouterParams()
    )
    with self.assertRaises(access_control.UnauthorizedAccess):
      router.GetCollectedTimeline(None, context=self.context)

  def testGetCollectedTimelineRaisesIfFlowWasNotCreatedBySameUser(self):
    flow_id = flow_test_lib.StartFlow(
        timeline.TimelineFlow, self.client_id, creator=self.another_username
    )

    router = rr.ApiCallRobotRouter(
        params=api_call_router_pb2.ApiCallRobotRouterParams(
            get_collected_timeline=api_call_router_pb2.RobotRouterGetCollectedTimelineParams(
                enabled=True
            )
        )
    )
    with self.assertRaises(access_control.UnauthorizedAccess):
      router.GetCollectedTimeline(
          api_timeline_pb2.ApiGetCollectedTimelineArgs(
              client_id=self.client_id, flow_id=flow_id
          ),
          context=self.context,
      )

  def testArtifactCollectorRaisesWhenEnabledButArgumentsNotCorrect(self):
    router = None

    def Check(artifacts):
      with self.assertRaises(access_control.UnauthorizedAccess):
        flow = api_flow_pb2.ApiFlow(
            name=collectors.ArtifactCollectorFlow.__name__,
        )
        flow.args.Pack(
            flows_pb2.ArtifactCollectorFlowArgs(artifact_list=artifacts)
        )
        router.CreateFlow(
            api_flow_pb2.ApiCreateFlowArgs(
                flow=flow,
                client_id=self.client_id,
            ),
            context=self.context,
        )

    router = rr.ApiCallRobotRouter(
        params=api_call_router_pb2.ApiCallRobotRouterParams(
            artifact_collector_flow=api_call_router_pb2.RobotRouterArtifactCollectorFlowParams(
                enabled=True
            )
        )
    )
    Check(["foo"])

    router = rr.ApiCallRobotRouter(
        params=api_call_router_pb2.ApiCallRobotRouterParams(
            artifact_collector_flow=api_call_router_pb2.RobotRouterArtifactCollectorFlowParams(
                enabled=True, allow_artifacts=["bar", "blah"]
            )
        )
    )
    Check(["foo", "bar"])

  def testArtifactCollectorFlowNameCanBeOverridden(self):
    router = rr.ApiCallRobotRouter(
        params=api_call_router_pb2.ApiCallRobotRouterParams(
            artifact_collector_flow=api_call_router_pb2.RobotRouterArtifactCollectorFlowParams(
                enabled=True,
                artifact_collector_flow_name=AnotherArtifactCollector.__name__,
            )
        )
    )  # pylint: disable=undefined-variable
    handler = router.CreateFlow(
        api_flow_pb2.ApiCreateFlowArgs(
            flow=api_flow_pb2.ApiFlow(name=AnotherArtifactCollector.__name__),  # pylint: disable=undefined-variable
            client_id=self.client_id,
        ),
        context=self.context,
    )

    self.assertEqual(
        handler.override_flow_name, AnotherArtifactCollector.__name__
    )  # pylint: disable=undefined-variable

  def testOverriddenArtifactCollectorFlowCanBeCreatedUsingOriginalName(self):
    router = rr.ApiCallRobotRouter(
        params=api_call_router_pb2.ApiCallRobotRouterParams(
            artifact_collector_flow=api_call_router_pb2.RobotRouterArtifactCollectorFlowParams(
                enabled=True,
                artifact_collector_flow_name=AnotherArtifactCollector.__name__,
            )
        )
    )  # pylint: disable=undefined-variable

    handler = router.CreateFlow(
        api_flow_pb2.ApiCreateFlowArgs(
            flow=api_flow_pb2.ApiFlow(
                name=collectors.ArtifactCollectorFlow.__name__
            ),
            client_id=self.client_id,
        ),
        context=self.context,
    )

    self.assertEqual(
        handler.override_flow_name, AnotherArtifactCollector.__name__
    )  # pylint: disable=undefined-variable

  def testOnlyFileFinderAndArtifactCollectorFlowsAreAllowed(self):
    router = rr.ApiCallRobotRouter(
        params=api_call_router_pb2.ApiCallRobotRouterParams(
            file_finder_flow=api_call_router_pb2.RobotRouterFileFinderFlowParams(
                enabled=True
            ),
            artifact_collector_flow=api_call_router_pb2.RobotRouterArtifactCollectorFlowParams(
                enabled=True
            ),
        )
    )

    with self.assertRaises(access_control.UnauthorizedAccess):
      router.CreateFlow(
          api_flow_pb2.ApiCreateFlowArgs(
              flow=api_flow_pb2.ApiFlow(name=flow_test_lib.BrokenFlow.__name__),
              client_id=self.client_id,
          ),
          context=self.context,
      )

  def _CreateFlowWithRobotId(
      self,
      flow_name: Optional[str] = None,
      flow_args: Optional[message.Message] = None,
  ):
    flow_name = flow_name or file_finder.FileFinder.__name__

    handler = rr.ApiRobotCreateFlowHandler()

    api_flow_args = api_flow_pb2.ApiCreateFlowArgs()
    api_flow_args.client_id = self.client_id
    if flow_name:
      api_flow_args.flow.name = flow_name
    if flow_args:
      api_flow_args.flow.args.Pack(flow_args)

    flow_result = handler.Handle(
        args=api_flow_args,
        context=self.context,
    )
    return flow_result.flow_id

  def testGetFlowIsDisabledByDefault(self):
    router = rr.ApiCallRobotRouter(
        params=api_call_router_pb2.ApiCallRobotRouterParams()
    )
    with self.assertRaises(access_control.UnauthorizedAccess):
      router.GetFlow(None, context=self.context)

  def testGetFlowRaisesIfFlowWasNotCreatedBySameUser(self):
    flow_id = flow_test_lib.StartFlow(
        file_finder.FileFinder, self.client_id, creator=self.another_username
    )

    router = rr.ApiCallRobotRouter(
        params=api_call_router_pb2.ApiCallRobotRouterParams(
            get_flow=api_call_router_pb2.RobotRouterGetFlowParams(enabled=True)
        )
    )
    with self.assertRaises(access_control.UnauthorizedAccess):
      router.GetFlow(
          api_flow_pb2.ApiGetFlowArgs(
              client_id=self.client_id, flow_id=flow_id
          ),
          context=self.context,
      )

  def testGetFlowWorksIfFlowWasCreatedBySameUser(self):
    flow_id = self._CreateFlowWithRobotId()
    router = rr.ApiCallRobotRouter(
        params=api_call_router_pb2.ApiCallRobotRouterParams(
            get_flow=api_call_router_pb2.RobotRouterGetFlowParams(enabled=True)
        )
    )
    router.GetFlow(
        api_flow_pb2.ApiGetFlowArgs(client_id=self.client_id, flow_id=flow_id),
        context=self.context,
    )

  def testListFlowResultsIsDisabledByDefault(self):
    router = rr.ApiCallRobotRouter(
        params=api_call_router_pb2.ApiCallRobotRouterParams()
    )
    with self.assertRaises(access_control.UnauthorizedAccess):
      router.ListFlowResults(None, context=self.context)

  def testListFlowResultsRaisesIfFlowWasNotCreatedBySameUser(self):
    flow_id = flow_test_lib.StartFlow(
        file_finder.FileFinder, self.client_id, creator=self.another_username
    )

    router = rr.ApiCallRobotRouter(
        params=api_call_router_pb2.ApiCallRobotRouterParams(
            list_flow_results=api_call_router_pb2.RobotRouterListFlowResultsParams(
                enabled=True
            )
        )
    )
    with self.assertRaises(access_control.UnauthorizedAccess):
      router.ListFlowResults(
          api_flow_pb2.ApiListFlowResultsArgs(
              client_id=self.client_id, flow_id=flow_id
          ),
          context=self.context,
      )

  def testListFlowResultsWorksIfFlowWasCreatedBySameUser(self):
    flow_id = self._CreateFlowWithRobotId()
    router = rr.ApiCallRobotRouter(
        params=api_call_router_pb2.ApiCallRobotRouterParams(
            list_flow_results=api_call_router_pb2.RobotRouterListFlowResultsParams(
                enabled=True
            )
        )
    )
    router.ListFlowResults(
        api_flow_pb2.ApiListFlowResultsArgs(
            client_id=self.client_id, flow_id=flow_id
        ),
        context=self.context,
    )

  def testListFlowLogsIsDisabledByDefault(self):
    router = rr.ApiCallRobotRouter(
        params=api_call_router_pb2.ApiCallRobotRouterParams()
    )
    with self.assertRaises(access_control.UnauthorizedAccess):
      router.ListFlowLogs(None, context=self.context)

  def testListFlowLogsRaisesIfFlowWasNotCreatedBySameUser(self):
    flow_id = flow_test_lib.StartFlow(
        file_finder.FileFinder, self.client_id, creator=self.another_username
    )

    router = rr.ApiCallRobotRouter(
        params=api_call_router_pb2.ApiCallRobotRouterParams(
            list_flow_logs=api_call_router_pb2.RobotRouterListFlowLogsParams(
                enabled=True
            )
        )
    )
    with self.assertRaises(access_control.UnauthorizedAccess):
      router.ListFlowLogs(
          api_flow_pb2.ApiListFlowLogsArgs(
              client_id=self.client_id, flow_id=flow_id
          ),
          context=self.context,
      )

  def testListFlowLogsWorksIfFlowWasCreatedBySameUser(self):
    flow_id = self._CreateFlowWithRobotId()
    router = rr.ApiCallRobotRouter(
        params=api_call_router_pb2.ApiCallRobotRouterParams(
            list_flow_logs=api_call_router_pb2.RobotRouterListFlowLogsParams(
                enabled=True
            )
        )
    )
    router.ListFlowLogs(
        api_flow_pb2.ApiListFlowLogsArgs(
            client_id=self.client_id, flow_id=flow_id
        ),
        context=self.context,
    )

  def testGetFileBlobIsDisabledByDefault(self):
    router = rr.ApiCallRobotRouter(
        params=api_call_router_pb2.ApiCallRobotRouterParams()
    )
    with self.assertRaises(access_control.UnauthorizedAccess):
      router.GetFileBlob(None, context=self.context)

  def testGetFlowFilesArchiveIsDisabledByDefault(self):
    router = rr.ApiCallRobotRouter(
        params=api_call_router_pb2.ApiCallRobotRouterParams()
    )
    with self.assertRaises(access_control.UnauthorizedAccess):
      router.GetFlowFilesArchive(None, context=self.context)

  def testFlowFilesArchiveRaisesIfFlowWasNotCreatedBySameUser(self):
    flow_id = flow_test_lib.StartFlow(
        file_finder.FileFinder, self.client_id, creator=self.another_username
    )

    router = rr.ApiCallRobotRouter(
        params=api_call_router_pb2.ApiCallRobotRouterParams()
    )
    with self.assertRaises(access_control.UnauthorizedAccess):
      router.GetFlowFilesArchive(
          api_flow_pb2.ApiGetFlowFilesArchiveArgs(
              client_id=self.client_id, flow_id=flow_id
          ),
          context=self.context,
      )

  def testGetFlowFilesArchiveWorksIfFlowWasCreatedBySameUser(self):
    flow_id = self._CreateFlowWithRobotId()
    router = rr.ApiCallRobotRouter(
        params=api_call_router_pb2.ApiCallRobotRouterParams(
            get_flow_files_archive=api_call_router_pb2.RobotRouterGetFlowFilesArchiveParams(
                enabled=True
            )
        )
    )
    router.GetFlowFilesArchive(
        api_flow_pb2.ApiGetFlowFilesArchiveArgs(
            client_id=self.client_id, flow_id=flow_id
        ),
        context=self.context,
    )

  def testGetFlowFilesArchiveReturnsLimitedHandler(self):
    flow_id = self._CreateFlowWithRobotId()
    router = rr.ApiCallRobotRouter(
        params=api_call_router_pb2.ApiCallRobotRouterParams(
            get_flow_files_archive=api_call_router_pb2.RobotRouterGetFlowFilesArchiveParams(
                enabled=True,
                exclude_path_globs=["**/*.txt"],
                include_only_path_globs=["foo/*", "bar/*"],
            )
        )
    )
    handler = router.GetFlowFilesArchive(
        api_flow_pb2.ApiGetFlowFilesArchiveArgs(
            client_id=self.client_id, flow_id=flow_id
        ),
        context=self.context,
    )
    self.assertEqual(handler.exclude_path_globs, ["**/*.txt"])
    self.assertEqual(handler.include_only_path_globs, ["foo/*", "bar/*"])

  def testGetFlowFilesArchiveReturnsNonLimitedHandlerForArtifactsWhenNeeded(
      self,
  ):
    router = rr.ApiCallRobotRouter(
        params=api_call_router_pb2.ApiCallRobotRouterParams(
            artifact_collector_flow=api_call_router_pb2.RobotRouterArtifactCollectorFlowParams(
                artifact_collector_flow_name=AnotherArtifactCollector.__name__
            ),  # pylint: disable=undefined-variable
            get_flow_files_archive=api_call_router_pb2.RobotRouterGetFlowFilesArchiveParams(
                enabled=True,
                skip_glob_checks_for_artifact_collector=True,
                exclude_path_globs=["**/*.txt"],
                include_only_path_globs=["foo/*", "bar/*"],
            ),
        )
    )

    flow_id = self._CreateFlowWithRobotId()
    handler = router.GetFlowFilesArchive(
        api_flow_pb2.ApiGetFlowFilesArchiveArgs(
            client_id=self.client_id, flow_id=flow_id
        ),
        context=self.context,
    )
    self.assertEqual(handler.exclude_path_globs, ["**/*.txt"])
    self.assertEqual(handler.include_only_path_globs, ["foo/*", "bar/*"])

    flow_id = self._CreateFlowWithRobotId(
        flow_name=AnotherArtifactCollector.__name__,  # pylint: disable=undefined-variable
        flow_args=flows_pb2.ArtifactCollectorFlowArgs(artifact_list=["Foo"]),
    )
    handler = router.GetFlowFilesArchive(
        api_flow_pb2.ApiGetFlowFilesArchiveArgs(
            client_id=self.client_id, flow_id=flow_id
        ),
        context=self.context,
    )
    self.assertIsNone(handler.exclude_path_globs)
    self.assertIsNone(handler.include_only_path_globs)

  IMPLEMENTED_METHODS = [
      "SearchClients",
      "CreateFlow",
      "GetFlow",
      "ListFlowResults",
      "ListFlowLogs",
      "GetFlowFilesArchive",
      # This single reflection method is needed for API libraries to work
      # correctly.
      "ListApiMethods",
      "GetOpenApiDescription",
      # TODO(user): Remove methods below as soon as they are deprecated
      # in favor of the methods above.
      "StartRobotGetFilesOperation",
      "GetRobotGetFilesOperationState",
      "GetCollectedTimeline",
      "GetFileBlob",
  ]

  def testAllOtherMethodsAreNotImplemented(self):
    router = rr.ApiCallRobotRouter(
        params=api_call_router_pb2.ApiCallRobotRouterParams()
    )

    unchecked_methods = set(
        router.__class__.GetAnnotatedMethods().keys()
    ) - set(self.IMPLEMENTED_METHODS)
    self.assertTrue(unchecked_methods)

    for method_name in unchecked_methods:
      with self.assertRaises(NotImplementedError):
        getattr(router, method_name)(None, context=self.context)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
