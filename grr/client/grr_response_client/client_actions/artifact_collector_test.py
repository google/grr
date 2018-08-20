#!/usr/bin/env python
"""Tests the client artifactor collection."""
import os

from builtins import filter  # pylint: disable=redefined-builtin
import mock

from grr_response_client import client_utils
from grr_response_client import client_utils_common
from grr_response_client.client_actions import artifact_collector
from grr_response_client.client_actions.file_finder_utils import globbing
from grr_response_core import config
from grr_response_core.lib import flags
from grr_response_core.lib import parser
from grr_response_core.lib import utils
from grr_response_core.lib.parsers import config_file
from grr_response_core.lib.rdfvalues import anomaly as rdf_anomaly
from grr_response_core.lib.rdfvalues import artifacts as rdf_artifact
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr.test_lib import artifact_test_lib
from grr.test_lib import client_test_lib
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib


class ArtifactCollectorTest(client_test_lib.EmptyActionTest):

  def setUp(self):
    super(ArtifactCollectorTest, self).setUp()
    self.test_artifacts_file = os.path.join(config.CONFIG["Test.data_dir"],
                                            "artifacts", "test_artifacts.json")

  @artifact_test_lib.PatchCleanArtifactRegistry
  def testCommandArtifact(self, registry):
    """Test the basic ExecuteCommand action."""

    client_test_lib.Command("/usr/bin/dpkg", args=["--list"], system="Linux")

    registry.AddFileSource(self.test_artifacts_file)
    artifact = registry.GetArtifact("TestCmdArtifact")
    ext_src = rdf_artifact.ExtendedSource(base_source=list(artifact.sources)[0])
    ext_art = rdf_artifact.ExtendedArtifact(
        name=artifact.name, sources=[ext_src])
    request = rdf_artifact.ClientArtifactCollectorArgs(
        artifacts=[ext_art], apply_parsers=False)
    result = self.RunAction(artifact_collector.ArtifactCollector, request)[0]
    collected_artifact = list(result.collected_artifacts)[0]
    execute_response = list(collected_artifact.action_results)[0].value

    self.assertEqual(collected_artifact.name, "TestCmdArtifact")
    self.assertTrue(execute_response.time_used > 0)

  @artifact_test_lib.PatchCleanArtifactRegistry
  def testGRRClientActionArtifact(self, registry):
    """Test the GetHostname action."""
    registry.AddFileSource(self.test_artifacts_file)
    artifact = registry.GetArtifact("TestOSAgnostic")
    ext_src = rdf_artifact.ExtendedSource(base_source=list(artifact.sources)[0])
    ext_art = rdf_artifact.ExtendedArtifact(
        name=artifact.name, sources=[ext_src])
    request = rdf_artifact.ClientArtifactCollectorArgs(
        artifacts=[ext_art], apply_parsers=False)
    result = self.RunAction(artifact_collector.ArtifactCollector, request)[0]
    collected_artifact = list(result.collected_artifacts)[0]
    hostname = list(collected_artifact.action_results)[0].value

    self.assertEqual(collected_artifact.name, "TestOSAgnostic")
    self.assertTrue(hostname.string)

  def testRegistryValueArtifact(self):
    """Test the basic Registry Value collection."""
    with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.REGISTRY,
                                   vfs_test_lib.FakeRegistryVFSHandler):
      with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                                     vfs_test_lib.FakeFullVFSHandler):
        source = rdf_artifact.ArtifactSource(
            type=rdf_artifact.ArtifactSource.SourceType.REGISTRY_VALUE,
            attributes={
                "key_value_pairs": [{
                    "key": (r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet"
                            r"\Control\Session Manager"),
                    "value":
                        "BootExecute"
                }]
            })
        ext_src = rdf_artifact.ExtendedSource(base_source=source)
        ext_art = rdf_artifact.ExtendedArtifact(
            name="FakeRegistryValue", sources=[ext_src])
        request = rdf_artifact.ClientArtifactCollectorArgs(
            artifacts=[ext_art], apply_parsers=False)
        result = self.RunAction(artifact_collector.ArtifactCollector,
                                request)[0]
        collected_artifact = list(result.collected_artifacts)[0]
        file_stat = list(collected_artifact.action_results)[0].value
        self.assertTrue(isinstance(file_stat, rdf_client_fs.StatEntry))
        urn = file_stat.pathspec.AFF4Path(self.SetupClient(0))
        self.assertTrue(str(urn).endswith("BootExecute"))

  @artifact_test_lib.PatchCleanArtifactRegistry
  def testMultipleArtifacts(self, registry):
    """Test collecting multiple artifacts."""

    client_test_lib.Command("/usr/bin/dpkg", args=["--list"], system="Linux")

    registry.AddFileSource(self.test_artifacts_file)
    artifact = registry.GetArtifact("TestCmdArtifact")
    ext_src = rdf_artifact.ExtendedSource(base_source=list(artifact.sources)[0])
    ext_art = rdf_artifact.ExtendedArtifact(
        name=artifact.name, sources=[ext_src])
    request = rdf_artifact.ClientArtifactCollectorArgs(
        artifacts=[ext_art], apply_parsers=False)
    request.artifacts.append(ext_art)
    result = self.RunAction(artifact_collector.ArtifactCollector, request)[0]
    collected_artifacts = list(result.collected_artifacts)
    self.assertEqual(len(collected_artifacts), 2)
    self.assertEqual(collected_artifacts[0].name, "TestCmdArtifact")
    self.assertEqual(collected_artifacts[1].name, "TestCmdArtifact")
    execute_response_1 = list(collected_artifacts[0].action_results)[0].value
    execute_response_2 = list(collected_artifacts[1].action_results)[0].value
    self.assertGreater(execute_response_1.time_used, 0)
    self.assertGreater(execute_response_2.time_used, 0)


class WindowsArtifactCollectorTests(client_test_lib.OSSpecificClientTests):

  def setUp(self):
    super(WindowsArtifactCollectorTests, self).setUp()
    self.test_artifacts_file = os.path.join(config.CONFIG["Test.data_dir"],
                                            "artifacts", "test_artifacts.json")

    windows_mock = mock.MagicMock()
    modules = {
        ("grr_response_client.client_actions"
         ".windows"):
            windows_mock
    }

    self.module_patcher = mock.patch.dict("sys.modules", modules)
    self.module_patcher.start()

    self.windows = windows_mock.windows

  def tearDown(self):
    super(WindowsArtifactCollectorTests, self).tearDown()
    self.module_patcher.stop()

  @artifact_test_lib.PatchCleanArtifactRegistry
  def testWMIArtifact(self, registry):
    registry.AddFileSource(self.test_artifacts_file)
    artifact = registry.GetArtifact("WMIActiveScriptEventConsumer")

    ext_src = rdf_artifact.ExtendedSource(base_source=artifact.sources[0])
    ext_art = rdf_artifact.ExtendedArtifact(
        name=artifact.name, sources=[ext_src])
    request = rdf_artifact.ClientArtifactCollectorArgs(
        artifacts=[ext_art],
        knowledge_base=None,
        ignore_interpolation_errors=True,
        apply_parsers=False)
    result = self.RunAction(artifact_collector.ArtifactCollector, request)[0]
    self.assertIsInstance(result, rdf_artifact.ClientArtifactCollectorResult)

    coll = artifact_collector.ArtifactCollector()
    coll.knowledge_base = None
    coll.ignore_interpolation_errors = True

    expected = rdf_client_action.WMIRequest(
        query="SELECT * FROM ActiveScriptEventConsumer",
        base_object="winmgmts:\\root\\subscription")

    for action, request in coll._ProcessWmiSource(ext_src):
      self.assertEqual(request, expected)
      self.assertEqual(action, self.windows.WmiQuery)
      self.windows.WmiQuery.Start.assert_called_with(request)


class TestEchoCmdParser(parser.CommandParser):

  output_types = ["SoftwarePackage"]
  supported_artifacts = ["TestEchoCmdArtifact"]

  def Parse(self, cmd, args, stdout, stderr, return_val, time_taken,
            knowledge_base):
    del cmd, args, stderr, return_val, time_taken, knowledge_base  # Unused
    installed = rdf_client.SoftwarePackage.InstallState.INSTALLED
    soft = rdf_client.SoftwarePackage(
        name="Package",
        description=stdout,
        version="1",
        architecture="amd64",
        install_state=installed)
    yield soft


class FakeFileParser(parser.FileParser):

  output_types = ["AttributedDict"]
  supported_artifacts = ["FakeFileArtifact"]

  def Parse(self, stat, file_obj, knowledge_base):

    del knowledge_base  # Unused.

    lines = set([l.strip() for l in file_obj.read().splitlines()])

    users = list(filter(None, lines))

    filename = stat.pathspec.path
    cfg = {"filename": filename, "users": users}

    yield rdf_protodict.AttributedDict(**cfg)


class ParseResponsesTest(client_test_lib.EmptyActionTest):

  def testCmdArtifact(self):
    """Test the parsing of an Echo Command with a TestParser."""
    client_test_lib.Command("/bin/echo", args=["1"])

    processor = parser.Parser.GetClassesByArtifact("TestEchoCmdArtifact")[0]()

    self.assertIsInstance(processor, TestEchoCmdParser)

    request = rdf_client_action.ExecuteRequest(cmd="/bin/echo", args=["1"])
    res = client_utils_common.Execute(request.cmd, request.args)
    (stdout, stderr, status, time_used) = res

    response = rdf_client_action.ExecuteResponse(
        request=request,
        stdout=stdout,
        stderr=stderr,
        exit_status=status,
        time_used=int(1e6 * time_used))

    results = []
    for res in artifact_collector.ParseResponse(processor, response, {}):
      results.append(res)

    self.assertEqual(len(results), 1)
    self.assertIsInstance(results[0], rdf_client.SoftwarePackage)
    self.assertEqual(results[0].description, "1\n")

  def testCmdArtifactAction(self):
    """Test the actual client action with parsers."""
    client_test_lib.Command("/bin/echo", args=["1"])

    source = rdf_artifact.ArtifactSource(
        type=rdf_artifact.ArtifactSource.SourceType.COMMAND,
        attributes={
            "cmd": "/bin/echo",
            "args": ["1"]
        })
    ext_src = rdf_artifact.ExtendedSource(base_source=source)
    ext_art = rdf_artifact.ExtendedArtifact(
        name="TestEchoCmdArtifact", sources=[ext_src])
    request = rdf_artifact.ClientArtifactCollectorArgs(
        artifacts=[ext_art],
        knowledge_base=None,
        ignore_interpolation_errors=True,
        apply_parsers=True)
    result = self.RunAction(artifact_collector.ArtifactCollector, request)[0]
    self.assertIsInstance(result, rdf_artifact.ClientArtifactCollectorResult)
    self.assertTrue(len(result.collected_artifacts), 1)
    res = result.collected_artifacts[0].action_results[0].value
    self.assertIsInstance(res, rdf_client.SoftwarePackage)
    self.assertEqual(res.description, "1\n")

  def testFileArtifactParser(self):
    """Test parsing a fake file artifact with a file parser."""

    processor = config_file.CronAtAllowDenyParser()

    source = rdf_artifact.ArtifactSource(
        type=rdf_artifact.ArtifactSource.SourceType.FILE,
        attributes={
            "paths": ["VFSFixture/etc/passwd", "numbers.txt"],
        })

    paths = []
    for path in source.attributes["paths"]:
      paths.append(os.path.join(self.base_path, path))

    stat_cache = utils.StatCache()

    expanded_paths = []
    opts = globbing.PathOpts(follow_links=True)
    for path in paths:
      for expanded_path in globbing.ExpandPath(path, opts):
        expanded_paths.append(expanded_path)

    results = []
    for path in expanded_paths:
      stat = stat_cache.Get(path, follow_symlink=True)
      pathspec = rdf_paths.PathSpec(
          pathtype=rdf_paths.PathSpec.PathType.OS,
          path=client_utils.LocalPathToCanonicalPath(stat.GetPath()),
          path_options=rdf_paths.PathSpec.Options.CASE_LITERAL)
      response = rdf_client_fs.FindSpec(pathspec=pathspec)

      for res in artifact_collector.ParseResponse(processor, response, {}):
        results.append(res)

    self.assertEqual(len(results), 3)
    self.assertTrue(
        results[0]["filename"].endswith("test_data/VFSFixture/etc/passwd"))
    self.assertIsInstance(results[0], rdf_protodict.AttributedDict)
    self.assertEqual(len(results[0]["users"]), 3)
    self.assertIsInstance(results[1], rdf_anomaly.Anomaly)
    self.assertEqual(len(results[2]["users"]), 1000)

  def testFakeFileArtifactAction(self):
    file_path = os.path.join(self.base_path, "numbers.txt")
    source = rdf_artifact.ArtifactSource(
        type=rdf_artifact.ArtifactSource.SourceType.FILE,
        attributes={"paths": [file_path]})

    ext_src = rdf_artifact.ExtendedSource(base_source=source)
    ext_art = rdf_artifact.ExtendedArtifact(
        name="FakeFileArtifact", sources=[ext_src])
    request = rdf_artifact.ClientArtifactCollectorArgs(
        artifacts=[ext_art],
        knowledge_base=None,
        ignore_interpolation_errors=True,
        apply_parsers=True)
    result = self.RunAction(artifact_collector.ArtifactCollector, request)[0]
    self.assertEqual(len(result.collected_artifacts[0].action_results), 1)
    res = result.collected_artifacts[0].action_results[0].value
    self.assertIsInstance(res, rdf_protodict.AttributedDict)
    self.assertEqual(len(res.users), 1000)
    self.assertEqual(res.filename, file_path)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
