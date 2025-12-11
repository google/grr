#!/usr/bin/env python
import random
import string

from absl.testing import absltest

from grr_response_client import actions
from grr_response_core.lib.rdfvalues import cloud as rdf_cloud
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import mig_cloud
from grr_response_proto import cloud_pb2
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import objects_pb2
from grr_response_proto import signed_commands_pb2
from grr_response_server.databases import db as abstract_db
from grr_response_server.databases import db_test_utils
from grr_response_server.flows.general import cloud
from grr.test_lib import action_mocks
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import rrg_test_lib
from grr.test_lib import testing_startup
from grr_response_proto import rrg_pb2
from grr_response_proto.rrg import os_pb2 as rrg_os_pb2
from grr_response_proto.rrg.action import execute_signed_command_pb2 as rrg_execute_signed_command_pb2
from grr_response_proto.rrg.action import get_tcp_response_pb2 as rrg_get_tcp_response_pb2
from grr_response_proto.rrg.action import query_wmi_pb2 as rrg_query_wmi_pb2


class CollectCloudVMMetadataTest(flow_test_lib.FlowTestsBaseclass):

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    testing_startup.TestInit()

  @db_test_lib.WithDatabase
  def testRRGGoogleLinux(
      self,
      db: abstract_db.Database,
  ) -> None:
    # TODO: Load signed commands from the `.textproto` file to
    # ensure integrity.
    command = rrg_execute_signed_command_pb2.Command()
    command.path.raw_bytes = "/usr/sbin/dmidecode".encode("utf-8")
    command.args_signed.append("--string")
    command.args_signed.append("bios-version")
    signed_command = signed_commands_pb2.SignedCommand()
    signed_command.id = "dmidecode_bios_version"
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

      if command.args_signed != ["--string", "bios-version"]:
        raise RuntimeError(f"Unexpected command args: {command.args_signed}")

      result = rrg_execute_signed_command_pb2.Result()
      result.exit_code = 0
      result.stdout = "Google\n".encode("utf-8")
      session.Reply(result)

    def GetTcpResponseHandler(session: rrg_test_lib.Session) -> None:
      args = rrg_get_tcp_response_pb2.Args()
      assert session.args.Unpack(args)

      result = rrg_get_tcp_response_pb2.Result()

      if args.data.startswith(b"GET /computeMetadata/v1/instance/id"):
        result.data = "\r\n".join([
            "HTTP/1.1 200 OK",
            "Metadata-Flavor: Google",
            "Content-Type: application/text",
            "ETag: 2b5a32c29d113f891",
            "Date: Fri, 14 Feb 2025 11:47:04 GMT",
            "Server: Metadata Server for VM",
            "Content-Length: 19",
            "X-XSS-Protection: 0",
            "X-Frame-Options: SAMEORIGIN",
            "",
            "7723260132568912421",
        ]).encode("ascii")
      elif args.data.startswith(b"GET /computeMetadata/v1/instance/zone"):
        result.data = "\r\n".join([
            "HTTP/1.1 200 OK",
            "Metadata-Flavor: Google",
            "Content-Type: application/text",
            "ETag: f98eb48e18111526",
            "Date: Fri, 14 Feb 2025 11:50:42 GMT",
            "Server: Metadata Server for VM",
            "Content-Length: 41",
            "X-XSS-Protection: 0",
            "X-Frame-Options: SAMEORIGIN",
            "",
            "projects/129731223780/zones/us-central1-c",
        ]).encode("ascii")
      elif args.data.startswith(b"GET /computeMetadata/v1/instance/hostname"):
        result.data = "\r\n".join([
            "HTTP/1.1 200 OK",
            "Metadata-Flavor: Google",
            "Content-Type: application/text",
            "ETag: ab7d150a1647c491",
            "Date: Fri, 14 Feb 2025 11:54:59 GMT",
            "Server: Metadata Server for VM",
            "Content-Length: 50",
            "X-XSS-Protection: 0",
            "X-Frame-Options: SAMEORIGIN",
            "",
            "foo-linux.us-central1-c.c.example-project.internal",
        ]).encode("ascii")
      elif args.data.startswith(b"GET /computeMetadata/v1/instance/machine-ty"):
        result.data = "\r\n".join([
            "HTTP/1.1 200 OK",
            "Metadata-Flavor: Google",
            "Content-Type: application/text",
            "ETag: 7022c1f053098db5",
            "Date: Fri, 14 Feb 2025 11:58:37 GMT",
            "Server: Metadata Server for VM",
            "Content-Length: 44",
            "X-XSS-Protection: 0",
            "X-Frame-Options: SAMEORIGIN",
            "",
            "projects/129731223780/machineTypes/e2-medium",
        ]).encode("ascii")
      elif args.data.startswith(b"GET /computeMetadata/v1/project/project-id"):
        result.data = "\r\n".join([
            "HTTP/1.1 200 OK",
            "Metadata-Flavor: Google",
            "Content-Type: application/text",
            "ETag: cafcbcb2a5e35ee3",
            "Date: Fri, 14 Feb 2025 12:00:55 GMT",
            "Server: Metadata Server for VM",
            "Content-Length: 15",
            "X-XSS-Protection: 0",
            "X-Frame-Options: SAMEORIGIN",
            "",
            "example-project",
        ]).encode("ascii")
      else:
        result.data = "\r\n".join([
            "HTTP/1.1 404 Not Found",
            "Metadata-Flavor: Google",
            "Date: Fri, 14 Feb 2025 12:03:10 GMT",
            "Content-Type: text/html; charset=UTF-8",
            "Server: Metadata Server for VM",
            "Content-Length: 9",
            "X-XSS-Protection: 0",
            "X-Frame-Options: SAMEORIGIN",
            "",
            "Not Found",
        ])

      session.Reply(result)

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=cloud.CollectCloudVMMetadata,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers={
            rrg_pb2.Action.EXECUTE_SIGNED_COMMAND: ExecuteSignedCommandHandler,
            rrg_pb2.Action.GET_TCP_RESPONSE: GetTcpResponseHandler,
        },
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    flow_results = db.ReadFlowResults(client_id, flow_id, offset=0, count=1024)
    self.assertLen(flow_results, 1)

    result = cloud_pb2.CollectCloudVMMetadataResult()
    assert flow_results[0].payload.Unpack(result)

    self.assertEqual(
        result.vm_metadata.cloud_type,
        jobs_pb2.CloudInstance.GOOGLE,
    )
    self.assertEqual(
        result.vm_metadata.google.instance_id,
        "7723260132568912421",
    )
    self.assertEqual(
        result.vm_metadata.google.zone,
        "projects/129731223780/zones/us-central1-c",
    )
    self.assertEqual(
        result.vm_metadata.google.hostname,
        "foo-linux.us-central1-c.c.example-project.internal",
    )
    self.assertEqual(
        result.vm_metadata.google.machine_type,
        "projects/129731223780/machineTypes/e2-medium",
    )
    self.assertEqual(
        result.vm_metadata.google.project_id,
        "example-project",
    )
    self.assertEqual(
        result.vm_metadata.google.unique_id,
        "us-central1-c/example-project/7723260132568912421",
    )

  @db_test_lib.WithDatabase
  def testRRGAmazonLinux(
      self,
      db: abstract_db.Database,
  ) -> None:
    # TODO: Load signed commands from the `.textproto` file to
    # ensure integrity.
    command = rrg_execute_signed_command_pb2.Command()
    command.path.raw_bytes = "/usr/sbin/dmidecode".encode("utf-8")
    command.args_signed.append("--string")
    command.args_signed.append("bios-version")
    signed_command = signed_commands_pb2.SignedCommand()
    signed_command.id = "dmidecode_bios_version"
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

      if command.args_signed != ["--string", "bios-version"]:
        raise RuntimeError(f"Unexpected command args: {command.args_signed}")

      result = rrg_execute_signed_command_pb2.Result()
      result.exit_code = 0
      result.stdout = "4.2.amazon\n".encode("utf-8")
      session.Reply(result)

    token = "".join(random.choices(string.ascii_letters + string.digits, k=128))

    def GetTcpResponseHandler(session: rrg_test_lib.Session) -> None:
      args = rrg_get_tcp_response_pb2.Args()
      assert session.args.Unpack(args)

      result = rrg_get_tcp_response_pb2.Result()

      # TODO: The responses below were generated with the help of
      # Gemini as we do not have access to the real AWS instance. From what I've
      # checked it nailed the sample format for each property when compared to
      # the real-world data we currently have in our database. Nevertheless, it
      # would be nice to verify them.

      if args.data.startswith(b"GET /latest/api/token"):
        result.data = "\r\n".join([
            "HTTP/1.1 200 OK",
            "Date: Tue, 23 May 2023 12:00:00 GMT",
            "Server: EC2ws",
            "Content-Type: text/plain",
            f"Content-Length: {len(token)}",
            "",
            f"{token}",
        ]).encode("ascii")
        session.Reply(result)
        return

      if args.data.startswith(b"GET /latest/meta-data/"):
        if f"X-aws-ec2-metadata-token: {token}".encode() not in args.data:
          result.data = "\r\n".join([
              "HTTP/1.1 401 Unauthorized",
              "Date: Tue, 23 May 2023 12:00:00 GMT",
              "Server: EC2ws",
              "Content-Type: text/plain",
              "Content-Length: 12",
              "",
              "Unauthorized",
          ]).encode("ascii")
          session.Reply(result)
          return

      if args.data.startswith(b"GET /latest/meta-data/instance-id"):
        result.data = "\r\n".join([
            "HTTP/1.1 200 OK",
            "Date: Tue, 23 May 2023 12:00:00 GMT",
            "Server: EC2ws",
            "Content-Type: text/plain",
            "Content-Length: 19",
            "",
            "i-0123456789abcdef0",
        ]).encode("ascii")
      elif args.data.startswith(b"GET /latest/meta-data/instance-type"):
        result.data = "\r\n".join([
            "HTTP/1.1 200 OK",
            "Date: Tue, 23 May 2023 12:00:00 GMT",
            "Server: EC2ws",
            "Content-Type: text/plain",
            "Content-Length: 8",
            "",
            "m5.large",
        ]).encode("ascii")
      elif args.data.startswith(b"GET /latest/meta-data/ami-id"):
        result.data = "\r\n".join([
            "HTTP/1.1 200 OK",
            "Date: Tue, 23 May 2023 12:00:00 GMT",
            "Server: EC2ws",
            "Content-Type: text/plain",
            "Content-Length: 21",
            "",
            "ami-0123456789abcdef0",
        ]).encode("ascii")
      elif args.data.startswith(b"GET /latest/meta-data/hostname"):
        result.data = "\r\n".join([
            "HTTP/1.1 200 OK",
            "Content-Type: application/text",
            "Content-Length: 28",
            "",
            "ip-192-168-1-10.ec2.internal",
        ]).encode("ascii")
      elif args.data.startswith(b"GET /latest/meta-data/public-hostname"):
        result.data = "\r\n".join([
            "HTTP/1.1 200 OK",
            "Date: Tue, 23 May 2023 12:00:00 GMT",
            "Server: EC2ws",
            "Content-Type: text/plain",
            "Content-Length: 40",
            "",
            "ec2-203-0-113-25.compute-1.amazonaws.com",
        ]).encode("ascii")
      else:
        result.data = "\r\n".join([
            "HTTP/1.1 404 Not Found",
            "Date: Tue, 23 May 2023 12:00:00 GMT",
            "Server: EC2ws",
            "Content-Type: text/plain",
            "Content-Length: 9",
            "",
            "Not Found",
        ]).encode("ascii")

      session.Reply(result)

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=cloud.CollectCloudVMMetadata,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers={
            rrg_pb2.Action.EXECUTE_SIGNED_COMMAND: ExecuteSignedCommandHandler,
            rrg_pb2.Action.GET_TCP_RESPONSE: GetTcpResponseHandler,
        },
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    flow_results = db.ReadFlowResults(client_id, flow_id, offset=0, count=1024)
    self.assertLen(flow_results, 1)

    result = cloud_pb2.CollectCloudVMMetadataResult()
    assert flow_results[0].payload.Unpack(result)

    self.assertEqual(
        result.vm_metadata.cloud_type,
        jobs_pb2.CloudInstance.AMAZON,
    )
    self.assertEqual(
        result.vm_metadata.amazon.instance_id,
        "i-0123456789abcdef0",
    )
    self.assertEqual(
        result.vm_metadata.amazon.instance_type,
        "m5.large",
    )
    self.assertEqual(
        result.vm_metadata.amazon.ami_id,
        "ami-0123456789abcdef0",
    )
    self.assertEqual(
        result.vm_metadata.amazon.hostname,
        "ip-192-168-1-10.ec2.internal",
    )
    self.assertEqual(
        result.vm_metadata.amazon.public_hostname,
        "ec2-203-0-113-25.compute-1.amazonaws.com",
    )

  @db_test_lib.WithDatabase
  def testRRGGoogleWindows(
      self,
      db: abstract_db.Database,
  ) -> None:
    client_id = db_test_utils.InitializeRRGClient(
        db,
        os_type=rrg_os_pb2.WINDOWS,
    )

    def QueryWmiHandler(session: rrg_test_lib.Session) -> None:
      args = rrg_query_wmi_pb2.Args()
      assert session.args.Unpack(args)

      if not args.query.strip().startswith("SELECT "):
        raise RuntimeError("Non-`SELECT` WMI query")

      if "Win32_Service" not in args.query or "GCEAgent" not in args.query:
        raise RuntimeError(f"Unexpected WMI query: {args.query!r}")

      result = rrg_query_wmi_pb2.Result()
      result.row["Name"].string = "GCEAgent"
      session.Reply(result)

    def GetTcpResponseHandler(session: rrg_test_lib.Session) -> None:
      args = rrg_get_tcp_response_pb2.Args()
      assert session.args.Unpack(args)

      result = rrg_get_tcp_response_pb2.Result()

      if args.data.startswith(b"GET /computeMetadata/v1/instance/id"):
        result.data = "\r\n".join([
            "HTTP/1.1 200 OK",
            "Metadata-Flavor: Google",
            "X-XSS-Protection: 0",
            "X-Frame-Options: SAMEORIGIN",
            "Content-Length: 19",
            "Content-Type: application/text",
            "Date: Mon, 17 Feb 2025 12:34:54 GMT",
            "ETag: f4ffd4d91ab0534d",
            "Server: Metadata Server for VM",
            "",
            "3123781986532187642",
        ]).encode("ascii")
      elif args.data.startswith(b"GET /computeMetadata/v1/instance/zone"):
        result.data = "\r\n".join([
            "HTTP/1.1 200 OK",
            "Metadata-Flavor: Google",
            "X-XSS-Protection: 0",
            "X-Frame-Options: SAMEORIGIN",
            "Content-Length: 42",
            "Content-Type: application/text",
            "Date: Mon, 17 Feb 2025 12:42:03 GMT",
            "ETag: 2c5e68c56e3b0de0",
            "Server: Metadata Server for VM",
            "",
            "projects/129731223780/zones/europe-west4-c",
        ]).encode("ascii")
      elif args.data.startswith(b"GET /computeMetadata/v1/instance/hostname"):
        result.data = "\r\n".join([
            "HTTP/1.1 200 OK",
            "Metadata-Flavor: Google",
            "X-XSS-Protection: 0",
            "X-Frame-Options: SAMEORIGIN",
            "Content-Length: 52",
            "Content-Type: application/text",
            "Date: Mon, 17 Feb 2025 12:53:23 GMT",
            "ETag: 4c738723ac99b4bc",
            "Server: Metadata Server for VM",
            "",
            "winvm.europe-west4-c.c.foo-prod.example.com.internal",
        ]).encode("ascii")
      elif args.data.startswith(b"GET /computeMetadata/v1/instance/machine-ty"):
        result.data = "\r\n".join([
            "HTTP/1.1 200 OK",
            "Metadata-Flavor: Google",
            "X-XSS-Protection: 0",
            "X-Frame-Options: SAMEORIGIN",
            "Content-Length: 49",
            "Content-Type: application/text",
            "Date: Mon, 17 Feb 2025 12:56:58 GMT",
            "ETag: 78b4f619d1b91316",
            "Server: Metadata Server for VM",
            "",
            "projects/129731223780/machineTypes/n2d-standard-8",
        ]).encode("ascii")
      elif args.data.startswith(b"GET /computeMetadata/v1/project/project-id"):
        result.data = "\r\n".join([
            "HTTP/1.1 200 OK",
            "Metadata-Flavor: Google",
            "X-XSS-Protection: 0",
            "X-Frame-Options: SAMEORIGIN",
            "Content-Length: 20",
            "Content-Type: application/text",
            "Date: Mon, 17 Feb 2025 12:59:25 GMT",
            "ETag: 9d27c903e79b4996",
            "Server: Metadata Server for VM",
            "",
            "example.com:foo-prod",
        ]).encode("ascii")
      else:
        result.data = "\r\n".join([
            "HTTP/1.1 404 NotFound",
            "Metadata-Flavor: Google",
            "Date: Mon, 17 Feb 2025 13:12:06 GMT",
            "Server: Metadata",
            "Server: Server",
            "Server: for",
            "Server: VM",
            "X-XSS-Protection: 0",
            "X-Frame-Options: SAMEORIGIN",
            "Content-Type: text/html; charset=UTF-8",
            "Content-Length: 9",
            "",
            "Not Found",
        ]).encode("ascii")

      session.Reply(result)

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=cloud.CollectCloudVMMetadata,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers={
            rrg_pb2.Action.GET_TCP_RESPONSE: GetTcpResponseHandler,
            rrg_pb2.Action.QUERY_WMI: QueryWmiHandler,
        },
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    flow_results = db.ReadFlowResults(client_id, flow_id, offset=0, count=1024)
    self.assertLen(flow_results, 1)

    result = cloud_pb2.CollectCloudVMMetadataResult()
    assert flow_results[0].payload.Unpack(result)

    self.assertEqual(
        result.vm_metadata.cloud_type,
        jobs_pb2.CloudInstance.GOOGLE,
    )
    self.assertEqual(
        result.vm_metadata.google.instance_id,
        "3123781986532187642",
    )
    self.assertEqual(
        result.vm_metadata.google.zone,
        "projects/129731223780/zones/europe-west4-c",
    )
    self.assertEqual(
        result.vm_metadata.google.hostname,
        "winvm.europe-west4-c.c.foo-prod.example.com.internal",
    )
    self.assertEqual(
        result.vm_metadata.google.machine_type,
        "projects/129731223780/machineTypes/n2d-standard-8",
    )
    self.assertEqual(
        result.vm_metadata.google.project_id,
        "example.com:foo-prod",
    )
    self.assertEqual(
        result.vm_metadata.google.unique_id,
        "europe-west4-c/example.com:foo-prod/3123781986532187642",
    )

  @db_test_lib.WithDatabase
  def testRRGAmazonWindows(
      self,
      db: abstract_db.Database,
  ) -> None:
    client_id = db_test_utils.InitializeRRGClient(
        db,
        os_type=rrg_os_pb2.WINDOWS,
    )

    def QueryWmiHandler(session: rrg_test_lib.Session) -> None:
      args = rrg_query_wmi_pb2.Args()
      assert session.args.Unpack(args)

      if not args.query.strip().startswith("SELECT "):
        raise RuntimeError("Non-`SELECT` WMI query")

      if "Win32_Service" not in args.query or "AWSLiteAgent" not in args.query:
        raise RuntimeError(f"Unexpected WMI query: {args.query!r}")

      result = rrg_query_wmi_pb2.Result()
      result.row["Name"].string = "AWSLiteAgent"
      session.Reply(result)

    token = "".join(random.choices(string.ascii_letters + string.digits, k=128))

    def GetTcpResponseHandler(session: rrg_test_lib.Session) -> None:
      args = rrg_get_tcp_response_pb2.Args()
      assert session.args.Unpack(args)

      result = rrg_get_tcp_response_pb2.Result()

      if args.data.startswith(b"GET /latest/api/token"):
        result.data = "\r\n".join([
            "HTTP/1.1 200 OK",
            "Date: Tue, 23 May 2023 12:00:00 GMT",
            "Server: EC2ws",
            "Content-Type: text/plain",
            f"Content-Length: {len(token)}",
            "",
            f"{token}",
        ]).encode("ascii")
        session.Reply(result)
        return

      if args.data.startswith(b"GET /latest/meta-data/"):
        if f"X-aws-ec2-metadata-token: {token}".encode() not in args.data:
          result.data = "\r\n".join([
              "HTTP/1.1 401 Unauthorized",
              "Date: Tue, 23 May 2023 12:00:00 GMT",
              "Server: EC2ws",
              "Content-Type: text/plain",
              "Content-Length: 12",
              "",
              "Unauthorized",
          ]).encode("ascii")
          session.Reply(result)
          return

      if args.data.startswith(b"GET /latest/meta-data/instance-id"):
        result.data = "\r\n".join([
            "HTTP/1.1 200 OK",
            "Date: Tue, 23 May 2023 12:00:00 GMT",
            "Server: EC2ws",
            "Content-Type: text/plain",
            "Content-Length: 19",
            "",
            "i-0123456789abcdef9",
        ]).encode("ascii")
      elif args.data.startswith(b"GET /latest/meta-data/instance-type"):
        result.data = "\r\n".join([
            "HTTP/1.1 200 OK",
            "Date: Tue, 23 May 2023 12:00:00 GMT",
            "Server: EC2ws",
            "Content-Type: text/plain",
            "Content-Length: 8",
            "",
            "m5.large",
        ]).encode("ascii")
      elif args.data.startswith(b"GET /latest/meta-data/ami-id"):
        result.data = "\r\n".join([
            "HTTP/1.1 200 OK",
            "Date: Tue, 23 May 2023 12:00:00 GMT",
            "Server: EC2ws",
            "Content-Type: text/plain",
            "Content-Length: 21",
            "",
            "ami-0123456789abcdef9",
        ]).encode("ascii")
      elif args.data.startswith(b"GET /latest/meta-data/hostname"):
        result.data = "\r\n".join([
            "HTTP/1.1 200 OK",
            "Content-Type: application/text",
            "Content-Length: 28",
            "",
            "ip-192-168-1-19.ec2.internal",
        ]).encode("ascii")
      else:
        result.data = "\r\n".join([
            "HTTP/1.1 404 Not Found",
            "Date: Tue, 23 May 2023 12:00:00 GMT",
            "Server: EC2ws",
            "Content-Type: text/plain",
            "Content-Length: 9",
            "",
            "Not Found",
        ]).encode("ascii")
      session.Reply(result)

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=cloud.CollectCloudVMMetadata,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers={
            rrg_pb2.Action.GET_TCP_RESPONSE: GetTcpResponseHandler,
            rrg_pb2.Action.QUERY_WMI: QueryWmiHandler,
        },
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    flow_results = db.ReadFlowResults(client_id, flow_id, offset=0, count=1024)
    self.assertLen(flow_results, 1)

    result = cloud_pb2.CollectCloudVMMetadataResult()
    assert flow_results[0].payload.Unpack(result)

    self.assertEqual(
        result.vm_metadata.cloud_type,
        jobs_pb2.CloudInstance.AMAZON,
    )
    self.assertEqual(
        result.vm_metadata.amazon.instance_id,
        "i-0123456789abcdef9",
    )
    self.assertEqual(
        result.vm_metadata.amazon.instance_type,
        "m5.large",
    )
    self.assertEqual(
        result.vm_metadata.amazon.ami_id,
        "ami-0123456789abcdef9",
    )
    self.assertEqual(
        result.vm_metadata.amazon.hostname,
        "ip-192-168-1-19.ec2.internal",
    )

  @db_test_lib.WithDatabase
  def testGoogle(
      self,
      db: abstract_db.Database,
  ) -> None:
    creator = db_test_utils.InitializeUser(db)
    client_id = db_test_utils.InitializeClient(db)

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Linux"
    db.WriteClientSnapshot(snapshot)

    class FakeGetCloudVMMetadata(actions.ActionPlugin):

      in_rdfvalue = rdf_cloud.CloudMetadataRequests
      out_rdfvalues = [rdf_cloud.CloudMetadataResponses]

      def Run(self, args: rdf_cloud.CloudMetadataRequests) -> None:
        args = mig_cloud.ToProtoCloudMetadataRequests(args)

        result = flows_pb2.CloudMetadataResponses()
        result.instance_type = jobs_pb2.CloudInstance.InstanceType.GOOGLE

        for request in args.requests:
          instance_type = request.instance_type
          if instance_type != jobs_pb2.CloudInstance.InstanceType.GOOGLE:
            continue

          if request.label == "instance_id":
            response = result.responses.add()
            response.label = "instance_id"
            response.text = "1122334455667788990"
          elif request.label == "zone":
            response = result.responses.add()
            response.label = "zone"
            response.text = "projects/1234567890/zones/us-central1-a"
          elif request.label == "project_id":
            response = result.responses.add()
            response.label = "project_id"
            response.text = "example.com:foobar"
          elif request.label == "hostname":
            response = result.responses.add()
            response.label = "hostname"
            response.text = "quux.c.foobar.example.com.internal"
          elif request.label == "machine_type":
            response = result.responses.add()
            response.label = "machine_type"
            response.text = "projects/1234567890/machineTypes/n2-standard-8"
          else:
            raise RuntimeError(f"Unexpected request label: {request.label}")

        if result.responses:
          self.SendReply(mig_cloud.ToRDFCloudMetadataResponses(result))

    flow_id = flow_test_lib.StartAndRunFlow(
        cloud.CollectCloudVMMetadata,
        action_mocks.ActionMock.With({
            "GetCloudVMMetadata": FakeGetCloudVMMetadata,
        }),
        client_id=client_id,
        creator=creator,
    )

    results = flow_test_lib.GetFlowResults(client_id, flow_id)
    self.assertLen(results, 1)

    self.assertEqual(
        results[0].vm_metadata.cloud_type,
        jobs_pb2.CloudInstance.InstanceType.GOOGLE,
    )
    self.assertEqual(
        results[0].vm_metadata.google.unique_id,
        "us-central1-a/example.com:foobar/1122334455667788990",
    )
    self.assertEqual(
        results[0].vm_metadata.google.zone,
        "projects/1234567890/zones/us-central1-a",
    )
    self.assertEqual(
        results[0].vm_metadata.google.project_id,
        "example.com:foobar",
    )
    self.assertEqual(
        results[0].vm_metadata.google.instance_id,
        "1122334455667788990",
    )
    self.assertEqual(
        results[0].vm_metadata.google.hostname,
        "quux.c.foobar.example.com.internal",
    )
    self.assertEqual(
        results[0].vm_metadata.google.machine_type,
        "projects/1234567890/machineTypes/n2-standard-8",
    )

  @db_test_lib.WithDatabase
  def testAmazon(
      self,
      db: abstract_db.Database,
  ) -> None:
    creator = db_test_utils.InitializeUser(db)
    client_id = db_test_utils.InitializeClient(db)

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Linux"
    db.WriteClientSnapshot(snapshot)

    class FakeGetCloudVMMetadata(actions.ActionPlugin):

      in_rdfvalue = rdf_cloud.CloudMetadataRequests
      out_rdfvalues = [rdf_cloud.CloudMetadataResponses]

      def Run(self, args: rdf_cloud.CloudMetadataRequests) -> None:
        args = mig_cloud.ToProtoCloudMetadataRequests(args)

        result = flows_pb2.CloudMetadataResponses()
        result.instance_type = jobs_pb2.CloudInstance.InstanceType.AMAZON

        for request in args.requests:
          instance_type = request.instance_type
          if instance_type != jobs_pb2.CloudInstance.InstanceType.AMAZON:
            continue

          if request.label == "instance_id":
            response = result.responses.add()
            response.label = "instance_id"
            response.text = "i-06904aca710c59ff5"
          elif request.label == "ami_id":
            response = result.responses.add()
            response.label = "ami_id"
            response.text = "ami-12345678901a12b12"
          elif request.label == "hostname":
            response = result.responses.add()
            response.label = "hostname"
            response.text = "ip-21-47-0-17.example.com"
          elif request.label == "public_hostname":
            response = result.responses.add()
            response.label = "public_hostname"
            response.text = "ec2-42-121-168-192.compute-1.amazonaws.com"
          elif request.label == "instance_type":
            response = result.responses.add()
            response.label = "instance_type"
            response.text = "t2.medium"
          else:
            raise RuntimeError(f"Unexpected request label: {request.label}")

        if result.responses:
          self.SendReply(mig_cloud.ToRDFCloudMetadataResponses(result))

    flow_id = flow_test_lib.StartAndRunFlow(
        cloud.CollectCloudVMMetadata,
        action_mocks.ActionMock.With({
            "GetCloudVMMetadata": FakeGetCloudVMMetadata,
        }),
        client_id=client_id,
        creator=creator,
    )

    results = flow_test_lib.GetFlowResults(client_id, flow_id)
    self.assertLen(results, 1)

    self.assertEqual(
        results[0].vm_metadata.cloud_type,
        jobs_pb2.CloudInstance.InstanceType.AMAZON,
    )
    self.assertEqual(
        results[0].vm_metadata.amazon.instance_id,
        "i-06904aca710c59ff5",
    )
    self.assertEqual(
        results[0].vm_metadata.amazon.ami_id,
        "ami-12345678901a12b12",
    )
    self.assertEqual(
        results[0].vm_metadata.amazon.hostname,
        "ip-21-47-0-17.example.com",
    )
    self.assertEqual(
        results[0].vm_metadata.amazon.public_hostname,
        "ec2-42-121-168-192.compute-1.amazonaws.com",
    )
    self.assertEqual(
        results[0].vm_metadata.amazon.instance_type,
        "t2.medium",
    )


if __name__ == "__main__":
  absltest.main()
