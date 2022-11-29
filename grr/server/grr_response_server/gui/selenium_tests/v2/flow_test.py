#!/usr/bin/env python
import os

from absl import app

from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_server import artifact_registry
from grr_response_server import data_store
from grr_response_server import maintenance_utils
from grr_response_server import signed_binary_utils
from grr_response_server.flows import file
from grr_response_server.flows.general import administrative
from grr_response_server.flows.general import collectors
from grr_response_server.flows.general import memory
# Required for ApiListFlowDescriptorsHandler() to truly return all flow
# descriptors during testing.
from grr_response_server.flows.general import registry_init  # pylint: disable=unused-import
from grr_response_server.flows.general import timeline
from grr_response_server.gui import api_auth_manager
from grr_response_server.gui import api_call_context
from grr_response_server.gui import gui_test_lib
from grr_response_server.gui.api_plugins import flow as api_flow
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import test_lib


def _ListFlows(client_id: str, creator: str):
  handler = api_flow.ApiListFlowsHandler()
  return handler.Handle(
      api_flow.ApiListFlowsArgs(client_id=client_id, top_flows_only=True),
      context=api_call_context.ApiCallContext(username=creator)).items


def _ListScheduledFlows(client_id: str, creator: str):
  handler = api_flow.ApiListScheduledFlowsHandler()
  return handler.Handle(
      api_flow.ApiListScheduledFlowsArgs(client_id=client_id, creator=creator),
      context=api_call_context.ApiCallContext(username=creator)).scheduled_flows


class FlowCreationTest(gui_test_lib.GRRSeleniumTest):
  """Tests the generic flow creation and approval request UI."""

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)
    self.CreateUser('approvername')

  def _RequestApproval(self, reason: str, approver: str):
    self.Type('css=approval input[name=reason]', 'examplereason')
    self.Type(
        'css=approval .approvers input', 'approvername', end_with_enter=True)

    self.assertEmpty(self.ListClientApprovals())

    self.Click('css=approval button[type=submit]')

    self.WaitUntilContains('Request sent, waiting', self.GetText,
                           'css=approval')

    def ApprovalHasBeenRequested():
      approvals = self.ListClientApprovals()
      self.assertLessEqual(len(approvals), 1)
      return approvals[0] if len(approvals) == 1 else None

    return self.WaitUntil(ApprovalHasBeenRequested)

  def testCanRequestApprovalWithoutFlow(self):
    self.Open(f'/v2/clients/{self.client_id}')
    self.WaitUntilContains('No access', self.GetText, 'css=client-overview')

    approval = self._RequestApproval(
        reason='examplereason', approver='approvername')

    self.assertEqual(approval.reason, 'examplereason')
    self.assertEqual(approval.notified_users, ['approvername'])
    self.assertEqual(approval.subject.client_id, self.client_id)

  def testCanScheduleFlowWithoutApproval(self):
    self.Open(f'/v2/clients/{self.client_id}')
    self.WaitUntilContains('No access', self.GetText, 'css=client-overview')

    self.Click('css=flow-form button:contains("Collect files")')
    self.Click(
        'css=.mat-menu-panel button:contains("Collect files by search criteria")'
    )

    self.Type('css=flow-args-form app-glob-expression-input input', '/foo/test')

    self.assertEmpty(_ListScheduledFlows(self.client_id, self.test_username))

    self.Click('css=flow-form button:contains("Schedule")')

    self.WaitUntilContains('CollectMultipleFiles', self.GetText,
                           'css=scheduled-flow-list')
    self.WaitUntilContains('Pending approval', self.GetText,
                           'css=scheduled-flow-list')

    def GetFirstScheduledFlow():
      scheduled_flows = _ListScheduledFlows(self.client_id, self.test_username)
      self.assertLessEqual(len(scheduled_flows), 1)
      return scheduled_flows[0] if len(scheduled_flows) == 1 else None

    scheduled_flow = self.WaitUntil(GetFirstScheduledFlow)

    self.assertEqual(scheduled_flow.client_id, self.client_id)
    self.assertEqual(scheduled_flow.creator, self.test_username)
    self.assertEqual(scheduled_flow.flow_name, 'CollectMultipleFiles')
    self.assertEqual(scheduled_flow.flow_args.path_expressions, ['/foo/test'])
    self.assertFalse(scheduled_flow.error)

  def testApprovalGrantStartsScheduledFlow(self):
    self.testCanScheduleFlowWithoutApproval()

    approval = self._RequestApproval(
        reason='examplereason', approver='approvername')

    self.GrantClientApproval(
        client_id=self.client_id,
        requestor=self.test_username,
        approval_id=approval.id,
        approver='approvername')

    self.WaitUntilNot(self.GetVisibleElement, 'css=scheduled-flow-list')
    self.WaitUntilContains('All human flows', self.GetText, 'css=flow-list')
    self.WaitUntilContains('Collect multiple files', self.GetText,
                           'css=flow-details')
    self.WaitUntil(self.GetVisibleElement, 'css=flow-details .in-progress')

    self.assertEmpty(_ListScheduledFlows(self.client_id, self.test_username))
    self.assertLen(_ListFlows(self.client_id, self.test_username), 1)

  def testCanCreateFlowAfterGrantedApproval(self):
    self.Open(f'/v2/clients/{self.client_id}')
    self.WaitUntilContains('No access', self.GetText, 'css=client-overview')

    approval = self._RequestApproval(
        reason='examplereason', approver='approvername')
    self.GrantClientApproval(
        client_id=self.client_id,
        requestor=self.test_username,
        approval_id=approval.id,
        approver='approvername')

    self.WaitUntilContains('Access granted', self.GetText,
                           'css=client-overview')

    self.Click('css=flow-form button:contains("Collect files")')
    self.Click(
        'css=.mat-menu-panel button:contains("Collect files by search criteria")'
    )

    self.Type('css=flow-args-form app-glob-expression-input input', '/foo/test')

    self.assertEmpty(_ListScheduledFlows(self.client_id, self.test_username))

    self.Click('css=flow-form button:contains("Start")')

    self.WaitUntilContains('All human flows', self.GetText, 'css=flow-list')
    self.WaitUntilContains('Collect multiple files', self.GetText,
                           'css=flow-details')
    self.WaitUntil(self.GetVisibleElement, 'css=flow-details .in-progress')

    self.assertEmpty(_ListScheduledFlows(self.client_id, self.test_username))
    self.assertLen(_ListFlows(self.client_id, self.test_username), 1)

  def testCanDuplicateFlow(self):
    self.Open(f'/v2/clients/{self.client_id}')
    self.WaitUntilContains('No access', self.GetText, 'css=client-overview')

    approval = self._RequestApproval(
        reason='examplereason', approver='approvername')
    self.GrantClientApproval(
        client_id=self.client_id,
        requestor=self.test_username,
        approval_id=approval.id,
        approver='approvername')

    self.WaitUntilContains('Access granted', self.GetText,
                           'css=client-overview')

    self.Click('css=flow-form button:contains("Collect files")')
    self.Click(
        'css=.mat-menu-panel button:contains("Collect files by search criteria")'
    )
    self.Type('css=flow-args-form app-glob-expression-input input', '/foo/test')
    self.Click('css=flow-form button:contains("Start")')

    self.WaitUntilContains('/foo/test', self.GetText, 'css=flow-details')

    self.Click('css=flow-details button[aria-label="Flow menu"]')
    self.Click('css=.mat-menu-panel button:contains("Duplicate flow")')
    self.Click('css=flow-form button:contains("Start")')

    self.WaitUntilContains('/foo/test', self.GetText,
                           'css=flow-details:nth-of-type(1)')
    self.WaitUntilContains('/foo/test', self.GetText,
                           'css=flow-details:nth-of-type(2)')

  def testScheduleTimelineFlow(self):
    self.Open(f'/v2/clients/{self.client_id}')
    self.WaitUntilContains('No access', self.GetText, 'css=client-overview')

    self.Click('css=flow-form button:contains("Collect path timeline")')

    self.Type('css=flow-args-form input[name=root]', '/foo/test')

    self.Click('css=flow-form button:contains("Schedule")')

    def GetFirstScheduledFlow():
      scheduled_flows = _ListScheduledFlows(self.client_id, self.test_username)
      return scheduled_flows[0] if len(scheduled_flows) == 1 else None

    scheduled_flow = self.WaitUntil(GetFirstScheduledFlow)

    self.assertEqual(scheduled_flow.flow_name, timeline.TimelineFlow.__name__)
    self.assertEqual(scheduled_flow.flow_args.root, b'/foo/test')

  def testCollectMultipleFilesFlow(self):
    self.Open(f'/v2/clients/{self.client_id}')
    self.WaitUntilContains('No access', self.GetText, 'css=client-overview')

    self.Click('css=flow-form button:contains("Collect files")')
    self.Click(
        'css=.mat-menu-panel button:contains("Collect files by search criteria")'
    )

    self.Type(
        'css=flow-args-form ' +
        'app-glob-expression-input:nth-of-type(1) input', '/foo/firstpath')

    self.Click('css=flow-form button:contains("Add path expression")')
    self.Type(
        'css=flow-args-form ' +
        'app-glob-expression-input:nth-of-type(2) input', '/foo/secondpath')

    self.Click('css=flow-form button:contains("Literal match")')
    self.Type('css=flow-args-form input[name=literal]', 'literalinput')

    self.Click('css=flow-form button:contains("Regex match")')
    self.Type('css=flow-args-form input[name=regex]', 'regexinput')

    self.Click('css=flow-form button:contains("Modification time")')
    self.Type('css=flow-args-form [title="modification"] [name=minTime] input',
              '2000-01-01 11:00:00')
    self.Type('css=flow-args-form [title="modification"] [name=maxTime] input',
              '2000-01-02 22:00:00')

    self.Click('css=flow-form button:contains("Access time")')
    self.Type('css=flow-args-form [title=access] [name=minTime] input',
              '2000-02-01 11:00:00')
    self.Type('css=flow-args-form [title=access] [name=maxTime] input',
              '2000-02-02 22:00:00')

    self.Click('css=flow-form button:contains("Inode change time")')
    self.Type('css=flow-args-form [title="inode change"] [name=minTime] input',
              '2000-03-01 11:00:00')
    self.Type('css=flow-args-form [title="inode change"] [name=maxTime] input',
              '2000-03-02 22:00:00')

    self.Click('css=flow-form button:contains("File size")')
    self.Type('css=flow-args-form input[name=minFileSize]', '1 KiB')
    self.Type('css=flow-args-form input[name=maxFileSize]', '2 KiB')

    self.Click('css=flow-form button:contains("Extended file flags")')
    # Press 'X' once to only include files with flag FS_NOCOMP_FL.
    self.Click(
        'css=flow-form ext-flags-condition button .identifier:contains("X")')
    # Press 'u' twice to exclude files with flag FS_UNRM_FL.
    self.Click(
        'css=flow-form ext-flags-condition button .identifier:contains("u")')
    self.Click(
        'css=flow-form ext-flags-condition button .identifier:contains("u")')

    self.Click('css=flow-form button:contains("Schedule")')

    def GetFirstScheduledFlow():
      scheduled_flows = _ListScheduledFlows(self.client_id, self.test_username)
      return scheduled_flows[0] if len(scheduled_flows) == 1 else None

    scheduled_flow = self.WaitUntil(GetFirstScheduledFlow)
    args = scheduled_flow.flow_args

    self.assertEqual(scheduled_flow.flow_name,
                     file.CollectMultipleFiles.__name__)
    self.assertEqual(args.path_expressions,
                     ['/foo/firstpath', '/foo/secondpath'])
    self.assertEqual(
        args.modification_time.min_last_modified_time,
        rdfvalue.RDFDatetime.FromHumanReadable('2000-01-01 11:00:00'))
    self.assertEqual(
        args.modification_time.max_last_modified_time,
        rdfvalue.RDFDatetime.FromHumanReadable('2000-01-02 22:00:00'))
    self.assertEqual(
        args.access_time.min_last_access_time,
        rdfvalue.RDFDatetime.FromHumanReadable('2000-02-01 11:00:00'))
    self.assertEqual(
        args.access_time.max_last_access_time,
        rdfvalue.RDFDatetime.FromHumanReadable('2000-02-02 22:00:00'))
    self.assertEqual(
        args.inode_change_time.min_last_inode_change_time,
        rdfvalue.RDFDatetime.FromHumanReadable('2000-03-01 11:00:00'))
    self.assertEqual(
        args.inode_change_time.max_last_inode_change_time,
        rdfvalue.RDFDatetime.FromHumanReadable('2000-03-02 22:00:00'))
    self.assertEqual(args.size.min_file_size, 1024)
    self.assertEqual(args.size.max_file_size, 2048)
    self.assertEqual(args.ext_flags.linux_bits_set, 0x00000400)
    self.assertEqual(args.ext_flags.linux_bits_unset, 0x00000002)

    self.assertEqual(args.contents_regex_match.regex, b'regexinput')
    self.assertEqual(args.contents_literal_match.literal, b'literalinput')

  def _LoadTestArtifacts(self):
    artifact_registry.REGISTRY.ClearRegistry()
    test_artifacts_file = os.path.join(config.CONFIG['Test.data_dir'],
                                       'artifacts', 'test_artifacts.json')
    artifact_registry.REGISTRY.AddFileSource(test_artifacts_file)

  def testScheduleArtifactCollectorFlow(self):
    self._LoadTestArtifacts()
    self.Open(f'/v2/clients/{self.client_id}')
    self.WaitUntilContains('No access', self.GetText, 'css=client-overview')

    self.Click('css=flow-form button:contains("Collect forensic artifacts")')

    # Type whole artifact name except last letter into autocomplete.
    self.Type('css=flow-args-form input[name=artifactName]', 'FakeFileArtifac')

    self.Click('css=.mat-option:contains("FakeFileArtifact")')

    self.WaitUntilContains('Collects file', self.GetText, 'css=flow-args-form')
    self.WaitUntilContains('/notafile', self.GetText, 'css=flow-args-form')
    self.WaitUntilContains('/grr_response_test/test_data/numbers.txt',
                           self.GetText, 'css=flow-args-form')

    self.Click('css=flow-form button:contains("Schedule")')

    def GetFirstScheduledFlow():
      scheduled_flows = _ListScheduledFlows(self.client_id, self.test_username)
      return scheduled_flows[0] if len(scheduled_flows) == 1 else None

    scheduled_flow = self.WaitUntil(GetFirstScheduledFlow)

    self.assertEqual(scheduled_flow.flow_name,
                     collectors.ArtifactCollectorFlow.__name__)
    self.assertEqual(scheduled_flow.flow_args.artifact_list,
                     ['FakeFileArtifact'])

  def testScheduleArtifactCollectorFlowWithDefaultArtifacts(self):
    artifact_registry.REGISTRY.AddDefaultSources()
    self.assertLen(
        artifact_registry.REGISTRY.GetArtifacts(
            name_list=['LinuxHardwareInfo']), 1)

    self.Open(f'/v2/clients/{self.client_id}')
    self.WaitUntilContains('No access', self.GetText, 'css=client-overview')
    self.Click('css=flow-form button:contains("Collect forensic artifacts")')

    self.assertLen(
        artifact_registry.REGISTRY.GetArtifacts(
            name_list=['LinuxHardwareInfo']), 1)
    # Type whole artifact name except last letter into autocomplete.
    self.Type('css=flow-args-form input[name=artifactName]', 'LinuxHardwareInf')

    self.Click('css=.mat-option:contains("LinuxHardwareInfo")')
    self.Click('css=flow-form button:contains("Schedule")')

    def GetFirstScheduledFlow():
      scheduled_flows = _ListScheduledFlows(self.client_id, self.test_username)
      return scheduled_flows[0] if len(scheduled_flows) == 1 else None

    scheduled_flow = self.WaitUntil(GetFirstScheduledFlow)

    self.assertEqual(scheduled_flow.flow_name,
                     collectors.ArtifactCollectorFlow.__name__)
    self.assertEqual(scheduled_flow.flow_args.artifact_list,
                     ['LinuxHardwareInfo'])

  def _SetUpAdminUser(self):
    data_store.REL_DB.WriteGRRUser(
        self.test_username,
        user_type=rdf_objects.GRRUser.UserType.USER_TYPE_ADMIN)

  def testScheduleLaunchBinaryFlow(self):
    self._SetUpAdminUser()
    maintenance_utils.UploadSignedConfigBlob(
        b'foo',
        aff4_path=signed_binary_utils.GetAFF4ExecutablesRoot().Add(
            'windows/a.exe'))
    maintenance_utils.UploadSignedConfigBlob(
        b'foo',
        aff4_path=signed_binary_utils.GetAFF4ExecutablesRoot().Add(
            'windows/test.exe'))

    self.Open(f'/v2/clients/{self.client_id}')
    self.WaitUntilContains('No access', self.GetText, 'css=client-overview')

    self.Type(
        'css=flow-form input[name=flowSearchBox]',
        'binary',
        end_with_enter=True)
    self.Type(
        'css=flow-args-form input[name=binary]', 'test', end_with_enter=True)
    self.Type('css=flow-args-form input[name=commandLine]', '--foo --bar')

    self.Click('css=flow-form button:contains("Schedule")')

    def GetFirstScheduledFlow():
      scheduled_flows = _ListScheduledFlows(self.client_id, self.test_username)
      return scheduled_flows[0] if len(scheduled_flows) == 1 else None

    scheduled_flow = self.WaitUntil(GetFirstScheduledFlow)

    self.assertEqual(scheduled_flow.flow_name,
                     administrative.LaunchBinary.__name__)
    self.assertEqual(scheduled_flow.flow_args.binary,
                     'aff4:/config/executables/windows/test.exe')
    self.assertEqual(scheduled_flow.flow_args.command_line, '--foo --bar')

  def testScheduleLaunchExecutePythonHackFlow(self):
    self._SetUpAdminUser()
    maintenance_utils.UploadSignedConfigBlob(
        b'foo',
        aff4_path=signed_binary_utils.GetAFF4PythonHackRoot().Add(
            'windows/a.py'))
    maintenance_utils.UploadSignedConfigBlob(
        b'foo',
        aff4_path=signed_binary_utils.GetAFF4PythonHackRoot().Add(
            'windows/test.py'))

    self.Open(f'/v2/clients/{self.client_id}')
    self.WaitUntilContains('No access', self.GetText, 'css=client-overview')

    self.Type(
        'css=flow-form input[name=flowSearchBox]',
        'python',
        end_with_enter=True)
    self.Type(
        'css=flow-args-form input[name=hackName]', 'test', end_with_enter=True)

    self.Click('css=flow-args-form button:contains("Add argument")')

    self.Type('css=flow-args-form .key-input input', 'fookey')
    self.Type('css=flow-args-form .value-input input', 'foovalue')

    self.Click('css=flow-form button:contains("Schedule")')

    def GetFirstScheduledFlow():
      scheduled_flows = _ListScheduledFlows(self.client_id, self.test_username)
      return scheduled_flows[0] if len(scheduled_flows) == 1 else None

    scheduled_flow = self.WaitUntil(GetFirstScheduledFlow)

    self.assertEqual(scheduled_flow.flow_name,
                     administrative.ExecutePythonHack.__name__)
    self.assertEqual(scheduled_flow.flow_args.hack_name, 'windows/test.py')
    self.assertEqual(scheduled_flow.flow_args.py_args['fookey'], 'foovalue')

  def testDumpProcessMemoryFlow(self):
    self.Open(f'/v2/clients/{self.client_id}')
    self.WaitUntilContains('No access', self.GetText, 'css=client-overview')

    self.Type(
        'css=flow-form input[name=flowSearchBox]',
        'dump process',
        end_with_enter=True)

    self.Click('css=flow-form mat-button-toggle:contains("Name")')

    self.Type('css=flow-args-form input[name=processRegex]', 'python\\d')

    self.Click('css=flow-form mat-checkbox label:contains("shared")')

    self.Click('css=flow-form button:contains("Schedule")')

    def GetFirstScheduledFlow():
      scheduled_flows = _ListScheduledFlows(self.client_id, self.test_username)
      return scheduled_flows[0] if len(scheduled_flows) == 1 else None

    scheduled_flow = self.WaitUntil(GetFirstScheduledFlow)

    self.assertEqual(scheduled_flow.flow_name,
                     memory.DumpProcessMemory.__name__)
    self.assertEqual(scheduled_flow.flow_args.process_regex, 'python\\d')
    self.assertTrue(scheduled_flow.flow_args.skip_shared_regions)

  def testYaraProcessScanFlow(self):
    self.Open(f'/v2/clients/{self.client_id}')
    self.WaitUntilContains('No access', self.GetText, 'css=client-overview')

    self.Type(
        'css=flow-form input[name=flowSearchBox]', 'yara', end_with_enter=True)

    # ScrollIntoView fixes a mischievous Heisenbug, where Click() would succeed
    # but not actually trigger the toggle.
    self.ScrollIntoView('css=flow-form mat-button-toggle:contains("Name")')
    self.Click('css=flow-form mat-button-toggle:contains("Name")')

    self.Type('css=flow-args-form input[name=processRegex]', 'python\\d')

    self.Click('css=flow-form mat-checkbox label:contains("shared")')

    self.Click('css=flow-form button:contains("Schedule")')

    def GetFirstScheduledFlow():
      scheduled_flows = _ListScheduledFlows(self.client_id, self.test_username)
      return scheduled_flows[0] if len(scheduled_flows) == 1 else None

    scheduled_flow = self.WaitUntil(GetFirstScheduledFlow)

    self.assertEqual(scheduled_flow.flow_name, memory.YaraProcessScan.__name__)
    self.assertEqual(scheduled_flow.flow_args.process_regex, 'python\\d')
    self.assertTrue(scheduled_flow.flow_args.skip_shared_regions)


class FlowCreationTestWithApprovalsDisabled(gui_test_lib.GRRSeleniumTest):
  """Tests the generic flow creation when approvals are disabled."""

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)

  def InstallACLChecks(self):
    # This class purposefully does not install ACL checks.
    api_auth_manager.InitializeApiAuthManager()

  def testCanCreateFlowWithApprovalsDisabled(self):
    self.Open(f'/v2/clients/{self.client_id}')

    self.WaitUntil(self.GetVisibleElement,
                   'css=client-overview .fqdn-chips online-chip')
    self.WaitUntilNot(self.GetVisibleElement,
                      'css=client-overview .fqdn-chips app-approval-chip')

    self.Click('css=flow-form button:contains("Collect files")')
    self.Click(
        'css=.mat-menu-panel button:contains("Collect files by search criteria")'
    )

    self.Type('css=flow-args-form app-glob-expression-input input', '/foo/test')

    self.assertEmpty(_ListFlows(self.client_id, self.test_username))

    self.Click('css=flow-form button:contains("Start")')

    self.WaitUntilContains('All human flows', self.GetText, 'css=flow-list')
    self.WaitUntilContains('Collect multiple files', self.GetText,
                           'css=flow-details')
    self.WaitUntil(self.GetVisibleElement, 'css=flow-details .in-progress')

    self.assertEmpty(_ListScheduledFlows(self.client_id, self.test_username))

    flows = _ListFlows(self.client_id, self.test_username)
    self.assertLen(flows, 1)

    self.assertEqual(flows[0].client_id, self.client_id)
    self.assertEqual(flows[0].creator, self.test_username)
    self.assertEqual(flows[0].name, 'CollectMultipleFiles')
    self.assertEqual(flows[0].args.path_expressions, ['/foo/test'])


if __name__ == '__main__':
  app.run(test_lib.main)
