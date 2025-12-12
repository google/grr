#!/usr/bin/env python
from collections.abc import Iterator

from absl.testing import absltest

from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import mig_client_action
from grr_response_core.lib.rdfvalues import mig_protodict
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_proto import flows_pb2
from grr_response_proto import objects_pb2
from grr_response_proto import signed_commands_pb2
from grr_response_server import data_store
from grr_response_server.databases import db as abstract_db
from grr_response_server.databases import db_test_utils
from grr_response_server.flows.general import hardware
from grr_response_server.models import protodicts as models_protodicts
from grr.test_lib import action_mocks
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import rrg_test_lib
from grr.test_lib import testing_startup
from grr_response_proto import rrg_pb2
from grr_response_proto.rrg import os_pb2 as rrg_os_pb2
from grr_response_proto.rrg.action import execute_signed_command_pb2 as rrg_execute_signed_command_pb2
from grr_response_proto.rrg.action import query_wmi_pb2 as rrg_query_wmi_pb2


class CollectHardwareInfoTest(flow_test_lib.FlowTestsBaseclass):

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    testing_startup.TestInit()

  @db_test_lib.WithDatabase
  def testRRGLinux(self, db: abstract_db.Database) -> None:
    # TODO: Load signed commands from the `.textproto` file to
    # ensure integrity.
    command = rrg_execute_signed_command_pb2.Command()
    command.path.raw_bytes = "/usr/sbin/dmidecode".encode("utf-8")
    command.args_signed.append("-q")
    signed_command = signed_commands_pb2.SignedCommand()
    signed_command.id = "dmidecode_q"
    signed_command.operating_system = signed_commands_pb2.SignedCommand.OS.LINUX
    signed_command.command = command.SerializeToString()
    signed_command.ed25519_signature = b"\x00" * 64
    db.WriteSignedCommand(signed_command)

    client_id = db_test_utils.InitializeRRGClient(
        db,
        os_type=rrg_os_pb2.LINUX,
    )

    def ExecuteSignedCommandHandler(session: rrg_test_lib.Session) -> None:
      args = rrg_execute_signed_command_pb2.Args()
      assert session.args.Unpack(args)

      command = rrg_execute_signed_command_pb2.Command()
      command.ParseFromString(args.command)

      if command.path.raw_bytes != "/usr/sbin/dmidecode".encode("utf-8"):
        raise RuntimeError(f"Unexpected command path: {command.path}")

      if command.args_signed != ["-q"]:
        raise RuntimeError(f"Unexpected command args: {command.args_signed}")

      result = rrg_execute_signed_command_pb2.Result()
      result.exit_code = 0
      result.stdout = """\
BIOS Information
        Vendor: Google
        Version: Google
        Release Date: 01/25/2024
        Address: 0xE8000
        Runtime Size: 96 kB
        ROM Size: 64 kB
        Characteristics:
                BIOS characteristics not supported
                Targeted content distribution is supported
        BIOS Revision: 1.0

System Information
        Manufacturer: Google
        Product Name: Google Compute Engine
        Version: Not Specified
        Serial Number: GoogleCloud-ABCDEF1234567890ABCDEF1234567890
        UUID: 78fc848d-b909-4b53-a917-50d5203d88ac
        Wake-up Type: Power Switch
        SKU Number: Not Specified
        Family: Not Specified

Base Board Information
        Manufacturer: Google
        Product Name: Google Compute Engine
        Version: Not Specified
        Serial Number: Board-GoogleCloud-ABCDEF1234567890ABCDEF1234567890
        Asset Tag: 78FC848D-B909-4B53-A917-50D5203D88AC
        Features:
                Board is a hosting board
        Location In Chassis: Not Specified
        Type: Motherboard

System Boot Information
        Status: No errors detected

      """.encode("utf-8")
      session.Reply(result)

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=hardware.CollectHardwareInfo,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers={
            rrg_pb2.Action.EXECUTE_SIGNED_COMMAND: ExecuteSignedCommandHandler,
        },
    )

    results = flow_test_lib.GetFlowResults(client_id, flow_id)

    self.assertLen(results, 1)

    result = results[0]

    self.assertEqual(
        result.serial_number,
        "GoogleCloud-ABCDEF1234567890ABCDEF1234567890",
    )

    self.assertEqual(result.system_manufacturer, "Google")
    self.assertEqual(result.system_product_name, "Google Compute Engine")
    self.assertEqual(result.system_uuid, "78fc848d-b909-4b53-a917-50d5203d88ac")
    self.assertEqual(result.system_sku_number, "Not Specified")
    self.assertEqual(result.system_family, "Not Specified")

    self.assertEqual(result.bios_vendor, "Google")
    self.assertEqual(result.bios_version, "Google")
    self.assertEqual(result.bios_release_date, "01/25/2024")
    self.assertEqual(result.bios_rom_size, "64 kB")
    self.assertEqual(result.bios_revision, "1.0")

  @db_test_lib.WithDatabase
  def testRRGLinux_NonZeroExitSignal(self, db: abstract_db.Database) -> None:
    # TODO: Load signed commands from the `.textproto` file to
    # ensure integrity.
    command = rrg_execute_signed_command_pb2.Command()
    command.path.raw_bytes = "/usr/sbin/dmidecode".encode("utf-8")
    command.args_signed.append("-q")
    signed_command = signed_commands_pb2.SignedCommand()
    signed_command.id = "dmidecode_q"
    signed_command.operating_system = signed_commands_pb2.SignedCommand.OS.LINUX
    signed_command.command = command.SerializeToString()
    signed_command.ed25519_signature = b"\x00" * 64
    db.WriteSignedCommand(signed_command)

    client_id = db_test_utils.InitializeRRGClient(
        db,
        os_type=rrg_os_pb2.LINUX,
    )

    def ExecuteSignedCommandHandler(session: rrg_test_lib.Session) -> None:
      args = rrg_execute_signed_command_pb2.Args()
      assert session.args.Unpack(args)

      result = rrg_execute_signed_command_pb2.Result()
      result.exit_signal = 42
      session.Reply(result)

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=hardware.CollectHardwareInfo,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers={
            rrg_pb2.Action.EXECUTE_SIGNED_COMMAND: ExecuteSignedCommandHandler,
        },
    )

    flow_obj = db.ReadFlowObject(client_id=client_id, flow_id=flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.ERROR)
    self.assertIn("signal: 42", flow_obj.error_message)

  def testLinux(self):
    assert data_store.REL_DB is not None
    db: abstract_db.Database = data_store.REL_DB

    creator = db_test_utils.InitializeUser(db)
    client_id = db_test_utils.InitializeClient(db)

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Linux"
    db.WriteClientSnapshot(snapshot)

    flow_id = flow_test_lib.StartAndRunFlow(
        hardware.CollectHardwareInfo,
        action_mocks.ExecuteCommandActionMock(
            cmd="/usr/sbin/dmidecode",
            exit_status=0,
            stdout="""\
BIOS Information
        Vendor: Google
        Version: Google
        Release Date: 01/25/2024
        Address: 0xE8000
        Runtime Size: 96 kB
        ROM Size: 64 kB
        Characteristics:
                BIOS characteristics not supported
                Targeted content distribution is supported
        BIOS Revision: 1.0

System Information
        Manufacturer: Google
        Product Name: Google Compute Engine
        Version: Not Specified
        Serial Number: GoogleCloud-ABCDEF1234567890ABCDEF1234567890
        UUID: 78fc848d-b909-4b53-a917-50d5203d88ac
        Wake-up Type: Power Switch
        SKU Number: Not Specified
        Family: Not Specified

Base Board Information
        Manufacturer: Google
        Product Name: Google Compute Engine
        Version: Not Specified
        Serial Number: Board-GoogleCloud-ABCDEF1234567890ABCDEF1234567890
        Asset Tag: 78FC848D-B909-4B53-A917-50D5203D88AC
        Features:
                Board is a hosting board
        Location In Chassis: Not Specified
        Type: Motherboard

System Boot Information
        Status: No errors detected

""".encode("utf-8"),
        ),
        client_id=client_id,
        creator=creator,
    )

    results = flow_test_lib.GetFlowResults(client_id, flow_id)

    self.assertLen(results, 1)

    result = results[0]

    self.assertEqual(
        result.serial_number,
        "GoogleCloud-ABCDEF1234567890ABCDEF1234567890",
    )

    self.assertEqual(result.system_manufacturer, "Google")
    self.assertEqual(result.system_product_name, "Google Compute Engine")
    self.assertEqual(result.system_uuid, "78fc848d-b909-4b53-a917-50d5203d88ac")
    self.assertEqual(result.system_sku_number, "Not Specified")
    self.assertEqual(result.system_family, "Not Specified")

    self.assertEqual(result.bios_vendor, "Google")
    self.assertEqual(result.bios_version, "Google")
    self.assertEqual(result.bios_release_date, "01/25/2024")
    self.assertEqual(result.bios_rom_size, "64 kB")
    self.assertEqual(result.bios_revision, "1.0")

  @db_test_lib.WithDatabase
  def testRRGMacos(self, db: abstract_db.Database) -> None:
    # TODO: Load signed commands from the `.textproto` file to
    # ensure integrity.
    command = rrg_execute_signed_command_pb2.Command()
    command.path.raw_bytes = "/usr/sbin/system_profiler".encode("utf-8")
    command.args_signed.append("-xml")
    command.args_signed.append("SPHardwareDataType")
    signed_command = signed_commands_pb2.SignedCommand()
    signed_command.id = "system_profiler_xml_sphardware"
    signed_command.operating_system = signed_commands_pb2.SignedCommand.OS.MACOS
    signed_command.command = command.SerializeToString()
    signed_command.ed25519_signature = b"\x00" * 64
    db.WriteSignedCommand(signed_command)

    client_id = db_test_utils.InitializeRRGClient(
        db,
        os_type=rrg_os_pb2.MACOS,
    )

    def ExecuteSignedCommandHandler(session: rrg_test_lib.Session) -> None:
      args = rrg_execute_signed_command_pb2.Args()
      assert session.args.Unpack(args)

      if not args.timeout.ToNanoseconds() > 0:
        raise RuntimeError(f"No command timeout: {args.timeout}")

      command = rrg_execute_signed_command_pb2.Command()
      command.ParseFromString(args.command)

      if command.path.raw_bytes != "/usr/sbin/system_profiler".encode("utf-8"):
        raise RuntimeError(f"Unexpected command path: {command.path}")

      if command.args_signed != ["-xml", "SPHardwareDataType"]:
        raise RuntimeError(f"Unexpected command args: {command.args_signed}")

      result = rrg_execute_signed_command_pb2.Result()
      result.exit_code = 0
      result.stdout = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<array>
        <dict>
                <key>_SPCommandLineArguments</key>
                <array>
                        <string>/usr/sbin/system_profiler</string>
                        <string>-nospawn</string>
                        <string>-xml</string>
                        <string>SPHardwareDataType</string>
                        <string>-detailLevel</string>
                        <string>full</string>
                </array>
                <key>_SPCompletionInterval</key>
                <real>0.044379949569702148</real>
                <key>_SPResponseTime</key>
                <real>0.19805097579956055</real>
                <key>_dataType</key>
                <string>SPHardwareDataType</string>
                <key>_detailLevel</key>
                <string>-2</string>
                <key>_items</key>
                <array>
                        <dict>
                                <key>_name</key>
                                <string>hardware_overview</string>
                                <key>activation_lock_status</key>
                                <string>activation_lock_disabled</string>
                                <key>boot_rom_version</key>
                                <string>10151.101.3</string>
                                <key>chip_type</key>
                                <string>Apple M1 Pro</string>
                                <key>machine_model</key>
                                <string>MacBookPro18,3</string>
                                <key>machine_name</key>
                                <string>MacBook Pro</string>
                                <key>model_number</key>
                                <string>Z15G000PCB/A</string>
                                <key>number_processors</key>
                                <string>proc 8:6:2</string>
                                <key>os_loader_version</key>
                                <string>10151.101.3</string>
                                <key>physical_memory</key>
                                <string>16 GB</string>
                                <key>platform_UUID</key>
                                <string>48F1516D-23AB-4242-BB81-6F32D193D3F2</string>
                                <key>provisioning_UDID</key>
                                <string>00008000-0001022E3FD6901A</string>
                                <key>serial_number</key>
                                <string>XY42EDVYNN</string>
                        </dict>
                </array>
                <key>_parentDataType</key>
                <string>SPRootDataType</string>
                <key>_timeStamp</key>
                <date>2024-04-12T15:26:32Z</date>
                <key>_versionInfo</key>
                <dict>
                        <key>com.apple.SystemProfiler.SPPlatformReporter</key>
                        <string>1500</string>
                </dict>
        </dict>
</array>
</plist>
      """.encode("utf-8")
      session.Reply(result)

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=hardware.CollectHardwareInfo,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers={
            rrg_pb2.Action.EXECUTE_SIGNED_COMMAND: ExecuteSignedCommandHandler,
        },
    )

    results = flow_test_lib.GetFlowResults(client_id, flow_id)

    self.assertLen(results, 1)

    result = results[0]
    self.assertEqual(result.serial_number, "XY42EDVYNN")
    self.assertEqual(result.system_product_name, "MacBookPro18,3")
    self.assertEqual(result.system_uuid, "48F1516D-23AB-4242-BB81-6F32D193D3F2")
    self.assertEqual(result.bios_version, "10151.101.3")

  @db_test_lib.WithDatabase
  def testRRGMacos_NonZeroExitSignal(self, db: abstract_db.Database) -> None:
    # TODO: Load signed commands from the `.textproto` file to
    # ensure integrity.
    command = rrg_execute_signed_command_pb2.Command()
    command.path.raw_bytes = "/usr/sbin/system_profiler".encode("utf-8")
    command.args_signed.append("-xml")
    command.args_signed.append("SPHardwareDataType")
    signed_command = signed_commands_pb2.SignedCommand()
    signed_command.id = "system_profiler_xml_sphardware"
    signed_command.operating_system = signed_commands_pb2.SignedCommand.OS.MACOS
    signed_command.command = command.SerializeToString()
    signed_command.ed25519_signature = b"\x00" * 64
    db.WriteSignedCommand(signed_command)

    client_id = db_test_utils.InitializeRRGClient(
        db,
        os_type=rrg_os_pb2.MACOS,
    )

    def ExecuteSignedCommandHandler(session: rrg_test_lib.Session) -> None:
      args = rrg_execute_signed_command_pb2.Args()
      assert session.args.Unpack(args)

      result = rrg_execute_signed_command_pb2.Result()
      result.exit_signal = 42
      session.Reply(result)

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=hardware.CollectHardwareInfo,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers={
            rrg_pb2.Action.EXECUTE_SIGNED_COMMAND: ExecuteSignedCommandHandler,
        },
    )

    flow_obj = db.ReadFlowObject(client_id=client_id, flow_id=flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.ERROR)
    self.assertIn("signal: 42", flow_obj.error_message)

  def testMacos(self):
    assert data_store.REL_DB is not None
    db: abstract_db.Database = data_store.REL_DB

    creator = db_test_utils.InitializeUser(db)
    client_id = db_test_utils.InitializeClient(db)

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Darwin"
    db.WriteClientSnapshot(snapshot)

    flow_id = flow_test_lib.StartAndRunFlow(
        hardware.CollectHardwareInfo,
        action_mocks.ExecuteCommandActionMock(
            cmd="/usr/sbin/system_profiler",
            args=["-xml", "SPHardwareDataType"],
            exit_status=0,
            stdout="""\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<array>
        <dict>
                <key>_SPCommandLineArguments</key>
                <array>
                        <string>/usr/sbin/system_profiler</string>
                        <string>-nospawn</string>
                        <string>-xml</string>
                        <string>SPHardwareDataType</string>
                        <string>-detailLevel</string>
                        <string>full</string>
                </array>
                <key>_SPCompletionInterval</key>
                <real>0.044379949569702148</real>
                <key>_SPResponseTime</key>
                <real>0.19805097579956055</real>
                <key>_dataType</key>
                <string>SPHardwareDataType</string>
                <key>_detailLevel</key>
                <string>-2</string>
                <key>_items</key>
                <array>
                        <dict>
                                <key>_name</key>
                                <string>hardware_overview</string>
                                <key>activation_lock_status</key>
                                <string>activation_lock_disabled</string>
                                <key>boot_rom_version</key>
                                <string>10151.101.3</string>
                                <key>chip_type</key>
                                <string>Apple M1 Pro</string>
                                <key>machine_model</key>
                                <string>MacBookPro18,3</string>
                                <key>machine_name</key>
                                <string>MacBook Pro</string>
                                <key>model_number</key>
                                <string>Z15G000PCB/A</string>
                                <key>number_processors</key>
                                <string>proc 8:6:2</string>
                                <key>os_loader_version</key>
                                <string>10151.101.3</string>
                                <key>physical_memory</key>
                                <string>16 GB</string>
                                <key>platform_UUID</key>
                                <string>48F1516D-23AB-4242-BB81-6F32D193D3F2</string>
                                <key>provisioning_UDID</key>
                                <string>00008000-0001022E3FD6901A</string>
                                <key>serial_number</key>
                                <string>XY42EDVYNN</string>
                        </dict>
                </array>
                <key>_parentDataType</key>
                <string>SPRootDataType</string>
                <key>_timeStamp</key>
                <date>2024-04-12T15:26:32Z</date>
                <key>_versionInfo</key>
                <dict>
                        <key>com.apple.SystemProfiler.SPPlatformReporter</key>
                        <string>1500</string>
                </dict>
        </dict>
</array>
</plist>
""".encode("utf-8"),
        ),
        client_id=client_id,
        creator=creator,
    )

    results = flow_test_lib.GetFlowResults(client_id, flow_id)

    self.assertLen(results, 1)

    result = results[0]
    self.assertEqual(result.serial_number, "XY42EDVYNN")
    self.assertEqual(result.system_product_name, "MacBookPro18,3")
    self.assertEqual(result.system_uuid, "48F1516D-23AB-4242-BB81-6F32D193D3F2")
    self.assertEqual(result.bios_version, "10151.101.3")

  @db_test_lib.WithDatabase
  def testRRGWindows(self, db: abstract_db.Database) -> None:
    client_id = db_test_utils.InitializeRRGClient(
        db,
        os_type=rrg_os_pb2.WINDOWS,
    )

    def QueryWmiHandler(session: rrg_test_lib.Session) -> None:
      args = rrg_query_wmi_pb2.Args()
      assert session.args.Unpack(args)

      if not args.query.strip().startswith("SELECT "):
        raise RuntimeError("Non-`SELECT` WMI query")

      if "Win32_ComputerSystemProduct" not in args.query:
        raise RuntimeError(f"Unexpected WMI query: {args.query!r}")

      result = rrg_query_wmi_pb2.Result()
      result.row["IdentifyingNumber"].string = "2S42F1S3320HFN2179FV"
      result.row["Name"].string = "42F1S3320H"
      result.row["Vendor"].string = "LEVELHO"
      result.row["Version"].string = "NumbBox Y1337"
      result.row["Caption"].string = "Computer System Product"
      session.Reply(result)

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=hardware.CollectHardwareInfo,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers={
            rrg_pb2.Action.QUERY_WMI: QueryWmiHandler,
        },
    )

    results = flow_test_lib.GetFlowResults(client_id, flow_id)

    self.assertLen(results, 1)
    self.assertEqual(results[0].serial_number, "2S42F1S3320HFN2179FV")
    self.assertEqual(results[0].system_manufacturer, "LEVELHO")

  def testWindows(self) -> None:
    assert data_store.REL_DB is not None
    db: abstract_db.Database = data_store.REL_DB

    creator = db_test_utils.InitializeUser(db)
    client_id = db_test_utils.InitializeClient(db)

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Windows"
    db.WriteClientSnapshot(snapshot)

    class ActionMock(action_mocks.ActionMock):

      def WmiQuery(
          self,
          args: rdf_client_action.WMIRequest,
      ) -> Iterator[rdf_protodict.Dict]:
        args = mig_client_action.ToProtoWMIRequest(args)

        if not args.query.upper().startswith("SELECT "):
          raise RuntimeError("Non-`SELECT` WMI query")

        if "Win32_ComputerSystemProduct" not in args.query:
          raise RuntimeError(f"Unexpected WMI query: {args.query!r}")

        result = {
            "IdentifyingNumber": "2S42F1S3320HFN2179FV",
            "Name": "42F1S3320H",
            "Vendor": "LEVELHO",
            "Version": "NumbBox Y1337",
            "Caption": "Computer System Product",
        }

        yield mig_protodict.ToRDFDict(models_protodicts.Dict(result))

    flow_id = flow_test_lib.StartAndRunFlow(
        hardware.CollectHardwareInfo,
        ActionMock(),
        client_id=client_id,
        creator=creator,
    )

    results = flow_test_lib.GetFlowResults(client_id, flow_id)

    self.assertLen(results, 1)
    self.assertEqual(results[0].serial_number, "2S42F1S3320HFN2179FV")
    self.assertEqual(results[0].system_manufacturer, "LEVELHO")


if __name__ == "__main__":
  absltest.main()
