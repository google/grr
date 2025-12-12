#!/usr/bin/env python
from collections.abc import Iterator
import datetime
import hashlib

from absl.testing import absltest

from grr_response_client import actions
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import mig_client_action
from grr_response_core.lib.rdfvalues import mig_file_finder
from grr_response_core.lib.rdfvalues import mig_protodict
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import objects_pb2
from grr_response_server import data_store
from grr_response_server.databases import db as abstract_db
from grr_response_server.databases import db_test_utils
from grr_response_server.flows.general import software
from grr_response_server.models import protodicts as models_protodicts
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import testing_startup


class CollectInstalledSoftwareTest(flow_test_lib.FlowTestsBaseclass):

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    testing_startup.TestInit()

  def testLinuxDebianPre3478(self) -> None:
    assert data_store.REL_DB is not None
    db: abstract_db.Database = data_store.REL_DB

    creator = db_test_utils.InitializeUser(db)
    client_id = db_test_utils.InitializeClient(db)

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Linux"
    snapshot.startup_info.client_info.client_version = 3478
    db.WriteClientSnapshot(snapshot)

    flow_id = flow_test_lib.StartAndRunFlow(
        software.CollectInstalledSoftware,
        action_mocks.ExecuteCommandActionMock(
            cmd="/usr/bin/dpkg",
            args=["--list"],
            exit_status=0,
            stdout="""\
Desired=Unknown/Install/Remove/Purge/Hold
| Status=Not/Inst/Conf-files/Unpacked/halF-conf/Half-inst/trig-aWait/Trig-pend
|/ Err?=(none)/Reinst-required (Status,Err: uppercase=bad)
||/ Name    Version         Architecture Description
+++-=======-===============-============-=======================================================
ii  7zip    23.01+dfsg-7    amd64        7-Zip file archiver with a high compression ratio
ii  acl     2.3.1-6         amd64        access control list - utilities
ii  adduser 3.137           all          add and remove users and groups
ii  bash    5.2.21-2        amd64        GNU Bourne Again SHell
ii  sudo    1.9.15p5-2      amd64        Provide limited super user privileges to specific users
ii  xorg    1:7.7+23+build1 amd64        X.Org X Window System
""".encode("utf-8"),
        ),
        client_id=client_id,
        creator=creator,
    )

    results = flow_test_lib.GetFlowResults(client_id, flow_id)

    self.assertLen(results, 1)

    packages_by_name = {
        package.name: package for package in results[0].packages
    }

    self.assertLen(packages_by_name, 6)

    self.assertEqual(packages_by_name["7zip"].version, "23.01+dfsg-7")
    self.assertEqual(packages_by_name["7zip"].architecture, "amd64")
    self.assertNotEmpty(packages_by_name["7zip"].description)

    self.assertEqual(packages_by_name["acl"].version, "2.3.1-6")
    self.assertEqual(packages_by_name["acl"].architecture, "amd64")
    self.assertNotEmpty(packages_by_name["acl"].description)

    self.assertEqual(packages_by_name["adduser"].version, "3.137")
    self.assertEqual(packages_by_name["adduser"].architecture, "all")
    self.assertNotEmpty(packages_by_name["adduser"].description)

    self.assertEqual(packages_by_name["bash"].version, "5.2.21-2")
    self.assertEqual(packages_by_name["bash"].architecture, "amd64")
    self.assertNotEmpty(packages_by_name["bash"].description)

    self.assertEqual(packages_by_name["sudo"].version, "1.9.15p5-2")
    self.assertEqual(packages_by_name["sudo"].architecture, "amd64")
    self.assertNotEmpty(packages_by_name["sudo"].description)

    self.assertEqual(packages_by_name["xorg"].version, "1:7.7+23+build1")
    self.assertEqual(packages_by_name["xorg"].architecture, "amd64")
    self.assertNotEmpty(packages_by_name["xorg"].description)

  def testLinuxDebianPost3478(self) -> None:
    assert data_store.REL_DB is not None
    db: abstract_db.Database = data_store.REL_DB

    creator = db_test_utils.InitializeUser(db)
    client_id = db_test_utils.InitializeClient(db)

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Linux"
    snapshot.startup_info.client_info.client_version = 3479
    db.WriteClientSnapshot(snapshot)

    flow_id = flow_test_lib.StartAndRunFlow(
        software.CollectInstalledSoftware,
        action_mocks.ExecuteCommandActionMock(
            cmd="/usr/bin/dpkg-query",
            exit_status=0,
            stdout="""\
7zip|23.01+dfsg-12|amd64||7-Zip file archiver with a high compression ratio
acl|2.3.2-1|amd64||access control list - utilities
adduser|3.137|all||add and remove users and groups
bash|5.2.21-2.1|amd64||GNU Bourne Again SHell
libgtk-3-0|3.24.41-1|amd64|gtk+3.0|GTK graphical user interface library
sudo|1.9.15p5-3+gl0|amd64||Provide limited super user privileges to specific users
telnet|0.17+2.5-3|all|inetutils (2:2.5-3)|transitional dummy package for inetutils-telnet default switch
xorg|1:7.7+23+build1|amd64||X.Org X Window System
xserver-xorg|1:7.7+23+build1|amd64|xorg|X.Org X server
""".encode("utf-8"),
        ),
        client_id=client_id,
        creator=creator,
    )

    results = flow_test_lib.GetFlowResults(client_id, flow_id)

    self.assertLen(results, 1)

    packages_by_name = {
        package.name: package for package in results[0].packages
    }

    self.assertLen(packages_by_name, 9)

    zip7 = packages_by_name["7zip"]
    self.assertEqual(zip7.version, "23.01+dfsg-12")
    self.assertEqual(zip7.architecture, "amd64")
    self.assertNotEmpty(zip7.description)

    acl = packages_by_name["acl"]
    self.assertEqual(acl.version, "2.3.2-1")
    self.assertEqual(acl.architecture, "amd64")
    self.assertNotEmpty(acl.description)

    adduser = packages_by_name["adduser"]
    self.assertEqual(adduser.version, "3.137")
    self.assertEqual(adduser.architecture, "all")
    self.assertNotEmpty(adduser.description)

    bash = packages_by_name["bash"]
    self.assertEqual(bash.version, "5.2.21-2.1")
    self.assertEqual(bash.architecture, "amd64")
    self.assertNotEmpty(bash.description)

    libgtk = packages_by_name["libgtk-3-0"]
    self.assertEqual(libgtk.version, "3.24.41-1")
    self.assertEqual(libgtk.architecture, "amd64")
    self.assertEqual(libgtk.source_deb, "gtk+3.0")
    self.assertNotEmpty(libgtk.description)

    telnet = packages_by_name["telnet"]
    self.assertEqual(telnet.version, "0.17+2.5-3")
    self.assertEqual(telnet.architecture, "all")
    self.assertEqual(telnet.source_deb, "inetutils (2:2.5-3)")
    self.assertNotEmpty(telnet.description)

    sudo = packages_by_name["sudo"]
    self.assertEqual(sudo.version, "1.9.15p5-3+gl0")
    self.assertEqual(sudo.architecture, "amd64")
    self.assertNotEmpty(sudo.description)

    xorg = packages_by_name["xorg"]
    self.assertEqual(xorg.version, "1:7.7+23+build1")
    self.assertEqual(xorg.architecture, "amd64")
    self.assertNotEmpty(xorg.description)

    xserver_xorg = packages_by_name["xserver-xorg"]
    self.assertEqual(xserver_xorg.version, "1:7.7+23+build1")
    self.assertEqual(xserver_xorg.architecture, "amd64")
    self.assertEqual(xserver_xorg.source_deb, "xorg")
    self.assertNotEmpty(xserver_xorg.description)

  def testLinuxDebianPost3478DpkgFallback(self) -> None:
    assert data_store.REL_DB is not None
    db: abstract_db.Database = data_store.REL_DB

    creator = db_test_utils.InitializeUser(db)
    client_id = db_test_utils.InitializeClient(db)

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Linux"
    snapshot.startup_info.client_info.client_version = 3479
    db.WriteClientSnapshot(snapshot)

    class ActionMock(action_mocks.ActionMock):

      def ExecuteCommand(
          self,
          args: rdf_client_action.ExecuteRequest,
      ) -> Iterator[rdf_client_action.ExecuteResponse]:
        args = mig_client_action.ToProtoExecuteRequest(args)
        result = jobs_pb2.ExecuteResponse()

        if args.cmd == "/usr/bin/dpkg-query":
          result.exit_status = 1
          result.stderr = "failed because reasons".encode("utf-8")
        elif args.cmd == "/usr/bin/dpkg":
          result.exit_status = 0
          result.stdout = """\
Desired=Unknown/Install/Remove/Purge/Hold
| Status=Not/Inst/Conf-files/Unpacked/halF-conf/Half-inst/trig-aWait/Trig-pend
|/ Err?=(none)/Reinst-required (Status,Err: uppercase=bad)
||/ Name             Version         Architecture Description
+++-================-===============-============-==============================================================
ii  7zip             23.01+dfsg-12   amd64        7-Zip file archiver with a high compression ratio
ii  acl              2.3.2-1         amd64        access control list - utilities
ii  adduser          3.137           all          add and remove users and groups
ii  bash             5.2.21-2.1      amd64        GNU Bourne Again SHell
rc  libgtk-3-0:amd64 3.24.41-1       amd64        GTK graphical user interface library
ii  sudo             1.9.15p5-3+gl0  amd64        Provide limited super user privileges to specific users
ii  telnet           0.17+2.5-3      all          transitional dummy package for inetutils-telnet default switch
ii  xorg             1:7.7+23+build1 amd64        X.Org X Window System
ii  xserver-xorg     1:7.7+23+build1 amd64        X.Org X server
""".encode("utf-8")
        else:
          raise RuntimeError(f"Unexpected command: {args.cmd}")

        yield mig_client_action.ToRDFExecuteResponse(result)

    flow_id = flow_test_lib.StartAndRunFlow(
        software.CollectInstalledSoftware,
        ActionMock(),
        client_id=client_id,
        creator=creator,
    )

    results = flow_test_lib.GetFlowResults(client_id, flow_id)

    self.assertLen(results, 1)

    packages_by_name = {
        package.name: package for package in results[0].packages
    }

    self.assertLen(packages_by_name, 9)

    zip7 = packages_by_name["7zip"]
    self.assertEqual(zip7.version, "23.01+dfsg-12")
    self.assertEqual(zip7.architecture, "amd64")
    self.assertNotEmpty(zip7.description)

    acl = packages_by_name["acl"]
    self.assertEqual(acl.version, "2.3.2-1")
    self.assertEqual(acl.architecture, "amd64")
    self.assertNotEmpty(acl.description)

    adduser = packages_by_name["adduser"]
    self.assertEqual(adduser.version, "3.137")
    self.assertEqual(adduser.architecture, "all")
    self.assertNotEmpty(adduser.description)

    bash = packages_by_name["bash"]
    self.assertEqual(bash.version, "5.2.21-2.1")
    self.assertEqual(bash.architecture, "amd64")
    self.assertNotEmpty(bash.description)

    libgtk = packages_by_name["libgtk-3-0:amd64"]
    self.assertEqual(libgtk.version, "3.24.41-1")
    self.assertEqual(libgtk.architecture, "amd64")
    self.assertNotEmpty(libgtk.description)

    telnet = packages_by_name["telnet"]
    self.assertEqual(telnet.version, "0.17+2.5-3")
    self.assertEqual(telnet.architecture, "all")
    self.assertNotEmpty(telnet.description)

    sudo = packages_by_name["sudo"]
    self.assertEqual(sudo.version, "1.9.15p5-3+gl0")
    self.assertEqual(sudo.architecture, "amd64")
    self.assertNotEmpty(sudo.description)

    xorg = packages_by_name["xorg"]
    self.assertEqual(xorg.version, "1:7.7+23+build1")
    self.assertEqual(xorg.architecture, "amd64")
    self.assertNotEmpty(xorg.description)

    xserver_xorg = packages_by_name["xserver-xorg"]
    self.assertEqual(xserver_xorg.version, "1:7.7+23+build1")
    self.assertEqual(xserver_xorg.architecture, "amd64")
    self.assertNotEmpty(xserver_xorg.description)

  def testLinuxFedoraPre3473(self) -> None:
    assert data_store.REL_DB is not None
    db: abstract_db.Database = data_store.REL_DB

    creator = db_test_utils.InitializeUser(db)
    client_id = db_test_utils.InitializeClient(db)

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Linux"
    snapshot.startup_info.client_info.client_version = 3473
    db.WriteClientSnapshot(snapshot)

    flow_id = flow_test_lib.StartAndRunFlow(
        software.CollectInstalledSoftware,
        action_mocks.ExecuteCommandActionMock(
            cmd="/bin/rpm",
            args=["-qa"],
            exit_status=0,
            stdout="""\
bash-5.2.21-1.fc39.x86_64
ca-certificates-2023.2.60_v7.0.306-2.fc39.noarch
elfutils-default-yama-scope-0.190-1.fc39.noarch
grep-3.11-3.fc39.x86_64
gzip-1.12-6.fc39.x86_64
python3-3.12.0-1.fc39.x86_64
yum-4.18.1-2.fc39.noarch
rpm-4.19.0-1.fc39.x86_64
""".encode("utf-8"),
        ),
        client_id=client_id,
        creator=creator,
    )

    results = flow_test_lib.GetFlowResults(client_id, flow_id)

    self.assertLen(results, 1)

    packages_by_name = {
        package.name: package for package in results[0].packages
    }

    self.assertLen(packages_by_name, 8)

    # TODO: Update version checks once know what the proper way
    # forward for reporting it is.

    bash = packages_by_name["bash"]
    self.assertEqual(bash.version, "5.2.21-1.fc39")
    self.assertEqual(bash.architecture, "x86_64")

    ca_certificates = packages_by_name["ca-certificates"]
    self.assertEqual(ca_certificates.version, "2023.2.60_v7.0.306-2.fc39")
    self.assertEqual(ca_certificates.architecture, "noarch")

    elfutils = packages_by_name["elfutils-default-yama-scope"]
    self.assertEqual(elfutils.version, "0.190-1.fc39")
    self.assertEqual(elfutils.architecture, "noarch")

    grep = packages_by_name["grep"]
    self.assertEqual(grep.version, "3.11-3.fc39")
    self.assertEqual(grep.architecture, "x86_64")

    gzip = packages_by_name["gzip"]
    self.assertEqual(gzip.version, "1.12-6.fc39")
    self.assertEqual(gzip.architecture, "x86_64")

    python3 = packages_by_name["python3"]
    self.assertEqual(python3.version, "3.12.0-1.fc39")
    self.assertEqual(python3.architecture, "x86_64")

    yum = packages_by_name["yum"]
    self.assertEqual(yum.version, "4.18.1-2.fc39")
    self.assertEqual(packages_by_name["yum"].architecture, "noarch")

    rpm = packages_by_name["rpm"]
    self.assertEqual(rpm.version, "4.19.0-1.fc39")
    self.assertEqual(rpm.architecture, "x86_64")

  def testLinuxFedoraPost3473(self) -> None:
    assert data_store.REL_DB is not None
    db: abstract_db.Database = data_store.REL_DB

    creator = db_test_utils.InitializeUser(db)
    client_id = db_test_utils.InitializeClient(db)

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Linux"
    snapshot.startup_info.client_info.client_version = 3474
    db.WriteClientSnapshot(snapshot)

    flow_id = flow_test_lib.StartAndRunFlow(
        software.CollectInstalledSoftware,
        action_mocks.ExecuteCommandActionMock(
            cmd="/bin/rpm",
            exit_status=0,
            stdout="""\
bash|(none)|5.2.26|1.fc39|x86_64|1711525869|Fedora Project|bash-5.2.26-1.fc39.src.rpm
ca-certificates|(none)|2023.2.60_v7.0.306|2.fc39|noarch|1711525871|Fedora Project|ca-certificates-2023.2.60_v7.0.306-2.fc39.src.rpm
elfutils-default-yama-scope|(none)|0.191|2.fc39|noarch|1711525870|Fedora Project|elfutils-0.191-2.fc39.src.rpm
grep|(none)|3.11|3.fc39|x86_64|1711525871|Fedora Project|grep-3.11-3.fc39.src.rpm
gzip|(none)|1.12|6.fc39|x86_64|1711525875|Fedora Project|gzip-1.12-6.fc39.src.rpm
python3|(none)|3.12.2|2.fc39|x86_64|1711525873|Fedora Project|python3.12-3.12.2-2.fc39.src.rpm
yum|(none)|4.19.0|1.fc39|noarch|1711525875|Fedora Project|dnf-4.19.0-1.fc39.src.rpm
rpm|(none)|4.19.1.1|1.fc39|x86_64|1711525876|Fedora Project|rpm-4.19.1.1-1.fc39.src.rpm
vim-minimal|2|9.1.181|1.fc39|x86_64|1711525876|Fedora Project|vim-9.1.181-1.fc39.src.rpm
gpg-pubkey|(none)|18b8e74c|62f2920f|(none)|1711525880|(none)|(none)
            """.encode("utf-8"),
        ),
        client_id=client_id,
        creator=creator,
    )

    results = flow_test_lib.GetFlowResults(client_id, flow_id)

    self.assertLen(results, 1)

    packages_by_name = {
        package.name: package for package in results[0].packages
    }

    self.assertLen(packages_by_name, 10)

    # TODO: Update version checks once know what the proper way
    # forward for reporting it is.

    bash = packages_by_name["bash"]
    self.assertEqual(bash.version, "5.2.26-1.fc39")
    self.assertEqual(bash.architecture, "x86_64")
    self.assertEqual(bash.installed_on, 1711525869)
    self.assertEqual(bash.publisher, "Fedora Project")
    self.assertEqual(bash.source_rpm, "bash-5.2.26-1.fc39.src.rpm")

    ca_certificates = packages_by_name["ca-certificates"]
    self.assertEqual(ca_certificates.version, "2023.2.60_v7.0.306-2.fc39")
    self.assertEqual(ca_certificates.architecture, "noarch")
    self.assertEqual(ca_certificates.installed_on, 1711525871)
    self.assertEqual(ca_certificates.publisher, "Fedora Project")

    elfutils = packages_by_name["elfutils-default-yama-scope"]
    self.assertEqual(elfutils.version, "0.191-2.fc39")
    self.assertEqual(elfutils.architecture, "noarch")
    self.assertEqual(elfutils.installed_on, 1711525870)
    self.assertEqual(elfutils.publisher, "Fedora Project")
    self.assertEqual(elfutils.source_rpm, "elfutils-0.191-2.fc39.src.rpm")

    grep = packages_by_name["grep"]
    self.assertEqual(grep.version, "3.11-3.fc39")
    self.assertEqual(grep.architecture, "x86_64")
    self.assertEqual(grep.installed_on, 1711525871)
    self.assertEqual(grep.publisher, "Fedora Project")
    self.assertEqual(grep.source_rpm, "grep-3.11-3.fc39.src.rpm")

    gzip = packages_by_name["gzip"]
    self.assertEqual(gzip.version, "1.12-6.fc39")
    self.assertEqual(gzip.architecture, "x86_64")
    self.assertEqual(gzip.installed_on, 1711525875)
    self.assertEqual(gzip.publisher, "Fedora Project")
    self.assertEqual(gzip.source_rpm, "gzip-1.12-6.fc39.src.rpm")

    python3 = packages_by_name["python3"]
    self.assertEqual(python3.version, "3.12.2-2.fc39")
    self.assertEqual(python3.architecture, "x86_64")
    self.assertEqual(python3.installed_on, 1711525873)
    self.assertEqual(python3.publisher, "Fedora Project")
    self.assertEqual(python3.source_rpm, "python3.12-3.12.2-2.fc39.src.rpm")

    yum = packages_by_name["yum"]
    self.assertEqual(yum.version, "4.19.0-1.fc39")
    self.assertEqual(yum.architecture, "noarch")
    self.assertEqual(yum.installed_on, 1711525875)
    self.assertEqual(yum.publisher, "Fedora Project")
    self.assertEqual(yum.source_rpm, "dnf-4.19.0-1.fc39.src.rpm")

    rpm = packages_by_name["rpm"]
    self.assertEqual(rpm.version, "4.19.1.1-1.fc39")
    self.assertEqual(rpm.architecture, "x86_64")
    self.assertEqual(rpm.installed_on, 1711525876)
    self.assertEqual(rpm.publisher, "Fedora Project")
    self.assertEqual(rpm.source_rpm, "rpm-4.19.1.1-1.fc39.src.rpm")

    vim_minimal = packages_by_name["vim-minimal"]
    self.assertEqual(vim_minimal.version, "9.1.181-1.fc39")
    self.assertEqual(vim_minimal.architecture, "x86_64")
    self.assertEqual(vim_minimal.installed_on, 1711525876)
    self.assertEqual(vim_minimal.publisher, "Fedora Project")
    self.assertEqual(vim_minimal.epoch, 2)
    self.assertEqual(vim_minimal.source_rpm, "vim-9.1.181-1.fc39.src.rpm")

    gpg_pubkey = packages_by_name["gpg-pubkey"]
    self.assertEqual(gpg_pubkey.version, "18b8e74c-62f2920f")
    self.assertEqual(gpg_pubkey.installed_on, 1711525880)
    self.assertFalse(gpg_pubkey.HasField("epoch"))
    self.assertFalse(gpg_pubkey.HasField("architecture"))
    self.assertFalse(gpg_pubkey.HasField("vendor"))
    self.assertFalse(gpg_pubkey.HasField("source_rpm"))

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

        if "Win32_Product" in args.query:
          for result in [
              {
                  "Name": "Rust 1.76 (MSVC 64-bit)",
                  "InstallDate": "20231229",
                  "Version": "1.75.0.0",
                  "Vendor": "The Rust Project Developers",
                  "Description": "Rust 1.75 (MSVC 64-bit)",
              },
              {
                  "Name": "Python 3.11.3 Core Interpreter (64-bit)",
                  "InstallDate": "20230523",
                  "Version": "3.11.3150.0",
                  "Vendor": "Python Software Foundation",
                  "Description": "Python 3.11.3 Core Interpreter (64-bit)",
              },
              {
                  "Name": "Google Chrome",
                  "InstallDate": "20230920",
                  "Version": "122.0.6261.128",
                  "Vendor": "Google LLC",
                  "Description": "Google Chrome",
              },
              {
                  "Name": "7-Zip 22.01 (x64 edition)",
                  "InstallDate": "20230320",
                  "Version": "22.01.00.0",
                  "Vendor": "Igor Pavlov",
                  "Description": "7-Zip 22.01 (x64 edition)",
              },
              {
                  "Name": "AMD Settings",
                  "InstallDate": "20230320",
                  "Version": "2022.1025.1410.1936",
                  "Vendor": "Advanced Micro Devices, Inc.",
                  "Description": "AMD Settings",
              },
          ]:
            yield mig_protodict.ToRDFDict(models_protodicts.Dict(result))
        elif "Win32_QuickFixEngineering" in args.query:
          for result in [
              {
                  "HotFixID": "KB5033909",
                  "InstalledOn": "1/10/2024",
                  "InstalledBy": "NT AUTHORITY\\SYSTEM",
                  "Caption": "http://support.microsoft.com/?kbid=5033909",
                  "Description": "Update",
              },
              {
                  "HotFixID": "KB4577586",
                  "InstalledOn": "2/22/2023",
                  "InstalledBy": "",
                  "Caption": "https://support.microsoft.com/help/4577586",
                  "Description": "Update",
              },
              {
                  "HotFixID": "KB5012170",
                  "InstalledOn": "2/22/2023",
                  "InstalledBy": "",
                  "Caption": "https://support.microsoft.com/help/5012170",
                  "Description": "Security Update",
              },
              {
                  "HotFixID": "KB5035845",
                  "InstalledOn": "3/13/2024",
                  "InstalledBy": "NT AUTHORITY\\SYSTEM",
                  "Caption": "https://support.microsoft.com/help/5035845",
                  "Description": "Security Update",
              },
              {
                  "HotFixID": "KB5034224",
                  "InstalledOn": "2/14/2024",
                  "InstalledBy": "NT AUTHORITY\\SYSTEM",
                  "Caption": "",
                  "Description": "Update",
              },
          ]:
            yield mig_protodict.ToRDFDict(models_protodicts.Dict(result))
        else:
          raise RuntimeError(f"Unexpected WMI query: {args.query!r}")

    flow_id = flow_test_lib.StartAndRunFlow(
        software.CollectInstalledSoftware,
        ActionMock(),
        client_id=client_id,
        creator=creator,
    )

    results = flow_test_lib.GetFlowResults(client_id, flow_id)

    self.assertLen(results, 2)

    packages_by_name = {
        package.name: package for package in results[0].packages
    }

    self.assertLen(packages_by_name, 5)

    rust = packages_by_name["Rust 1.76 (MSVC 64-bit)"]
    self.assertEqual(rust.version, "1.75.0.0")
    self.assertEqual(rust.publisher, "The Rust Project Developers")
    self.assertEqual(
        rust.installed_on / 1_000_000,
        datetime.datetime(year=2023, month=12, day=29).timestamp(),
    )

    python = packages_by_name["Python 3.11.3 Core Interpreter (64-bit)"]
    self.assertEqual(python.version, "3.11.3150.0")
    self.assertEqual(python.publisher, "Python Software Foundation")
    self.assertEqual(
        python.installed_on / 1_000_000,
        datetime.datetime(year=2023, month=5, day=23).timestamp(),
    )

    chrome = packages_by_name["Google Chrome"]
    self.assertEqual(chrome.version, "122.0.6261.128")
    self.assertEqual(chrome.publisher, "Google LLC")
    self.assertEqual(
        chrome.installed_on / 1_000_000,
        datetime.datetime(year=2023, month=9, day=20).timestamp(),
    )

    zip7 = packages_by_name["7-Zip 22.01 (x64 edition)"]
    self.assertEqual(zip7.version, "22.01.00.0")
    self.assertEqual(zip7.publisher, "Igor Pavlov")
    self.assertEqual(
        zip7.installed_on / 1_000_000,
        datetime.datetime(year=2023, month=3, day=20).timestamp(),
    )

    amd = packages_by_name["AMD Settings"]
    self.assertEqual(amd.version, "2022.1025.1410.1936")
    self.assertEqual(amd.publisher, "Advanced Micro Devices, Inc.")
    self.assertEqual(
        amd.installed_on / 1_000_000,
        datetime.datetime(year=2023, month=3, day=20).timestamp(),
    )

    packages_by_name = {
        package.name: package for package in results[1].packages
    }

    self.assertLen(packages_by_name, 5)

    self.assertEqual(
        packages_by_name["KB5033909"].installed_by,
        "NT AUTHORITY\\SYSTEM",
    )
    self.assertEqual(
        packages_by_name["KB5033909"].installed_on / 1_000_000,
        datetime.datetime(year=2024, month=1, day=10).timestamp(),
    )
    self.assertIn(
        "http://support.microsoft.com/?kbid=5033909",
        packages_by_name["KB5033909"].description,
    )
    self.assertIn(
        "Update",
        packages_by_name["KB5033909"].description,
    )

    self.assertEqual(
        packages_by_name["KB4577586"].installed_on / 1_000_000,
        datetime.datetime(year=2023, month=2, day=22).timestamp(),
    )
    self.assertIn(
        "https://support.microsoft.com/help/4577586",
        packages_by_name["KB4577586"].description,
    )
    self.assertIn(
        "Update",
        packages_by_name["KB4577586"].description,
    )

    self.assertEqual(
        packages_by_name["KB5012170"].installed_on / 1_000_000,
        datetime.datetime(year=2023, month=2, day=22).timestamp(),
    )
    self.assertIn(
        "https://support.microsoft.com/help/5012170",
        packages_by_name["KB5012170"].description,
    )
    self.assertIn(
        "Security Update",
        packages_by_name["KB5012170"].description,
    )

    self.assertEqual(
        packages_by_name["KB5035845"].installed_by,
        "NT AUTHORITY\\SYSTEM",
    )
    self.assertEqual(
        packages_by_name["KB5035845"].installed_on / 1_000_000,
        datetime.datetime(year=2024, month=3, day=13).timestamp(),
    )
    self.assertIn(
        "https://support.microsoft.com/help/5035845",
        packages_by_name["KB5035845"].description,
    )
    self.assertIn(
        "Security Update",
        packages_by_name["KB5035845"].description,
    )

    self.assertEqual(
        packages_by_name["KB5034224"].installed_by,
        "NT AUTHORITY\\SYSTEM",
    )
    self.assertIn(
        "Update",
        packages_by_name["KB5034224"].description,
    )

  def testMacos(self) -> None:
    assert data_store.REL_DB is not None
    db: abstract_db.Database = data_store.REL_DB

    creator = db_test_utils.InitializeUser(db)
    client_id = db_test_utils.InitializeClient(db)

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Darwin"
    db.WriteClientSnapshot(snapshot)

    class FakeFileFinderOS(actions.ActionPlugin):

      in_rdfvalue = rdf_file_finder.FileFinderArgs
      out_rdfvalues = [rdf_file_finder.FileFinderResult]

      def Run(self, args: rdf_file_finder.FileFinderArgs) -> None:
        args = mig_file_finder.ToProtoFileFinderArgs(args)

        if args.pathtype != jobs_pb2.PathSpec.PathType.OS:
          raise RuntimeError(f"Unexpected path type: {args.pathtype}")

        if list(args.paths) != ["/Library/Receipts/InstallHistory.plist"]:
          raise RuntimeError(f"Unexpected paths: {args.paths}")

        blob = jobs_pb2.DataBlob()
        blob.data = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<array>
        <dict>
                <key>date</key>
                <date>2023-07-17T08:45:50Z</date>
                <key>displayName</key>
                <string>macOS 13.4.1</string>
                <key>displayVersion</key>
                <string>13.4.1</string>
                <key>processName</key>
                <string>softwareupdated</string>
        </dict>
        <dict>
                <key>date</key>
                <date>2023-07-17T08:56:15Z</date>
                <key>displayName</key>
                <string>grrd</string>
                <key>displayVersion</key>
                <string></string>
                <key>packageIdentifiers</key>
                <array>
                        <string>com.google.corp.grrd</string>
                </array>
                <key>processName</key>
                <string>installer</string>
        </dict>
        <dict>
                <key>date</key>
                <date>2024-05-08T13:13:12Z</date>
                <key>displayName</key>
                <string>osquery</string>
                <key>displayVersion</key>
                <string></string>
                <key>packageIdentifiers</key>
                <array>
                        <string>io.osquery.agent</string>
                </array>
                <key>processName</key>
                <string>installer</string>
        </dict>
</array>
</plist>
        """.encode("utf-8")

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
        stat_entry.pathspec.path = "/Library/Receipts/InstallHistory.plist"

        chunk = result.transferred_file.chunks.add()
        chunk.offset = 0
        chunk.length = len(blob.data)
        chunk.digest = hashlib.sha256(blob.data).digest()

        self.SendReply(
            mig_file_finder.ToRDFFileFinderResult(result),
        )

    flow_id = flow_test_lib.StartAndRunFlow(
        software.CollectInstalledSoftware,
        action_mocks.ActionMock.With({
            "FileFinderOS": FakeFileFinderOS,
        }),
        client_id=client_id,
        creator=creator,
    )

    results = flow_test_lib.GetFlowResults(client_id, flow_id)
    self.assertLen(results, 1)

    packages_by_name = {
        package.name: package for package in results[0].packages
    }

    self.assertLen(packages_by_name, 3)

    self.assertEqual(
        packages_by_name["macOS 13.4.1"].version,
        "13.4.1",
    )
    self.assertEqual(
        packages_by_name["macOS 13.4.1"].installed_on / 1_000_000,
        datetime.datetime(
            year=2023, month=7, day=17, hour=8, minute=45, second=50
        ).timestamp(),
    )

    self.assertEqual(
        packages_by_name["grrd"].description,
        "com.google.corp.grrd",
    )
    self.assertEqual(
        packages_by_name["grrd"].installed_on / 1_000_000,
        datetime.datetime(
            year=2023, month=7, day=17, hour=8, minute=56, second=15
        ).timestamp(),
    )

    self.assertEqual(
        packages_by_name["osquery"].description,
        "io.osquery.agent",
    )
    self.assertEqual(
        packages_by_name["osquery"].installed_on / 1_000_000,
        datetime.datetime(
            year=2024, month=5, day=8, hour=13, minute=13, second=12
        ).timestamp(),
    )


if __name__ == "__main__":
  absltest.main()
