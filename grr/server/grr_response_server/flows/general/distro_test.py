#!/usr/bin/env python
import hashlib

from absl.testing import absltest

from grr_response_client import actions
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import mig_file_finder
from grr_response_core.lib.rdfvalues import mig_protodict
from grr_response_proto import distro_pb2
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import objects_pb2
from grr_response_server import blob_store as abstract_bs
from grr_response_server import data_store
from grr_response_server.databases import db as abstract_db
from grr_response_server.databases import db_test_utils
from grr_response_server.flows.general import distro
from grr.test_lib import action_mocks
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import rrg_test_lib
from grr.test_lib import testing_startup


class CollectDistroInfoTest(flow_test_lib.FlowTestsBaseclass):

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    testing_startup.TestInit()

  def testUbuntu(self) -> None:
    assert data_store.REL_DB is not None
    db = data_store.REL_DB

    creator = db_test_utils.InitializeUser(db)
    client_id = db_test_utils.InitializeClient(db)

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Linux"
    db.WriteClientSnapshot(snapshot)

    class FakeFileFinderOS(actions.ActionPlugin):

      in_rdfvalue = rdf_file_finder.FileFinderArgs
      out_rdfvalues = [rdf_file_finder.FileFinderResult]

      def Run(self, args: rdf_file_finder.FileFinderArgs) -> None:
        args = mig_file_finder.ToProtoFileFinderArgs(args)

        if args.pathtype != jobs_pb2.PathSpec.PathType.OS:
          raise RuntimeError(f"Unexpected path type: {args.pathtype}")

        for path in args.paths:
          blob = jobs_pb2.DataBlob()

          if path == "/etc/lsb-release":
            blob.data = """\
DISTRIB_ID=Ubuntu
DISTRIB_RELEASE=22.04
DISTRIB_CODENAME=jammy
DISTRIB_DESCRIPTION="Ubuntu 22.04.4 LTS"
            """.encode("utf-8")
            mode = 0o0644
          elif path == "/usr/lib/os-release":
            blob.data = """\
PRETTY_NAME="Ubuntu 22.04.4 LTS"
NAME="Ubuntu"
VERSION_ID="22.04"
VERSION="22.04.4 LTS (Jammy Jellyfish)"
VERSION_CODENAME=jammy
ID=ubuntu
ID_LIKE=debian
HOME_URL="https://www.ubuntu.com/"
SUPPORT_URL="https://help.ubuntu.com/"
BUG_REPORT_URL="https://bugs.launchpad.net/ubuntu/"
PRIVACY_POLICY_URL="https://www.ubuntu.com/legal/terms-and-policies/privacy-policy"
UBUNTU_CODENAME=jammy
            """.encode("utf-8")
            mode = 0o0777
          else:
            continue

          self.SendReply(
              mig_protodict.ToRDFDataBlob(blob),
              session_id=rdfvalue.SessionID(flow_name="TransferStore"),
          )

          result = flows_pb2.FileFinderResult()
          result.transferred_file.chunk_size = len(blob.data)

          stat_entry = result.stat_entry
          stat_entry.st_mode = mode
          stat_entry.st_size = len(blob.data)
          stat_entry.pathspec.pathtype = jobs_pb2.PathSpec.PathType.OS
          stat_entry.pathspec.path = path

          chunk = result.transferred_file.chunks.add()
          chunk.offset = 0
          chunk.length = len(blob.data)
          chunk.digest = hashlib.sha256(blob.data).digest()

          self.SendReply(
              mig_file_finder.ToRDFFileFinderResult(result),
          )

    flow_id = flow_test_lib.StartAndRunFlow(
        distro.CollectDistroInfo,
        action_mocks.ActionMock.With({
            "FileFinderOS": FakeFileFinderOS,
        }),
        client_id=client_id,
        creator=creator,
    )

    results = flow_test_lib.GetFlowResults(client_id, flow_id)
    self.assertLen(results, 1)
    self.assertEqual(results[0].name, "Ubuntu")
    self.assertEqual(results[0].release, "22.04")
    self.assertEqual(results[0].version_major, 22)
    self.assertEqual(results[0].version_minor, 4)

  @db_test_lib.WithDatabase
  @db_test_lib.WithDatabaseBlobstore
  def testRRGUbuntu(
      self,
      db: abstract_db.Database,
      bs: abstract_bs.BlobStore,
  ) -> None:
    del bs  # Unused.

    client_id = db_test_utils.InitializeRRGClient(db)

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Linux"
    db.WriteClientSnapshot(snapshot)

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=distro.CollectDistroInfo,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/etc/lsb-release": """\
DISTRIB_ID=Ubuntu
DISTRIB_RELEASE=22.04
DISTRIB_CODENAME=jammy
DISTRIB_DESCRIPTION="Ubuntu 22.04.4 LTS"
            """.encode("utf-8"),
            "/usr/lib/os-release": """\
PRETTY_NAME="Ubuntu 22.04.4 LTS"
NAME="Ubuntu"
VERSION_ID="22.04"
VERSION="22.04.4 LTS (Jammy Jellyfish)"
VERSION_CODENAME=jammy
ID=ubuntu
ID_LIKE=debian
HOME_URL="https://www.ubuntu.com/"
SUPPORT_URL="https://help.ubuntu.com/"
BUG_REPORT_URL="https://bugs.launchpad.net/ubuntu/"
PRIVACY_POLICY_URL="https://www.ubuntu.com/legal/terms-and-policies/privacy-policy"
UBUNTU_CODENAME=jammy
            """.encode("utf-8"),
        }),
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    results = db.ReadFlowResults(client_id, flow_id, offset=0, count=1024)
    self.assertLen(results, 1)

    result = distro_pb2.CollectDistroInfoResult()
    self.assertTrue(results[0].payload.Unpack(result))
    self.assertEqual(result.name, "Ubuntu")
    self.assertEqual(result.release, "22.04")
    self.assertEqual(result.version_major, 22)
    self.assertEqual(result.version_minor, 4)

  def testFedora(self) -> None:
    assert data_store.REL_DB is not None
    db = data_store.REL_DB

    creator = db_test_utils.InitializeUser(db)
    client_id = db_test_utils.InitializeClient(db)

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Linux"
    db.WriteClientSnapshot(snapshot)

    class FakeFileFinderOS(actions.ActionPlugin):

      in_rdfvalue = rdf_file_finder.FileFinderArgs
      out_rdfvalues = [rdf_file_finder.FileFinderResult]

      def Run(self, args: rdf_file_finder.FileFinderArgs) -> None:
        args = mig_file_finder.ToProtoFileFinderArgs(args)

        if args.pathtype != jobs_pb2.PathSpec.PathType.OS:
          raise RuntimeError(f"Unexpected path type: {args.pathtype}")

        for path in args.paths:
          blob = jobs_pb2.DataBlob()

          if path in [
              "/etc/fedora-release",
              "/etc/redhat-release",
              "/etc/system-release",
          ]:
            blob.data = """\
Fedora release 39 (Thirty Nine)
            """.encode("utf-8")
          elif path == "/usr/lib/os-release":
            blob.data = """\
NAME="Fedora Linux"
VERSION="39 (Container Image)"
ID=fedora
VERSION_ID=39
VERSION_CODENAME=""
PLATFORM_ID="platform:f39"
PRETTY_NAME="Fedora Linux 39 (Container Image)"
ANSI_COLOR="0;38;2;60;110;180"
LOGO=fedora-logo-icon
CPE_NAME="cpe:/o:fedoraproject:fedora:39"
DEFAULT_HOSTNAME="fedora"
HOME_URL="https://fedoraproject.org/"
DOCUMENTATION_URL="https://docs.fedoraproject.org/en-US/fedora/f39/system-administrators-guide/"
SUPPORT_URL="https://ask.fedoraproject.org/"
BUG_REPORT_URL="https://bugzilla.redhat.com/"
REDHAT_BUGZILLA_PRODUCT="Fedora"
REDHAT_BUGZILLA_PRODUCT_VERSION=39
REDHAT_SUPPORT_PRODUCT="Fedora"
REDHAT_SUPPORT_PRODUCT_VERSION=39
SUPPORT_END=2024-11-12
VARIANT="Container Image"
VARIANT_ID=container
            """.encode("utf-8")
          else:
            continue

          self.SendReply(
              mig_protodict.ToRDFDataBlob(blob),
              session_id=rdfvalue.SessionID(flow_name="TransferStore"),
          )

          result = flows_pb2.FileFinderResult()
          result.transferred_file.chunk_size = len(blob.data)

          stat_entry = result.stat_entry
          stat_entry.st_mode = 0o0777
          stat_entry.st_size = len(blob.data)
          stat_entry.pathspec.pathtype = jobs_pb2.PathSpec.PathType.OS
          stat_entry.pathspec.path = path

          chunk = result.transferred_file.chunks.add()
          chunk.offset = 0
          chunk.length = len(blob.data)
          chunk.digest = hashlib.sha256(blob.data).digest()

          self.SendReply(
              mig_file_finder.ToRDFFileFinderResult(result),
          )

    flow_id = flow_test_lib.StartAndRunFlow(
        distro.CollectDistroInfo,
        action_mocks.ActionMock.With({
            "FileFinderOS": FakeFileFinderOS,
        }),
        client_id=client_id,
        creator=creator,
    )

    results = flow_test_lib.GetFlowResults(client_id, flow_id)
    self.assertLen(results, 1)
    self.assertEqual(results[0].name, "RedHat")
    self.assertEqual(results[0].release, "Fedora release 39 (Thirty Nine)")
    self.assertEqual(results[0].version_major, 39)

  @db_test_lib.WithDatabase
  @db_test_lib.WithDatabaseBlobstore
  def testRRGFedora(
      self,
      db: abstract_db.Database,
      bs: abstract_bs.BlobStore,
  ) -> None:
    del bs  # Unused.

    client_id = db_test_utils.InitializeRRGClient(db)

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Linux"
    db.WriteClientSnapshot(snapshot)

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=distro.CollectDistroInfo,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/etc/fedora-release": """\
Fedora release 39 (Thirty Nine)
            """.encode("utf-8"),
            "/etc/redhat-release": """\
Fedora release 39 (Thirty Nine)
            """.encode("utf-8"),
            "/etc/system-release": """\
Fedora release 39 (Thirty Nine)
            """.encode("utf-8"),
            "/usr/lib/os-release": """\
NAME="Fedora Linux"
VERSION="39 (Container Image)"
ID=fedora
VERSION_ID=39
VERSION_CODENAME=""
PLATFORM_ID="platform:f39"
PRETTY_NAME="Fedora Linux 39 (Container Image)"
ANSI_COLOR="0;38;2;60;110;180"
LOGO=fedora-logo-icon
CPE_NAME="cpe:/o:fedoraproject:fedora:39"
DEFAULT_HOSTNAME="fedora"
HOME_URL="https://fedoraproject.org/"
DOCUMENTATION_URL="https://docs.fedoraproject.org/en-US/fedora/f39/system-administrators-guide/"
SUPPORT_URL="https://ask.fedoraproject.org/"
BUG_REPORT_URL="https://bugzilla.redhat.com/"
REDHAT_BUGZILLA_PRODUCT="Fedora"
REDHAT_BUGZILLA_PRODUCT_VERSION=39
REDHAT_SUPPORT_PRODUCT="Fedora"
REDHAT_SUPPORT_PRODUCT_VERSION=39
SUPPORT_END=2024-11-12
VARIANT="Container Image"
VARIANT_ID=container
            """.encode("utf-8"),
        }),
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    results = db.ReadFlowResults(client_id, flow_id, offset=0, count=1024)
    self.assertLen(results, 1)

    result = distro_pb2.CollectDistroInfoResult()
    self.assertTrue(results[0].payload.Unpack(result))
    self.assertEqual(result.name, "RedHat")
    self.assertEqual(result.release, "Fedora release 39 (Thirty Nine)")
    self.assertEqual(result.version_major, 39)

  def testCustom(self) -> None:
    assert data_store.REL_DB is not None
    db = data_store.REL_DB

    creator = db_test_utils.InitializeUser(db)
    client_id = db_test_utils.InitializeClient(db)

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Linux"
    db.WriteClientSnapshot(snapshot)

    class FakeFileFinderOS(actions.ActionPlugin):

      in_rdfvalue = rdf_file_finder.FileFinderArgs
      out_rdfvalues = [rdf_file_finder.FileFinderResult]

      def Run(self, args: rdf_file_finder.FileFinderArgs) -> None:
        args = mig_file_finder.ToProtoFileFinderArgs(args)

        if args.pathtype != jobs_pb2.PathSpec.PathType.OS:
          raise RuntimeError(f"Unexpected path type: {args.pathtype}")

        for path in args.paths:
          blob = jobs_pb2.DataBlob()

          if path == "/etc/os-release":
            blob.data = """\
PRETTY_NAME="Debian GNU/Linux foobar"
NAME="Debian GNU/Linux foobar"
VERSION_CODENAME=foobar
ID=debian
HOME_URL="https://example.com/"
SUPPORT_URL="https://example.com/support"
BUG_REPORT_URL="https://example.com/issues"
            """.encode("utf-8")
            mode = 0o0777
          elif path == "/etc/lsb-release":
            blob.data = """\
# $Id: //depot/foo/bar/templates/lsb-release.erb#42 $
DISTRIB_CODENAME=foobar
DISTRIB_DESCRIPTION="Debian GNU/Linux foobar"
DISTRIB_ID=Debian
DISTRIB_RELEASE=foobar
GOOGLE_CODENAME=foobar
GOOGLE_ID=Foobuntu
GOOGLE_RELEASE="foobar 20220121.05.00RD"
GOOGLE_ROLE=desktop
GOOGLE_TRACK=stable
            """.encode("utf-8")
            mode = 0o0644
          else:
            continue

          self.SendReply(
              mig_protodict.ToRDFDataBlob(blob),
              session_id=rdfvalue.SessionID(flow_name="TransferStore"),
          )

          result = flows_pb2.FileFinderResult()
          result.transferred_file.chunk_size = len(blob.data)

          stat_entry = result.stat_entry
          stat_entry.st_mode = mode
          stat_entry.st_size = len(blob.data)
          stat_entry.pathspec.pathtype = jobs_pb2.PathSpec.PathType.OS
          stat_entry.pathspec.path = path

          chunk = result.transferred_file.chunks.add()
          chunk.offset = 0
          chunk.length = len(blob.data)
          chunk.digest = hashlib.sha256(blob.data).digest()

          self.SendReply(
              mig_file_finder.ToRDFFileFinderResult(result),
          )

    flow_id = flow_test_lib.StartAndRunFlow(
        distro.CollectDistroInfo,
        action_mocks.ActionMock.With({
            "FileFinderOS": FakeFileFinderOS,
        }),
        client_id=client_id,
        creator=creator,
    )

    results = flow_test_lib.GetFlowResults(client_id, flow_id)
    self.assertLen(results, 1)
    self.assertEqual(results[0].name, "Debian")
    self.assertEqual(results[0].release, "foobar")

  @db_test_lib.WithDatabase
  @db_test_lib.WithDatabaseBlobstore
  def testRRGCustom(
      self,
      db: abstract_db.Database,
      bs: abstract_bs.BlobStore,
  ) -> None:
    del bs  # Unused.

    client_id = db_test_utils.InitializeRRGClient(db)

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Linux"
    db.WriteClientSnapshot(snapshot)

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=distro.CollectDistroInfo,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/etc/os-release": """\
PRETTY_NAME="Debian GNU/Linux foobar"
NAME="Debian GNU/Linux foobar"
VERSION_CODENAME=foobar
ID=debian
HOME_URL="https://example.com/"
SUPPORT_URL="https://example.com/support"
BUG_REPORT_URL="https://example.com/issues"
            """.encode("utf-8"),
            "/etc/lsb-release": """\
# $Id: //depot/foo/bar/templates/lsb-release.erb#42 $
DISTRIB_CODENAME=foobar
DISTRIB_DESCRIPTION="Debian GNU/Linux foobar"
DISTRIB_ID=Debian
DISTRIB_RELEASE=foobar
GOOGLE_CODENAME=foobar
GOOGLE_ID=Foobuntu
GOOGLE_RELEASE="foobar 20220121.05.00RD"
GOOGLE_ROLE=desktop
GOOGLE_TRACK=stable
            """.encode("utf-8"),
        }),
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    results = db.ReadFlowResults(client_id, flow_id, offset=0, count=1024)
    self.assertLen(results, 1)

    result = distro_pb2.CollectDistroInfoResult()
    self.assertTrue(results[0].payload.Unpack(result))
    self.assertEqual(result.name, "Debian")
    self.assertEqual(result.release, "foobar")

  def testAmazon1(self):
    assert data_store.REL_DB is not None
    db = data_store.REL_DB

    creator = db_test_utils.InitializeUser(db)
    client_id = db_test_utils.InitializeClient(db)

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Linux"
    db.WriteClientSnapshot(snapshot)

    class FakeFileFinderOS(actions.ActionPlugin):

      in_rdfvalue = rdf_file_finder.FileFinderArgs
      out_rdfvalues = [rdf_file_finder.FileFinderResult]

      def Run(self, args: rdf_file_finder.FileFinderArgs) -> None:
        args = mig_file_finder.ToProtoFileFinderArgs(args)

        if args.pathtype != jobs_pb2.PathSpec.PathType.OS:
          raise RuntimeError(f"Unexpected path type: {args.pathtype}")

        for path in args.paths:
          blob = jobs_pb2.DataBlob()

          if path == "/etc/os-release":
            blob.data = """\
NAME="Amazon Linux AMI"
VERSION="2018.03"
ID="amzn"
ID_LIKE="rhel fedora"
VERSION_ID="2018.03"
PRETTY_NAME="Amazon Linux AMI 2018.03"
ANSI_COLOR="0;33"
CPE_NAME="cpe:/o:amazon:linux:2018.03:ga"
HOME_URL="http://aws.amazon.com/amazon-linux-ami/"
            """.encode("utf-8")
          elif path == "/etc/system-release":
            blob.data = """\
Amazon Linux AMI release 2018.03
            """.encode("utf-8")
          else:
            continue

          self.SendReply(
              mig_protodict.ToRDFDataBlob(blob),
              session_id=rdfvalue.SessionID(flow_name="TransferStore"),
          )

          result = flows_pb2.FileFinderResult()
          result.transferred_file.chunk_size = len(blob.data)

          stat_entry = result.stat_entry
          stat_entry.st_mode = 0o0644
          stat_entry.st_size = len(blob.data)
          stat_entry.pathspec.pathtype = jobs_pb2.PathSpec.PathType.OS
          stat_entry.pathspec.path = path

          chunk = result.transferred_file.chunks.add()
          chunk.offset = 0
          chunk.length = len(blob.data)
          chunk.digest = hashlib.sha256(blob.data).digest()

          self.SendReply(
              mig_file_finder.ToRDFFileFinderResult(result),
          )

    flow_id = flow_test_lib.StartAndRunFlow(
        distro.CollectDistroInfo,
        action_mocks.ActionMock.With({
            "FileFinderOS": FakeFileFinderOS,
        }),
        client_id=client_id,
        creator=creator,
    )

    results = flow_test_lib.GetFlowResults(client_id, flow_id)
    self.assertLen(results, 1)
    self.assertEqual(results[0].name, "Amazon Linux AMI")
    self.assertEqual(results[0].release, "Amazon Linux AMI release 2018.03")
    self.assertEqual(results[0].version_major, 2018)
    self.assertEqual(results[0].version_minor, 3)

  @db_test_lib.WithDatabase
  @db_test_lib.WithDatabaseBlobstore
  def testRRGAmazon1(
      self,
      db: abstract_db.Database,
      bs: abstract_bs.BlobStore,
  ) -> None:
    del bs  # Unused.

    client_id = db_test_utils.InitializeRRGClient(db)

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Linux"
    db.WriteClientSnapshot(snapshot)

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=distro.CollectDistroInfo,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/etc/os-release": """\
NAME="Amazon Linux AMI"
VERSION="2018.03"
ID="amzn"
ID_LIKE="rhel fedora"
VERSION_ID="2018.03"
PRETTY_NAME="Amazon Linux AMI 2018.03"
ANSI_COLOR="0;33"
CPE_NAME="cpe:/o:amazon:linux:2018.03:ga"
HOME_URL="http://aws.amazon.com/amazon-linux-ami/"
            """.encode("utf-8"),
            "/etc/system-release": """\
Amazon Linux AMI release 2018.03
            """.encode("utf-8"),
        }),
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    results = db.ReadFlowResults(client_id, flow_id, offset=0, count=1024)
    self.assertLen(results, 1)

    result = distro_pb2.CollectDistroInfoResult()
    self.assertTrue(results[0].payload.Unpack(result))
    self.assertEqual(result.name, "Amazon Linux AMI")
    self.assertEqual(result.release, "Amazon Linux AMI release 2018.03")
    self.assertEqual(result.version_major, 2018)
    self.assertEqual(result.version_minor, 3)

  def testAmazon2(self):
    assert data_store.REL_DB is not None
    db = data_store.REL_DB

    creator = db_test_utils.InitializeUser(db)
    client_id = db_test_utils.InitializeClient(db)

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Linux"
    db.WriteClientSnapshot(snapshot)

    class FakeFileFinderOS(actions.ActionPlugin):

      in_rdfvalue = rdf_file_finder.FileFinderArgs
      out_rdfvalues = [rdf_file_finder.FileFinderResult]

      def Run(self, args: rdf_file_finder.FileFinderArgs) -> None:
        args = mig_file_finder.ToProtoFileFinderArgs(args)

        if args.pathtype != jobs_pb2.PathSpec.PathType.OS:
          raise RuntimeError(f"Unexpected path type: {args.pathtype}")

        for path in args.paths:
          blob = jobs_pb2.DataBlob()

          if path == "/etc/os-release":
            blob.data = """\
NAME="Amazon Linux"
VERSION="2"
ID="amzn"
ID_LIKE="centos rhel fedora"
VERSION_ID="2"
PRETTY_NAME="Amazon Linux 2"
ANSI_COLOR="0;33"
CPE_NAME="cpe:2.3:o:amazon:amazon_linux:2"
HOME_URL="https://amazonlinux.com/"
SUPPORT_END="2025-06-30"
            """.encode("utf-8")
          elif path == "/etc/system-release":
            blob.data = """\
Amazon Linux release 2 (Karoo)
            """.encode("utf-8")
          else:
            continue

          self.SendReply(
              mig_protodict.ToRDFDataBlob(blob),
              session_id=rdfvalue.SessionID(flow_name="TransferStore"),
          )

          result = flows_pb2.FileFinderResult()
          result.transferred_file.chunk_size = len(blob.data)

          stat_entry = result.stat_entry
          stat_entry.st_mode = 0o0644
          stat_entry.st_size = len(blob.data)
          stat_entry.pathspec.pathtype = jobs_pb2.PathSpec.PathType.OS
          stat_entry.pathspec.path = path

          chunk = result.transferred_file.chunks.add()
          chunk.offset = 0
          chunk.length = len(blob.data)
          chunk.digest = hashlib.sha256(blob.data).digest()

          self.SendReply(
              mig_file_finder.ToRDFFileFinderResult(result),
          )

    flow_id = flow_test_lib.StartAndRunFlow(
        distro.CollectDistroInfo,
        action_mocks.ActionMock.With({
            "FileFinderOS": FakeFileFinderOS,
        }),
        client_id=client_id,
        creator=creator,
    )

    results = flow_test_lib.GetFlowResults(client_id, flow_id)
    self.assertLen(results, 1)
    self.assertEqual(results[0].name, "Amazon Linux")
    self.assertEqual(results[0].release, "Amazon Linux release 2 (Karoo)")
    self.assertEqual(results[0].version_major, 2)

  @db_test_lib.WithDatabase
  @db_test_lib.WithDatabaseBlobstore
  def testRRGAmazon2(
      self,
      db: abstract_db.Database,
      bs: abstract_bs.BlobStore,
  ) -> None:
    del bs  # Unused.

    client_id = db_test_utils.InitializeRRGClient(db)

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Linux"
    db.WriteClientSnapshot(snapshot)

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=distro.CollectDistroInfo,
        flow_args=rdf_flows.EmptyFlowArgs(),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/etc/os-release": """\
NAME="Amazon Linux"
VERSION="2"
ID="amzn"
ID_LIKE="centos rhel fedora"
VERSION_ID="2"
PRETTY_NAME="Amazon Linux 2"
ANSI_COLOR="0;33"
CPE_NAME="cpe:2.3:o:amazon:amazon_linux:2"
HOME_URL="https://amazonlinux.com/"
SUPPORT_END="2025-06-30"
            """.encode("utf-8"),
            "/etc/system-release": """\
Amazon Linux release 2 (Karoo)
            """.encode("utf-8"),
        }),
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    results = db.ReadFlowResults(client_id, flow_id, offset=0, count=1024)
    self.assertLen(results, 1)

    result = distro_pb2.CollectDistroInfoResult()
    self.assertTrue(results[0].payload.Unpack(result))
    self.assertEqual(result.name, "Amazon Linux")
    self.assertEqual(result.release, "Amazon Linux release 2 (Karoo)")
    self.assertEqual(result.version_major, 2)


if __name__ == "__main__":
  absltest.main()
