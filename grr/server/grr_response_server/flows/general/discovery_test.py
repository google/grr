#!/usr/bin/env python
import binascii
from collections.abc import Iterator
import datetime
import ipaddress
import os
import platform
import socket
from unittest import mock

from absl import app

from google.protobuf import any_pb2
from grr_response_client.client_actions import admin
from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import mig_client_action
from grr_response_core.lib.rdfvalues import mig_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import knowledge_base_pb2
from grr_response_proto import objects_pb2
from grr_response_proto import sysinfo_pb2
from grr_response_server import action_registry
from grr_response_server import artifact_registry
from grr_response_server import client_index
from grr_response_server import data_store
from grr_response_server import events
from grr_response_server import fleetspeak_utils
from grr_response_server import flow_responses
from grr_response_server import server_stubs
from grr_response_server.databases import db as abstract_db
from grr_response_server.databases import db_test_utils
from grr_response_server.flows.general import cloud
from grr_response_server.flows.general import discovery
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import mig_objects
from grr.test_lib import acl_test_lib
from grr.test_lib import action_mocks
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import notification_test_lib
from grr.test_lib import rrg_test_lib
from grr.test_lib import stats_test_lib
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib
from grr_response_proto import rrg_pb2
from grr_response_proto.rrg import os_pb2 as rrg_os_pb2
from grr_response_proto.rrg import startup_pb2 as rrg_startup_pb2
from grr_response_proto.rrg.action import get_system_metadata_pb2 as rrg_get_system_metadata_pb2
from grr_response_proto.rrg.action import list_interfaces_pb2 as rrg_list_interfaces_pb2
from grr_response_proto.rrg.action import list_mounts_pb2 as rrg_list_mounts_pb2
from grr_response_proto.rrg.action import query_wmi_pb2 as rrg_query_wmi_pb2


class DiscoveryTestEventListener(events.EventListener):
  """A test listener to receive new client discoveries."""

  EVENTS = ["Discovery"]

  # For this test we just write the event as a class attribute.
  event = None

  def ProcessEvents(self, msgs=None, publisher_username=None):
    DiscoveryTestEventListener.event = msgs[0]


class TestClientInterrogate(
    acl_test_lib.AclTestMixin,
    notification_test_lib.NotificationTestMixin,
    flow_test_lib.FlowTestsBaseclass,
    stats_test_lib.StatsTestMixin,
):
  """Test the interrogate flow."""

  def _OpenClient(self, client_id):
    return mig_objects.ToRDFClientSnapshot(
        data_store.REL_DB.ReadClientSnapshot(client_id)
    )

  def _CheckUsers(self, client, expected_users):
    self.assertCountEqual(
        [user.username for user in client.knowledge_base.users], expected_users
    )

  def _CheckBasicInfo(self, client, fqdn, system, install_date):
    self.assertEqual(client.knowledge_base.fqdn, fqdn)
    self.assertEqual(client.knowledge_base.os, system)
    self.assertEqual(client.install_time, install_date)

  def _CheckClientInfo(self, client):
    info = client.startup_info.client_info
    self.assertEqual(info.client_name, config.CONFIG["Client.name"])
    self.assertEqual(
        info.client_version, int(config.CONFIG["Source.version_numeric"])
    )
    self.assertEqual(info.build_time, config.CONFIG["Client.build_time"])

  def _CheckGRRConfig(self, client):
    config_dict = {item.key: item.value for item in client.grr_configuration}

    # Config is stored in a string map so everything gets converted.
    self.assertEqual(config_dict["Client.foreman_check_frequency"], str(3600))

  def _CheckClientKwIndex(self, keywords, expected_count):
    # Tests that the client index has expected_count results when
    # searched for keywords.
    index = client_index.ClientIndex()
    self.assertLen(index.LookupClients(keywords), expected_count)

  def _CheckNotificationsCreated(self, username, client_id):
    notifications = self.GetUserNotifications(username)

    self.assertLen(notifications, 1)
    notification = notifications[0]
    self.assertEqual(notification.reference.client.client_id, client_id)

  def _CheckClientSummary(
      self,
      client_id,
      summary,
      osname,
      version,
      kernel="3.13.0-39-generic",
      release="5",
  ):
    self.assertEqual(
        summary.client_info.client_name, config.CONFIG["Client.name"]
    )
    self.assertEqual(
        summary.client_info.client_version,
        int(config.CONFIG["Source.version_numeric"]),
    )
    self.assertEqual(
        summary.client_info.build_time, config.CONFIG["Client.build_time"]
    )

    self.assertEqual(summary.system_info.system, osname)
    self.assertEqual(summary.system_info.fqdn, "test_node.test")
    self.assertEqual(summary.system_info.release, release)
    self.assertEqual(summary.system_info.version, version)
    self.assertEqual(summary.system_info.machine, "i386")
    self.assertEqual(summary.system_info.kernel, kernel)

    self.assertLen(summary.interfaces, 1)
    self.assertEqual(summary.interfaces[0].mac_address, b"123456")

    # Check that the client summary was published to the event listener.
    self.assertEqual(DiscoveryTestEventListener.event.client_id, client_id)
    self.assertEqual(
        DiscoveryTestEventListener.event.interfaces[0].mac_address, b"123456"
    )
    self.assertTrue(DiscoveryTestEventListener.event.timestamp)
    self.assertTrue(DiscoveryTestEventListener.event.last_ping)

  def _CheckNetworkInfo(self, client):
    self.assertEqual(client.interfaces[0].mac_address, b"123456")
    self.assertEqual(
        client.interfaces[0].addresses[0].human_readable_address,
        "100.100.100.1",
    )
    self.assertEqual(
        socket.inet_ntop(
            socket.AF_INET, client.interfaces[0].addresses[0].packed_bytes
        ),
        "100.100.100.1",
    )

  def _CheckLabels(self, client_id):
    expected_labels = ["GRRLabel1", "Label2"]

    labels = data_store.REL_DB.ReadClientLabels(client_id)
    self.assertEqual([label.name for label in labels], expected_labels)

  def _CheckLabelIndex(self, client_id):
    """Check that label indexes are updated."""
    self.assertCountEqual(
        client_index.ClientIndex().LookupClients(["label:Label2"]), [client_id]
    )

  def _CheckRelease(self, client, desired_release, desired_version):
    release = client.knowledge_base.os_release
    version = client.os_version

    self.assertEqual(release, desired_release)
    self.assertEqual(version, desired_version)

  def _CheckClientLibraries(self, client):
    versions = client.library_versions
    keys = [item.key for item in versions]

    self.assertCountEqual(keys, admin.GetLibraryVersions.library_map.keys())

    error_str = admin.GetLibraryVersions.error_str
    # Strip off the exception itself.
    error_str = error_str[: error_str.find("%s")]

    values = [item.value for item in versions]
    for v in values:
      self.assertNotStartsWith(v, error_str)

  def _CheckMemory(self, client):
    self.assertTrue(client.memory_size)

  def _CheckCloudMetadata(self, client):
    self.assertTrue(client.cloud_instance)
    self.assertEqual(client.cloud_instance.google.instance_id, "instance_id")
    self.assertEqual(client.cloud_instance.google.project_id, "project_id")
    self.assertEqual(client.cloud_instance.google.zone, "zone")
    self.assertEqual(
        client.cloud_instance.google.unique_id, "zone/project_id/instance_id"
    )
    self.assertEqual(client.cloud_instance.google.hostname, "hostname")

  def setUp(self):
    super().setUp()
    # This test checks for notifications so we can't use a system user.
    self.test_username = "discovery_test_user"
    self.CreateUser(self.test_username)
    # Labels are added using the `GRR` system user.
    self.CreateUser("GRR")

  def _SetupMinimalClient(self):
    client_id = "C.0000000000000000"

    data_store.REL_DB.WriteClientMetadata(client_id)

    startup = jobs_pb2.StartupInfo()
    startup.client_info.client_name = "GRR"
    startup.client_info.client_version = 4321
    data_store.REL_DB.WriteClientStartupInfo(client_id, startup)

    return client_id

  def testInterrogateCloudMetadataLinux(self):
    """Check google cloud metadata on linux."""
    client_id = self._SetupMinimalClient()
    with vfs_test_lib.VFSOverrider(
        rdf_paths.PathSpec.PathType.OS, vfs_test_lib.FakeTestDataVFSHandler
    ):
      client_mock = action_mocks.InterrogatedClient()
      client_mock.InitializeClient()

      flow_test_lib.StartAndRunFlow(
          discovery.Interrogate,
          client_mock,
          creator=self.test_username,
          client_id=client_id,
      )

    client = self._OpenClient(client_id)
    self._CheckCloudMetadata(client)

  def testInterrogateCloudMetadataWindows(self):
    """Check google cloud metadata on windows."""
    client_id = self._SetupMinimalClient()
    with vfs_test_lib.VFSOverrider(
        rdf_paths.PathSpec.PathType.REGISTRY,
        vfs_test_lib.FakeRegistryVFSHandler,
    ):
      with vfs_test_lib.VFSOverrider(
          rdf_paths.PathSpec.PathType.OS, vfs_test_lib.FakeFullVFSHandler
      ):
        client_mock = action_mocks.InterrogatedClient()
        client_mock.InitializeClient(
            system="Windows", version="6.1.7600", kernel="6.1.7601"
        )
        with mock.patch.object(platform, "system", return_value="Windows"):
          flow_test_lib.StartAndRunFlow(
              discovery.Interrogate,
              client_mock,
              creator=self.test_username,
              client_id=client_id,
          )

    client = self._OpenClient(client_id)
    self._CheckCloudMetadata(client)

  def testInterrogateLinux(self):
    """Test the Interrogate flow."""
    client_id = self._SetupMinimalClient()

    startup_info = jobs_pb2.StartupInfo()
    startup_info.client_info.client_name = "GRR"
    startup_info.client_info.client_version = 1337
    data_store.REL_DB.WriteClientStartupInfo(client_id, startup_info)

    with vfs_test_lib.FakeTestDataVFSOverrider():
      client_mock = action_mocks.InterrogatedClient()
      client_mock.InitializeClient(version="14.4", release="Ubuntu")

      with test_lib.SuppressLogs():
        flow_test_lib.StartAndRunFlow(
            discovery.Interrogate,
            client_mock,
            creator=self.test_username,
            client_id=client_id,
        )

    client = self._OpenClient(client_id)
    self._CheckBasicInfo(client, "test_node.test", "Linux", 100 * 1000000)
    self._CheckClientInfo(client)
    self._CheckGRRConfig(client)
    self._CheckNotificationsCreated(self.test_username, client_id)
    self._CheckClientSummary(
        client_id,
        client.GetSummary(),
        "Linux",
        "14.4",
        release="Ubuntu",
        kernel="3.13.0-39-generic",
    )
    self._CheckRelease(client, "Ubuntu", "14.4")

    # users 1,2,3 from wtmp, users yagharek, isaac from netgroup
    self._CheckUsers(client, ["yagharek", "isaac", "user1", "user2", "user3"])
    self._CheckNetworkInfo(client)
    # No VFS test when running on the relational db.
    self._CheckLabels(client_id)
    self._CheckLabelIndex(client_id)
    self._CheckClientKwIndex(["Linux"], 1)
    self._CheckClientKwIndex(["Label2"], 1)
    self._CheckClientLibraries(client)
    self._CheckMemory(client)

  def testInterrogateWindows(self):
    """Test the Interrogate flow."""
    client_id = self._SetupMinimalClient()

    startup_info = jobs_pb2.StartupInfo()
    startup_info.client_info.client_name = "GRR"
    startup_info.client_info.client_version = 1337
    data_store.REL_DB.WriteClientStartupInfo(client_id, startup_info)

    with vfs_test_lib.VFSOverrider(
        rdf_paths.PathSpec.PathType.REGISTRY,
        vfs_test_lib.FakeRegistryVFSHandler,
    ):
      with vfs_test_lib.VFSOverrider(
          rdf_paths.PathSpec.PathType.OS, vfs_test_lib.FakeFullVFSHandler
      ):

        client_mock = action_mocks.InterrogatedClient()
        client_mock.InitializeClient(
            system="Windows", version="6.1.7600", kernel="6.1.7601"
        )

        # Run the flow in the simulated way
        flow_test_lib.StartAndRunFlow(
            discovery.Interrogate,
            client_mock,
            creator=self.test_username,
            client_id=client_id,
        )

    client = self._OpenClient(client_id)
    self._CheckBasicInfo(client, "test_node.test", "Windows", 100 * 1000000)
    self._CheckClientInfo(client)
    self._CheckGRRConfig(client)
    self._CheckNotificationsCreated(self.test_username, client_id)
    self._CheckClientSummary(
        client_id, client.GetSummary(), "Windows", "6.1.7600", kernel="6.1.7601"
    )
    # jim parsed from registry profile keys
    self._CheckUsers(client, ["jim", "kovacs"])
    self._CheckNetworkInfo(client)
    # No VFS test for the relational db.
    self._CheckLabels(client_id)
    self._CheckLabelIndex(client_id)
    # No registry pathspec test for the relational db.
    self._CheckClientKwIndex(["Linux"], 0)
    self._CheckClientKwIndex(["Windows"], 1)
    self._CheckClientKwIndex(["Label2"], 1)
    self._CheckMemory(client)

  def testInterrogateVolumesWindows(self):
    assert data_store.REL_DB is not None
    db: abstract_db.Database = data_store.REL_DB

    creator = db_test_utils.InitializeUser(db)
    client_id = db_test_utils.InitializeClient(db)

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Windows"
    snapshot.startup_info.client_info.client_name = "GRR"
    snapshot.startup_info.client_info.client_version = 4321
    db.WriteClientSnapshot(snapshot)

    class ActionMock(action_mocks.ActionMock):

      def WmiQuery(
          self,
          args: rdf_client_action.WMIRequest,
      ) -> Iterator[rdf_protodict.Dict]:
        args = mig_client_action.ToProtoWMIRequest(args)

        if not args.query.upper().startswith("SELECT "):
          raise RuntimeError("Non-`SELECT` WMI query")

        if "Win32_LogicalDisk" not in args.query:
          raise RuntimeError(f"Unexpected WMI query: {args.query!r}")

        yield rdf_protodict.Dict({
            "Access": 0,
            "BlockSize": None,
            "Caption": "C:",
            "Compressed": False,
            "Description": "Local Fixed Disk",
            "DeviceID": "C:",
            "DriveType": 3,
            "FileSystem": "NTFS",
            "FreeSpace": "1807140478976",
            "InstallDate": None,
            "MediaType": 12,
            "Name": "C:",
            "NumberOfBlocks": None,
            "PNPDeviceID": None,
            "Size": "2047370850304",
            "SupportsDiskQuotas": False,
            "SupportsFileBasedCompression": True,
            "VolumeDirty": None,
            "VolumeName": "gWindows",
            "VolumeSerialNumber": "BCF3E28E",
        })

    flow_id = flow_test_lib.StartAndRunFlow(
        discovery.Interrogate,
        ActionMock(),
        client_id=client_id,
        creator=creator,
        # We use minimal setup, so certain subflows spawned by interrogation can
        # fail. We verify that the interrogation flow actually completed below.
        check_flow_errors=False,
    )

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    snapshot = data_store.REL_DB.ReadClientSnapshot(client_id)
    self.assertLen(snapshot.volumes, 1)

    volume = snapshot.volumes[0]
    self.assertEqual(volume.name, "gWindows")
    self.assertEqual(volume.serial_number, "BCF3E28E")
    self.assertEqual(volume.file_system_type, "NTFS")
    self.assertEqual(volume.windowsvolume.drive_letter, "C:")
    self.assertEqual(volume.windowsvolume.drive_type, 3)

  def testClientSummary_RRG(self):
    assert data_store.REL_DB is not None
    db: abstract_db.Database = data_store.REL_DB

    client_id = db_test_utils.InitializeClient(db)

    startup = rrg_startup_pb2.Startup()
    startup.metadata.version.major = 1
    startup.metadata.version.minor = 2
    startup.metadata.version.patch = 3
    startup.metadata.version.pre = "foo"
    startup.os_type = rrg_os_pb2.LINUX
    db.WriteClientRRGStartup(client_id, startup)

    def GetSystemMetadataHandler(session: rrg_test_lib.Session) -> None:
      result = rrg_get_system_metadata_pb2.Result()
      result.type = rrg_os_pb2.Type.LINUX
      session.Reply(result)

    def NotImplementedHandler(session: rrg_test_lib.Session) -> None:
      del session  # Unused.
      raise NotImplementedError()

    summary = jobs_pb2.ClientSummary()

    class TestClientSummaryEventListener(events.EventListener):

      EVENTS = ["Discovery"]

      def ProcessEvents(self, msgs=None, publisher_username=None):
        del publisher_username  # Unused.

        for msg in msgs or []:
          summary.MergeFrom(msg.AsPrimitiveProto())

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=discovery.Interrogate,
        flow_args=discovery.InterrogateArgs(),
        handlers={
            rrg_pb2.Action.GET_SYSTEM_METADATA: GetSystemMetadataHandler,
            # We don't care about these actions in this test — the flow should
            # gracefully handle their failures anyway. We verify that the flow
            # finished (and not crashed) below.
            rrg_pb2.Action.QUERY_WMI: NotImplementedHandler,
            rrg_pb2.Action.LIST_INTERFACES: NotImplementedHandler,
            rrg_pb2.Action.LIST_MOUNTS: NotImplementedHandler,
            rrg_pb2.Action.GREP_FILE_CONTENTS: NotImplementedHandler,
        },
    )

    del TestClientSummaryEventListener

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    self.assertEqual(summary.rrg_version_major, 1)
    self.assertEqual(summary.rrg_version_minor, 2)
    self.assertEqual(summary.rrg_version_patch, 3)
    self.assertEqual(summary.rrg_version_pre, "foo")

  def testInterrogateVolumesWindows_RRG(self):
    assert data_store.REL_DB is not None
    db: abstract_db.Database = data_store.REL_DB

    client_id = db_test_utils.InitializeRRGClient(
        db,
        os_type=rrg_os_pb2.WINDOWS,
    )

    def GetSystemMetadataHandler(session: rrg_test_lib.Session) -> None:
      result = rrg_get_system_metadata_pb2.Result()
      result.type = rrg_os_pb2.Type.WINDOWS
      session.Reply(result)

    def QueryWmiHandler(session: rrg_test_lib.Session) -> None:
      args = rrg_query_wmi_pb2.Args()
      assert session.args.Unpack(args)

      if args.query.split()[:1] != ["SELECT"]:
        raise RuntimeError("Non-`SELECT` WMI query")

      if "Win32_LogicalDisk" not in args.query:
        raise RuntimeError(f"Unexpected WMI query: {args.query!r}")

      result = rrg_query_wmi_pb2.Result()
      result.row["FileSystem"].string = "NTFS"
      result.row["DeviceID"].string = "C:"
      result.row["FreeSpace"].string = "83074121728"
      result.row["Size"].string = "160939618304"
      result.row["VolumeName"].string = "Foo"
      result.row["VolumeSerialNumber"].string = "BCF3E28E"
      session.Reply(result)

    def NotImplementedHandler(session: rrg_test_lib.Session) -> None:
      del session  # Unused.
      raise NotImplementedError()

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=discovery.Interrogate,
        flow_args=discovery.InterrogateArgs(),
        handlers={
            rrg_pb2.Action.GET_SYSTEM_METADATA: GetSystemMetadataHandler,
            rrg_pb2.Action.QUERY_WMI: QueryWmiHandler,
            # We don't care about these actions in this test — the flow should
            # gracefully handle their failures anyway. We verify that the flow
            # finished (and not crashed) below.
            rrg_pb2.Action.LIST_INTERFACES: NotImplementedHandler,
            rrg_pb2.Action.LIST_MOUNTS: NotImplementedHandler,
            rrg_pb2.Action.GET_WINREG_VALUE: NotImplementedHandler,
            rrg_pb2.Action.LIST_WINREG_KEYS: NotImplementedHandler,
        },
    )

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    snapshot = data_store.REL_DB.ReadClientSnapshot(client_id)
    self.assertLen(snapshot.volumes, 1)

    volume = snapshot.volumes[0]
    self.assertEqual(volume.name, "Foo")
    self.assertEqual(volume.serial_number, "BCF3E28E")
    self.assertEqual(volume.file_system_type, "NTFS")
    self.assertEqual(volume.windowsvolume.drive_letter, "C:")

    self.assertEqual(volume.bytes_per_sector, 1)
    self.assertEqual(volume.sectors_per_allocation_unit, 1)
    self.assertEqual(volume.total_allocation_units, 160_939_618_304)
    self.assertEqual(volume.actual_available_allocation_units, 83_074_121_728)

  def testInterrogateVolumesUnix(self):
    assert data_store.REL_DB is not None
    db: abstract_db.Database = data_store.REL_DB

    creator = db_test_utils.InitializeUser(db)
    client_id = db_test_utils.InitializeClient(db)

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Linux"
    db.WriteClientSnapshot(snapshot)

    startup = jobs_pb2.StartupInfo()
    startup.client_info.client_version = 4321
    data_store.REL_DB.WriteClientStartupInfo(client_id, startup)

    class ActionMock(action_mocks.ActionMock):

      def StatFS(
          self,
          args: rdf_client_action.StatFSRequest,
      ) -> Iterator[rdf_client_fs.Volume]:
        args = mig_client_action.ToProtoStatFSRequest(args)

        if not (len(args.path_list) == 1 and args.path_list[0] == "/"):
          raise RuntimeError(f"Unexpected path list: {args.path_list}")

        result = sysinfo_pb2.Volume()
        result.unixvolume.mount_point = "/"

        yield mig_client_fs.ToRDFVolume(result)

    flow_id = flow_test_lib.StartAndRunFlow(
        discovery.Interrogate,
        ActionMock(),
        client_id=client_id,
        creator=creator,
        # We use minimal setup, so certain subflows spawned by interrogation
        # can fail. We verify that the interrogation flow actually completed
        # below.
        check_flow_errors=False,
    )

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    snapshot = data_store.REL_DB.ReadClientSnapshot(client_id)
    self.assertLen(snapshot.volumes, 1)
    self.assertEqual(snapshot.volumes[0].unixvolume.mount_point, "/")

  @mock.patch.object(fleetspeak_utils, "GetLabelsFromFleetspeak")
  def testFleetspeakClient(self, mock_labels_fn):
    mock_labels_fn.return_value = ["foo", "bar"]
    client_id = "C.0000000000000001"
    data_store.REL_DB.WriteClientMetadata(
        client_id, fleetspeak_validation_info={"IP": "12.34.56.78"}
    )

    startup_info = jobs_pb2.StartupInfo()
    startup_info.client_info.client_name = "GRR"
    startup_info.client_info.client_version = 1337
    data_store.REL_DB.WriteClientStartupInfo(client_id, startup_info)

    client_mock = action_mocks.InterrogatedClient()
    client_mock.InitializeClient(
        fqdn="fleetspeak.test.com",
        system="Linux",
        release="Ubuntu",
        version="14.4",
    )

    with vfs_test_lib.FakeTestDataVFSOverrider():
      flow_test_lib.StartAndRunFlow(
          discovery.Interrogate,
          client_mock,
          creator=self.test_username,
          client_id=client_id,
      )

    snapshot = data_store.REL_DB.ReadClientSnapshot(client_id)
    self.assertEqual(snapshot.knowledge_base.fqdn, "fleetspeak.test.com")
    self.assertEqual(snapshot.knowledge_base.os, "Linux")
    self._CheckClientInfo(snapshot)
    self._CheckGRRConfig(snapshot)
    self._CheckNotificationsCreated(self.test_username, client_id)
    self._CheckRelease(snapshot, "Ubuntu", "14.4")
    self._CheckNetworkInfo(mig_objects.ToRDFClientSnapshot(snapshot))
    labels = data_store.REL_DB.ReadClientLabels(client_id)
    self.assertCountEqual([l.name for l in labels], ["foo", "bar"])

    fs_validation_tags = snapshot.fleetspeak_validation_info.tags
    self.assertLen(fs_validation_tags, 1)
    self.assertEqual(fs_validation_tags[0].key, "IP")
    self.assertEqual(fs_validation_tags[0].value, "12.34.56.78")

  @mock.patch.object(fleetspeak_utils, "GetLabelsFromFleetspeak")
  def testFleetspeakClient_OnlyGRRLabels(self, mock_labels_fn):
    mock_labels_fn.return_value = []
    client_id = "C.0000000000000001"
    data_store.REL_DB.WriteClientMetadata(client_id)

    startup_info = jobs_pb2.StartupInfo()
    startup_info.client_info.client_name = "GRR"
    startup_info.client_info.client_version = 1337
    data_store.REL_DB.WriteClientStartupInfo(client_id, startup_info)

    client_mock = action_mocks.InterrogatedClient()
    client_mock.InitializeClient(
        fqdn="fleetspeak.test.com",
        system="Linux",
        release="Ubuntu",
        version="14.4",
    )

    with vfs_test_lib.VFSOverrider(
        rdf_paths.PathSpec.PathType.OS, vfs_test_lib.FakeTestDataVFSHandler
    ):
      with self.assertStatsCounterDelta(
          1, discovery.FLEETSPEAK_UNLABELED_CLIENTS
      ):

        flow_test_lib.StartAndRunFlow(
            discovery.Interrogate,
            client_mock,
            creator=self.test_username,
            client_id=client_id,
        )

    labels = data_store.REL_DB.ReadClientLabels(client_id)
    expected_labels = [
        action_mocks.InterrogatedClient.LABEL1,
        action_mocks.InterrogatedClient.LABEL2,
    ]
    self.assertCountEqual([l.name for l in labels], expected_labels)

  def testCrowdStrikeAgentIDCollection(self):
    agent_id = binascii.hexlify(os.urandom(16)).decode("ascii")
    client_id = db_test_utils.InitializeClient(data_store.REL_DB)

    client_snapshot = objects_pb2.ClientSnapshot()
    client_snapshot.startup_info.client_info.client_name = "GRR"
    client_snapshot.startup_info.client_info.client_version = 4321
    client_snapshot.client_id = client_id
    client_snapshot.knowledge_base.os = "Linux"
    data_store.REL_DB.WriteClientSnapshot(client_snapshot)

    class ClientMock(action_mocks.InterrogatedClient):

      def ExecuteCommand(
          self,
          args: rdf_client_action.ExecuteRequest,
      ) -> rdf_client_action.ExecuteResponse:
        del args  # Unused.

        stdout = f'cid="4815162342",aid="{agent_id}"'

        result = rdf_client_action.ExecuteResponse()
        result.stdout = stdout.encode("ascii")
        yield result

    # Without clearing the artifact registry, the flow gets stuck. It is most
    # likely caused by some artifact waiting for something to be initialized or
    # other terrible dependency but I am too tired of trying to figure out what
    # exactly is the issue.
    with mock.patch.object(
        artifact_registry,
        "REGISTRY",
        artifact_registry.ArtifactRegistry(),
    ):
      with test_lib.ConfigOverrider({
          "Interrogate.collect_crowdstrike_agent_id": True,
      }):
        flow_test_lib.StartAndRunFlow(
            discovery.Interrogate,
            client_mock=ClientMock(),
            client_id=client_id,
        )
        flow_test_lib.FinishAllFlowsOnClient(client_id)

    client_snapshot = data_store.REL_DB.ReadClientSnapshot(client_id)
    self.assertLen(client_snapshot.edr_agents, 1)
    self.assertEqual(client_snapshot.edr_agents[0].name, "CrowdStrike")
    self.assertEqual(client_snapshot.edr_agents[0].agent_id, agent_id)

  def testSourceFlowIdIsSet(self):
    client_id = self._SetupMinimalClient()
    client_mock = action_mocks.InterrogatedClient()
    client_mock.InitializeClient()
    with test_lib.SuppressLogs():
      flow_id = flow_test_lib.StartAndRunFlow(
          discovery.Interrogate,
          client_mock,
          creator=self.test_username,
          client_id=client_id,
      )

    client = self._OpenClient(client_id)
    self.assertNotEmpty(client.metadata.source_flow_id)
    self.assertEqual(client.metadata.source_flow_id, flow_id)

  # TODO: Create a test with full RRG interrogation once there is
  # a single branch point and the flow is using either RRG actions or the Python
  # agent actions.

  @db_test_lib.WithDatabase
  def testHandleRRGGetSystemMetadata(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)
    flow_id = db_test_utils.InitializeFlow(db, client_id)

    result = rrg_get_system_metadata_pb2.Result()
    result.type = rrg_os_pb2.Type.LINUX
    result.arch = "x86_64"
    result.version = "1.2.3-alpha"
    result.fqdn = "foo.example.com"
    result.install_time.FromDatetime(datetime.datetime.now())

    result_response = rdf_flow_objects.FlowResponse()
    result_response.any_payload = rdf_structs.AnyValue.PackProto2(result)

    status_response = rdf_flow_objects.FlowStatus()
    status_response.status = rdf_flow_objects.FlowStatus.Status.OK

    responses = flow_responses.Responses.FromResponsesProto2Any([
        result_response,
        status_response,
    ])

    flow_args = discovery.InterrogateArgs()
    flow_args.lightweight = False

    rdf_flow = rdf_flow_objects.Flow()
    rdf_flow.client_id = client_id
    rdf_flow.flow_id = flow_id
    rdf_flow.flow_class_name = discovery.Interrogate.__name__
    rdf_flow.args = flow_args

    flow = discovery.Interrogate(rdf_flow)
    flow.Start()
    flow.HandleRRGGetSystemMetadata(responses)

    self.assertEqual(flow.store.client_snapshot.knowledge_base.os, "Linux")
    self.assertEqual(flow.store.client_snapshot.arch, "x86_64")
    self.assertEqual(
        flow.store.client_snapshot.knowledge_base.fqdn, "foo.example.com"
    )
    self.assertEqual(flow.store.client_snapshot.os_version, "1.2.3-alpha")

  # TODO: https://github.com/google/rrg/issues/58 - Remove once FQDN collection
  # is working on all platforms.
  @db_test_lib.WithDatabase
  def testHandleRRGGetSystemMetadataHostname(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)
    flow_id = db_test_utils.InitializeFlow(db, client_id)

    result = rrg_get_system_metadata_pb2.Result()
    result.type = rrg_os_pb2.Type.MACOS
    result.hostname = "foobar"
    result.install_time.FromDatetime(datetime.datetime.now())

    result_response = rdf_flow_objects.FlowResponse()
    result_response.any_payload = rdf_structs.AnyValue.PackProto2(result)

    status_response = rdf_flow_objects.FlowStatus()
    status_response.status = rdf_flow_objects.FlowStatus.Status.OK

    responses = flow_responses.Responses.FromResponsesProto2Any([
        result_response,
        status_response,
    ])

    flow_args = discovery.InterrogateArgs()
    flow_args.lightweight = False

    rdf_flow = rdf_flow_objects.Flow()
    rdf_flow.client_id = client_id
    rdf_flow.flow_id = flow_id
    rdf_flow.flow_class_name = discovery.Interrogate.__name__
    rdf_flow.args = flow_args

    flow = discovery.Interrogate(rdf_flow)
    flow.Start()
    flow.HandleRRGGetSystemMetadata(responses)

    self.assertEqual(flow.store.client_snapshot.knowledge_base.os, "Darwin")
    self.assertEqual(flow.store.client_snapshot.knowledge_base.fqdn, "foobar")

  @db_test_lib.WithDatabase
  def testHandleRRGGetSystemMetadataCloudVMMetadataLinux(
      self,
      db: abstract_db.Database,
  ):
    client_id = db_test_utils.InitializeRRGClient(db)
    flow_id = db_test_utils.InitializeFlow(db, client_id)

    result = rrg_get_system_metadata_pb2.Result(type=rrg_os_pb2.Type.LINUX)
    result_response = rdf_flow_objects.FlowResponse()
    result_response.any_payload = rdf_structs.AnyValue.PackProto2(result)

    status_response = rdf_flow_objects.FlowStatus()
    status_response.status = rdf_flow_objects.FlowStatus.Status.OK

    responses = flow_responses.Responses.FromResponsesProto2Any([
        result_response,
        status_response,
    ])

    flow_args = discovery.InterrogateArgs()
    flow_args.lightweight = False

    rdf_flow = rdf_flow_objects.Flow()
    rdf_flow.client_id = client_id
    rdf_flow.flow_id = flow_id
    rdf_flow.flow_class_name = discovery.Interrogate.__name__
    rdf_flow.args = flow_args

    flow = discovery.Interrogate(rdf_flow)
    flow.Start()
    flow.HandleRRGGetSystemMetadata(responses)

    cloud_vm_metadata_requested = False
    for child in db.ReadAllFlowObjects(client_id, parent_flow_id=flow_id):
      if child.flow_class_name == cloud.CollectCloudVMMetadata.__name__:
        cloud_vm_metadata_requested = True

    self.assertTrue(cloud_vm_metadata_requested)

  @db_test_lib.WithDatabase
  def testHandleRRGGetSystemMetadataCloudVMMetadataMacOS(
      self,
      db: abstract_db.Database,
  ):
    client_id = db_test_utils.InitializeRRGClient(db)
    flow_id = db_test_utils.InitializeFlow(db, client_id)

    result = rrg_get_system_metadata_pb2.Result(type=rrg_os_pb2.Type.MACOS)
    result_response = rdf_flow_objects.FlowResponse()
    result_response.any_payload = rdf_structs.AnyValue.PackProto2(result)

    status_response = rdf_flow_objects.FlowStatus()
    status_response.status = rdf_flow_objects.FlowStatus.Status.OK

    responses = flow_responses.Responses.FromResponsesProto2Any([
        result_response,
        status_response,
    ])

    flow_args = discovery.InterrogateArgs()
    flow_args.lightweight = False

    rdf_flow = rdf_flow_objects.Flow()
    rdf_flow.client_id = client_id
    rdf_flow.flow_id = flow_id
    rdf_flow.flow_class_name = discovery.Interrogate.__name__
    rdf_flow.args = flow_args

    flow = discovery.Interrogate(rdf_flow)
    flow.Start()
    flow.HandleRRGGetSystemMetadata(responses)

    # We should not collect VM metadata for macOS.
    self.assertFalse(
        _HasClientActionRequest(flow, server_stubs.GetCloudVMMetadata)
    )

  @db_test_lib.WithDatabase
  def testHandleRRGListInterfaces(
      self,
      db: abstract_db.Database,
  ):
    client_id = db_test_utils.InitializeRRGClient(db)
    flow_id = db_test_utils.InitializeFlow(db, client_id)

    result = rrg_list_interfaces_pb2.Result()
    result.interface.name = "lo"
    result.interface.ip_addresses.add(
        octets=ipaddress.ip_address("127.0.0.1").packed,
    )
    result.interface.ip_addresses.add(
        octets=ipaddress.ip_address("::1").packed,
    )
    result.interface.mac_address.octets = b"\xa1\xb2\xc3\xd4\xe5\xf6"

    result_response = rdf_flow_objects.FlowResponse()
    result_response.any_payload = rdf_structs.AnyValue.PackProto2(result)

    status_response = rdf_flow_objects.FlowStatus()
    status_response.status = rdf_flow_objects.FlowStatus.Status.OK

    responses = flow_responses.Responses.FromResponsesProto2Any([
        result_response,
        status_response,
    ])

    flow_args = discovery.InterrogateArgs()
    flow_args.lightweight = False

    rdf_flow = rdf_flow_objects.Flow()
    rdf_flow.client_id = client_id
    rdf_flow.flow_id = flow_id
    rdf_flow.flow_class_name = discovery.Interrogate.__name__
    rdf_flow.args = flow_args

    flow = discovery.Interrogate(rdf_flow)
    flow.Start()
    flow.HandleRRGListInterfaces(responses)

    snapshot = flow.store.client_snapshot
    self.assertLen(snapshot.interfaces, 1)
    self.assertEqual(snapshot.interfaces[0].ifname, "lo")
    self.assertLen(snapshot.interfaces[0].addresses, 2)
    self.assertEqual(
        snapshot.interfaces[0].addresses[0].address_type,
        jobs_pb2.NetworkAddress.Family.INET,
    )
    self.assertEqual(
        snapshot.interfaces[0].addresses[0].packed_bytes,
        ipaddress.ip_address("127.0.0.1").packed,
    )
    self.assertEqual(
        snapshot.interfaces[0].addresses[1].address_type,
        jobs_pb2.NetworkAddress.Family.INET6,
    )
    self.assertEqual(
        snapshot.interfaces[0].addresses[1].packed_bytes,
        ipaddress.ip_address("::1").packed,
    )
    self.assertEqual(
        snapshot.interfaces[0].mac_address,
        b"\xa1\xb2\xc3\xd4\xe5\xf6",
    )

  @db_test_lib.WithDatabase
  def testHandleRRGListMounts(
      self,
      db: abstract_db.Database,
  ):
    client_id = db_test_utils.InitializeRRGClient(db, os_type=rrg_os_pb2.LINUX)
    flow_id = db_test_utils.InitializeFlow(db, client_id)

    result_0 = rrg_list_mounts_pb2.Result()
    result_0.mount.name = "sysfs"
    result_0.mount.path.raw_bytes = "/sys".encode("ascii")
    result_0.mount.fs_type = "sysfs"

    result_1 = rrg_list_mounts_pb2.Result()
    result_1.mount.name = "udev"
    result_1.mount.path.raw_bytes = "/dev".encode("ascii")
    result_1.mount.fs_type = "devtmpfs"

    result_2 = rrg_list_mounts_pb2.Result()
    result_2.mount.name = "/dev/nvme0n1p1"
    result_2.mount.path.raw_bytes = "/boot/efi".encode("ascii")
    result_2.mount.fs_type = "vfat"

    result_response_0 = rdf_flow_objects.FlowResponse()
    result_response_0.any_payload = rdf_structs.AnyValue.PackProto2(result_0)

    result_response_1 = rdf_flow_objects.FlowResponse()
    result_response_1.any_payload = rdf_structs.AnyValue.PackProto2(result_1)

    result_response_2 = rdf_flow_objects.FlowResponse()
    result_response_2.any_payload = rdf_structs.AnyValue.PackProto2(result_2)

    status_response = rdf_flow_objects.FlowStatus()
    status_response.status = rdf_flow_objects.FlowStatus.Status.OK

    responses = flow_responses.Responses.FromResponsesProto2Any([
        result_response_0,
        result_response_1,
        result_response_2,
        status_response,
    ])

    flow_args = discovery.InterrogateArgs()
    flow_args.lightweight = False

    rdf_flow = rdf_flow_objects.Flow()
    rdf_flow.client_id = client_id
    rdf_flow.flow_id = flow_id
    rdf_flow.flow_class_name = discovery.Interrogate.__name__
    rdf_flow.args = flow_args

    flow = discovery.Interrogate(rdf_flow)
    flow.Start()
    flow.HandleRRGListMounts(responses)

    snapshot = flow.store.client_snapshot
    self.assertLen(snapshot.filesystems, 3)
    self.assertEqual(snapshot.filesystems[0].device, "sysfs")
    self.assertEqual(snapshot.filesystems[0].mount_point, "/sys")
    self.assertEqual(snapshot.filesystems[0].type, "sysfs")
    self.assertEqual(snapshot.filesystems[1].device, "udev")
    self.assertEqual(snapshot.filesystems[1].mount_point, "/dev")
    self.assertEqual(snapshot.filesystems[1].type, "devtmpfs")
    self.assertEqual(snapshot.filesystems[2].device, "/dev/nvme0n1p1")
    self.assertEqual(snapshot.filesystems[2].mount_point, "/boot/efi")
    self.assertEqual(snapshot.filesystems[2].type, "vfat")

  @db_test_lib.WithDatabase
  def testStartRRGOnly(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)
    flow_id = db_test_utils.InitializeFlow(db, client_id)

    flow_args = discovery.InterrogateArgs()
    flow_args.lightweight = False

    rdf_flow = rdf_flow_objects.Flow()
    rdf_flow.client_id = client_id
    rdf_flow.flow_id = flow_id
    rdf_flow.flow_class_name = discovery.Interrogate.__name__
    rdf_flow.args = flow_args

    flow = discovery.Interrogate(rdf_flow)
    flow.Start()

    self.assertFalse(_HasClientActionRequest(flow, server_stubs.GetClientInfo))
    self.assertTrue(_HasRRGRequest(flow, rrg_pb2.Action.GET_SYSTEM_METADATA))

  @db_test_lib.WithDatabase
  def testStartPythonAgent(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)
    flow_id = db_test_utils.InitializeFlow(db, client_id)

    startup_info = jobs_pb2.StartupInfo()
    startup_info.client_info.client_name = "GRR"
    startup_info.client_info.client_version = 1337
    data_store.REL_DB.WriteClientStartupInfo(client_id, startup_info)

    flow_args = discovery.InterrogateArgs()
    flow_args.lightweight = False

    rdf_flow = rdf_flow_objects.Flow()
    rdf_flow.client_id = client_id
    rdf_flow.flow_id = flow_id
    rdf_flow.flow_class_name = discovery.Interrogate.__name__
    rdf_flow.args = flow_args

    flow = discovery.Interrogate(rdf_flow)
    flow.Start()

    self.assertTrue(_HasClientActionRequest(flow, server_stubs.GetClientInfo))
    self.assertFalse(_HasRRGRequest(flow, rrg_pb2.Action.GET_SYSTEM_METADATA))

  @db_test_lib.WithDatabase
  def testStartBothAgents(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)
    flow_id = db_test_utils.InitializeFlow(db, client_id)

    startup = jobs_pb2.StartupInfo()
    startup.client_info.client_version = 4321
    db.WriteClientStartupInfo(client_id, startup)

    flow_args = discovery.InterrogateArgs()
    flow_args.lightweight = False

    rdf_flow = rdf_flow_objects.Flow()
    rdf_flow.client_id = client_id
    rdf_flow.flow_id = flow_id
    rdf_flow.flow_class_name = discovery.Interrogate.__name__
    rdf_flow.args = flow_args

    flow = discovery.Interrogate(rdf_flow)
    flow.Start()

    self.assertTrue(_HasClientActionRequest(flow, server_stubs.GetClientInfo))
    self.assertTrue(_HasRRGRequest(flow, rrg_pb2.Action.GET_SYSTEM_METADATA))

  @db_test_lib.WithDatabase
  def testProcessKnowledgeBaseCollectPasswdCacheUsers(
      self,
      db: abstract_db.Database,
  ):
    client_id = db_test_utils.InitializeClient(data_store.REL_DB)
    flow_id = db_test_utils.InitializeFlow(db, client_id)

    startup = jobs_pb2.StartupInfo()
    startup.client_info.client_version = 4321
    db.WriteClientStartupInfo(client_id, startup)

    rdf_flow = rdf_flow_objects.Flow()
    rdf_flow.client_id = client_id
    rdf_flow.flow_id = flow_id
    rdf_flow.flow_class_name = discovery.Interrogate.__name__

    flow = discovery.Interrogate(rdf_flow)
    flow.Start()

    result = knowledge_base_pb2.KnowledgeBase()
    result.os = "Linux"
    packed_result = any_pb2.Any()
    packed_result.Pack(result)

    responses = flow_responses.FakeResponses([packed_result], request_data=None)

    with test_lib.ConfigOverrider({
        "Interrogate.collect_passwd_cache_users": True,
    }):
      flow.ProcessKnowledgeBase(responses)

    self.assertTrue(_HasClientActionRequest(flow, server_stubs.FileFinderOS))

  @db_test_lib.WithDatabase
  def testProcessPasswdCacheUsers(
      self,
      db: abstract_db.Database,
  ):
    client_id = db_test_utils.InitializeClient(data_store.REL_DB)
    flow_id = db_test_utils.InitializeFlow(db, client_id)

    startup = jobs_pb2.StartupInfo()
    startup.client_info.client_name = "GRR"
    startup.client_info.client_version = 4321
    db.WriteClientStartupInfo(client_id, startup)

    rdf_flow = rdf_flow_objects.Flow()
    rdf_flow.client_id = client_id
    rdf_flow.flow_id = flow_id
    rdf_flow.flow_class_name = discovery.Interrogate.__name__

    flow = discovery.Interrogate(rdf_flow)
    flow.Start()
    flow.store.client_snapshot.knowledge_base.users.extend([
        knowledge_base_pb2.User(username="foo", full_name="Fó Fózyńczak"),
        knowledge_base_pb2.User(username="bar"),  # No full name available.
    ])

    result = flows_pb2.FileFinderResult()

    match = jobs_pb2.BufferReference()
    match.data = "foo:x:123:1337::/home/foo:/bin/bash\n".encode("utf-8")
    result.matches.append(match)

    match = jobs_pb2.BufferReference()
    match.data = "bar:x:456:1337:Bar Barowski:/home/bar:\n".encode("utf-8")
    result.matches.append(match)

    packed_result = any_pb2.Any()
    packed_result.Pack(result)

    responses = flow_responses.FakeResponses([packed_result], request_data=None)

    flow.ProcessPasswdCacheUsers(responses)

    users = list(flow.store.client_snapshot.knowledge_base.users)
    self.assertLen(users, 2)
    users.sort(key=lambda user: user.username)

    self.assertEqual(users[0].username, "bar")
    self.assertEqual(users[0].uid, 456)
    self.assertEqual(users[0].gid, 1337)
    self.assertEqual(users[0].full_name, "Bar Barowski")

    self.assertEqual(users[1].username, "foo")
    self.assertEqual(users[1].uid, 123)
    self.assertEqual(users[1].gid, 1337)
    self.assertEqual(users[1].full_name, "Fó Fózyńczak")
    self.assertEqual(users[1].shell, "/bin/bash")

  def testForemanTimeIsResetOnClientSnapshotWrite(self):
    client_id = self._SetupMinimalClient()
    data_store.REL_DB.WriteClientMetadata(
        client_id,
        last_foreman=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3600),
    )
    client_mock = action_mocks.InterrogatedClient()
    client_mock.InitializeClient()
    with test_lib.SuppressLogs():
      flow_test_lib.StartAndRunFlow(
          discovery.Interrogate,
          client_mock,
          creator=self.test_username,
          client_id=client_id,
      )

    md = data_store.REL_DB.ReadClientMetadata(client_id)
    self.assertTrue(md.HasField("last_foreman_time"))
    self.assertEqual(
        md.last_foreman_time,
        int(data_store.REL_DB.MinTimestamp()),
    )


def _HasClientActionRequest(
    flow: discovery.Interrogate,
    action: type[server_stubs.ClientActionStub],
) -> bool:
  """Checks whether the given flow has a request for the given action."""
  action_id = action_registry.ID_BY_ACTION_STUB[action]

  def IsAction(request: rdf_flows.GrrMessage) -> bool:
    return request.name == action_id

  def IsProtoAction(request: jobs_pb2.GrrMessage) -> bool:
    return request.name == action_id

  return any(map(IsAction, flow.client_action_requests)) or any(
      map(IsProtoAction, flow.proto_client_action_requests)
  )


def _HasRRGRequest(
    flow: discovery.Interrogate,
    action: rrg_pb2.Action,
) -> bool:
  """Checks whether the given flow has a request for the given RRG action."""

  def IsAction(request: rrg_pb2.Request) -> bool:
    return request.action == action

  return any(map(IsAction, flow.rrg_requests))


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
