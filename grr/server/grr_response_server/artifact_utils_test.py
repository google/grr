#!/usr/bin/env python
"""Tests for the artifact libraries."""

import os

from absl import app
from absl.testing import absltest

from grr_response_core.lib import artifact_utils
from grr_response_core.lib.rdfvalues import artifacts as rdf_artifacts
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import test_base as rdf_test_base
from grr_response_proto import knowledge_base_pb2
from grr_response_server import artifact_registry as ar
from grr.test_lib import artifact_test_lib
from grr.test_lib import test_lib


class ArtifactHandlingTest(test_lib.GRRBaseTest):

  def setUp(self):
    super().setUp()
    self.test_artifacts_dir = os.path.join(self.base_path, "artifacts")
    self.test_artifacts_file = os.path.join(
        self.test_artifacts_dir, "test_artifacts.json"
    )

  @artifact_test_lib.PatchCleanArtifactRegistry
  def testArtifactsValidate(self, registry):
    """Check each artifact we have passes validation."""
    registry.AddFileSource(self.test_artifacts_file)

    for artifact in registry.GetArtifacts():
      ar.Validate(artifact)

  @artifact_test_lib.PatchCleanArtifactRegistry
  def testAddFileSource(self, registry):
    registry.AddFileSource(self.test_artifacts_file)
    registry.GetArtifact("TestCmdArtifact")
    with self.assertRaises(rdf_artifacts.ArtifactNotRegisteredError):
      registry.GetArtifact("NonExistentArtifact")

  @artifact_test_lib.PatchCleanArtifactRegistry
  def testAddDirSource(self, registry):
    registry.AddDirSource(self.test_artifacts_dir)
    registry.GetArtifact("TestCmdArtifact")
    with self.assertRaises(rdf_artifacts.ArtifactNotRegisteredError):
      registry.GetArtifact("NonExistentArtifact")

  @artifact_test_lib.PatchDefaultArtifactRegistry
  def testGetArtifacts(self, registry):
    registry.AddFileSource(self.test_artifacts_file)

    results = registry.GetArtifacts(os_name="Windows")
    for result in results:
      self.assertTrue(
          "Windows" in result.supported_os or not result.supported_os
      )

    results = registry.GetArtifacts(
        os_name="Windows",
        name_list=["TestAggregationArtifact", "TestFileArtifact"],
    )

    # TestFileArtifact doesn't match the OS criteria
    self.assertCountEqual(
        [x.name for x in results], ["TestAggregationArtifact"]
    )
    for result in results:
      self.assertTrue(
          "Windows" in result.supported_os or not result.supported_os
      )

    results = registry.GetArtifacts(
        os_name="Windows",
        source_type=rdf_artifacts.ArtifactSource.SourceType.REGISTRY_VALUE,
        name_list=["DepsProvidesMultiple"],
    )
    self.assertEqual(results.pop().name, "DepsProvidesMultiple")

    # Check supported_os = [] matches any OS
    results = registry.GetArtifacts(
        os_name="Windows", name_list=["TestRegistryKey"]
    )
    self.assertLen(results, 1)
    artifact = results.pop()
    self.assertEqual(artifact.name, "TestRegistryKey")
    self.assertEqual(artifact.supported_os, [])

    results = registry.GetArtifacts(os_name="Windows", exclude_dependents=True)
    for result in results:
      self.assertFalse(ar.GetArtifactPathDependencies(result))

  @artifact_test_lib.PatchDefaultArtifactRegistry
  def testGetArtifactByAlias(self, registry):
    registry.AddFileSource(self.test_artifacts_file)
    self.assertEqual(
        registry.GetArtifact("TestArtifactWithAlias").name,
        "TestArtifactWithAlias",
    )
    self.assertEqual(
        registry.GetArtifact("ArtifactAlias").name, "TestArtifactWithAlias"
    )

  @artifact_test_lib.PatchDefaultArtifactRegistry
  def testGetArtifactNames(self, registry):
    registry.AddFileSource(self.test_artifacts_file)

    result_objs = registry.GetArtifacts(os_name="Windows")

    results_names = registry.GetArtifactNames(os_name="Windows")

    self.assertCountEqual(set([a.name for a in result_objs]), results_names)
    self.assertNotEmpty(results_names)

    results_names = registry.GetArtifactNames(os_name="Darwin")
    self.assertIn("UsersDirectory", results_names)

  @artifact_test_lib.PatchCleanArtifactRegistry
  def testArtifactConversion(self, registry):
    registry.AddFileSource(self.test_artifacts_file)

    for art_obj in registry.GetArtifacts():
      # Exercise conversions to ensure we can move back and forth between the
      # different forms.
      art_json = art_obj.ToJson()
      # TODO: This is a temporary hack. Once Python 3 compatibility
      # wrapper for dealing with JSON is implemented, this should go away.
      if isinstance(art_json, bytes):
        art_json = art_json.decode("utf-8")
      new_art_obj = registry.ArtifactsFromYaml(art_json)[0]
      self.assertEqual(new_art_obj.ToPrimitiveDict(), art_obj.ToPrimitiveDict())

  @artifact_test_lib.PatchCleanArtifactRegistry
  def testArtifactsDependencies(self, registry):
    """Check artifact dependencies work."""
    registry.AddFileSource(self.test_artifacts_file)

    art_obj = registry.GetArtifact("TestAggregationArtifactDeps")
    deps = ar.GetArtifactDependencies(art_obj)
    self.assertCountEqual(list(deps), ["TestAggregationArtifact"])

    deps = ar.GetArtifactDependencies(art_obj, recursive=True)
    self.assertCountEqual(
        list(deps),
        ["TestOSAgnostic", "TestCmdArtifact", "TestAggregationArtifact"],
    )

    # Test recursive loop.
    # Make sure we use the registry registered version of the class.
    source = art_obj.sources[0]
    backup = source.attributes["names"]
    try:
      source.attributes["names"] = ["TestAggregationArtifactDeps"]
      with self.assertRaises(RuntimeError) as e:
        ar.GetArtifactDependencies(art_obj, recursive=True)
      self.assertIn("artifact recursion depth", str(e.exception))
    finally:
      source.attributes["names"] = backup  # Restore old source.


class UserMergeTest(test_lib.GRRBaseTest):

  def testUserMergeWindows(self):
    """Check Windows users are accurately merged."""
    kb = rdf_client.KnowledgeBase()
    self.assertEmpty(kb.users)
    kb.MergeOrAddUser(rdf_client.User(sid="1234"))
    self.assertLen(kb.users, 1)
    kb.MergeOrAddUser(rdf_client.User(sid="5678", username="test1"))
    self.assertLen(kb.users, 2)

    kb.MergeOrAddUser(rdf_client.User(sid="5678", username="test2"))
    self.assertLen(kb.users, 2)
    self.assertEqual(kb.GetUser(sid="5678").username, "test2")

    # This should merge on user name as we have no other data.
    kb.MergeOrAddUser(rdf_client.User(username="test2", homedir="a"))
    self.assertLen(kb.users, 2)

    # This should create a new user since the sid is different.
    kb.MergeOrAddUser(
        rdf_client.User(username="test2", sid="12345", temp="/blah")
    )
    self.assertLen(kb.users, 3)

  def testUserMergeLinux(self):
    """Check Linux users are accurately merged."""
    kb = rdf_client.KnowledgeBase()
    self.assertEmpty(kb.users)
    kb.MergeOrAddUser(rdf_client.User(username="blake", last_logon=1111))
    self.assertLen(kb.users, 1)
    # This should merge since the username is the same.
    kb.MergeOrAddUser(rdf_client.User(uid="12", username="blake"))
    self.assertLen(kb.users, 1)

    # This should create a new record because the uid is different
    kb.MergeOrAddUser(
        rdf_client.User(
            username="blake", uid="13", desktop="/home/blake/Desktop"
        )
    )
    self.assertLen(kb.users, 2)

    kb.MergeOrAddUser(
        rdf_client.User(
            username="newblake", uid="14", desktop="/home/blake/Desktop"
        )
    )

    self.assertLen(kb.users, 3)

    # Check merging where we don't specify uid works
    kb.MergeOrAddUser(
        rdf_client.User(username="newblake", desktop="/home/blakey/Desktop")
    )
    self.assertLen(kb.users, 3)


class ArtifactTests(rdf_test_base.RDFValueTestMixin, test_lib.GRRBaseTest):
  """Test the Artifact implementation."""

  rdfvalue_class = rdf_artifacts.Artifact

  def GenerateSample(self, number=0):
    result = rdf_artifacts.Artifact(
        name="artifact%s" % number,
        doc="Doco",
        supported_os="Windows",
        urls="http://blah",
    )
    return result

  def testGetArtifactPathDependencies(self):
    sources = [
        {
            "type": rdf_artifacts.ArtifactSource.SourceType.REGISTRY_KEY,
            "attributes": {
                "keys": [
                    # pylint: disable=line-too-long
                    # pyformat: disable
                    r"%%current_control_set%%\Control\Session Manager\Environment\Path",
                    # pylint: enable=line-too-long
                    # pyformat: enable
                ],
            },
        },
        {
            "type": rdf_artifacts.ArtifactSource.SourceType.WMI,
            "attributes": {
                "query": """
                    SELECT *
                      FROM Win32_UserProfile
                     WHERE SID='%%users.sid%%'
                """.strip(),
            },
        },
        {
            "type": rdf_artifacts.ArtifactSource.SourceType.PATH,
            "attributes": {
                "paths": ["/home/%%users.username%%"],
            },
        },
    ]

    artifact = rdf_artifacts.Artifact(
        name="artifact",
        doc="Doco",
        supported_os=["Windows"],
        urls=["http://blah"],
        sources=sources,
    )

    self.assertCountEqual(
        [x["type"] for x in artifact.ToPrimitiveDict()["sources"]],
        ["REGISTRY_KEY", "WMI", "PATH"],
    )

    self.assertCountEqual(
        ar.GetArtifactPathDependencies(artifact),
        ["current_control_set", "users.sid", "users.username"],
    )

  def testValidateSyntax(self):
    sources = [
        {
            "type": rdf_artifacts.ArtifactSource.SourceType.REGISTRY_KEY,
            "attributes": {
                "keys": [
                    r"%%current_control_set%%\Control\Session "
                    r"Manager\Environment\Path"
                ]
            },
        },
        {
            "type": rdf_artifacts.ArtifactSource.SourceType.FILE,
            "attributes": {"paths": [r"%%environ_systemdrive%%\Temp"]},
        },
    ]

    artifact = rdf_artifacts.Artifact(
        name="good",
        doc="Doco",
        supported_os=["Windows"],
        urls=["http://blah"],
        sources=sources,
    )
    ar.ValidateSyntax(artifact)

  def testValidateSyntaxBadPathDependency(self):
    sources = [{
        "type": rdf_artifacts.ArtifactSource.SourceType.FILE,
        "attributes": {"paths": [r"%%systemdrive%%\Temp"]},
    }]

    artifact = rdf_artifacts.Artifact(
        name="bad",
        doc="Doco",
        supported_os=["Windows"],
        urls=["http://blah"],
        sources=sources,
    )
    with self.assertRaises(rdf_artifacts.ArtifactDefinitionError):
      ar.ValidateSyntax(artifact)


class ExpandKnowledgebaseWindowsEnvVars(absltest.TestCase):

  def testInvalidSystem(self):
    kb = knowledge_base_pb2.KnowledgeBase()
    kb.os = "Linux"

    with self.assertRaises(ValueError) as context:
      artifact_utils.ExpandKnowledgebaseWindowsEnvVars(kb)

    self.assertEqual(str(context.exception), "Invalid system: 'Linux'")

  def testCircularDependency(self):
    kb = knowledge_base_pb2.KnowledgeBase()
    kb.os = "Windows"
    kb.environ_systemdrive = "%SystemRoot%\\.."
    kb.environ_systemroot = "%SystemDrive%\\Windows"

    with self.assertRaises(ValueError) as context:
      artifact_utils.ExpandKnowledgebaseWindowsEnvVars(kb)

    self.assertStartsWith(str(context.exception), "Circular dependency")

  def testDefaults(self):
    kb = knowledge_base_pb2.KnowledgeBase()
    kb.os = "Windows"

    kb = artifact_utils.ExpandKnowledgebaseWindowsEnvVars(kb)

    self.assertEqual(kb.environ_systemdrive, "C:")
    self.assertEqual(kb.environ_systemroot, "C:\\Windows")
    self.assertEqual(kb.environ_temp, "C:\\Windows\\TEMP")
    self.assertEqual(kb.environ_programfiles, "C:\\Program Files")
    self.assertEqual(kb.environ_programfilesx86, "C:\\Program Files (x86)")

  def testSimpleExpansion(self):
    kb = knowledge_base_pb2.KnowledgeBase()
    kb.os = "Windows"
    kb.environ_systemdrive = "X:"
    kb.environ_temp = "%SystemDrive%\\Temporary"

    kb = artifact_utils.ExpandKnowledgebaseWindowsEnvVars(kb)

    self.assertEqual(kb.environ_systemdrive, "X:")
    self.assertEqual(kb.environ_temp, "X:\\Temporary")

  def testRecursiveExpansion(self):
    kb = knowledge_base_pb2.KnowledgeBase()
    kb.os = "Windows"
    kb.environ_systemdrive = "X:"
    kb.environ_systemroot = "%SystemDrive%\\W1nd0w5"
    kb.environ_temp = "%SystemRoot%\\T3mp"
    kb.environ_allusersappdata = "%TEMP%\\U53r5"

    kb = artifact_utils.ExpandKnowledgebaseWindowsEnvVars(kb)

    self.assertEqual(kb.environ_systemdrive, "X:")
    self.assertEqual(kb.environ_systemroot, "X:\\W1nd0w5")
    self.assertEqual(kb.environ_temp, "X:\\W1nd0w5\\T3mp")
    self.assertEqual(kb.environ_allusersappdata, "X:\\W1nd0w5\\T3mp\\U53r5")

  def testMultiExpansion(self):
    kb = knowledge_base_pb2.KnowledgeBase()
    kb.os = "Windows"
    kb.environ_systemdrive = "X:"
    kb.environ_comspec = "%SystemDrive%\\.."
    kb.environ_temp = "%ComSpec%\\%SystemDrive%"

    kb = artifact_utils.ExpandKnowledgebaseWindowsEnvVars(kb)

    self.assertEqual(kb.environ_systemdrive, "X:")
    self.assertEqual(kb.environ_comspec, "X:\\..")
    self.assertEqual(kb.environ_temp, "X:\\..\\X:")

  def testUnknownEnvVarRefs(self):
    kb = knowledge_base_pb2.KnowledgeBase()
    kb.os = "Windows"
    kb.environ_systemdrive = "X:"
    kb.environ_systemroot = "%SystemDrive%\\%SystemName%"

    kb = artifact_utils.ExpandKnowledgebaseWindowsEnvVars(kb)

    self.assertEqual(kb.environ_systemroot, "X:\\%SystemName%")


class KnowledgeBaseInterpolationTest(absltest.TestCase):

  def testSinglePattern(self):
    kb = knowledge_base_pb2.KnowledgeBase()
    kb.fqdn = "foo.example.com"

    interpolation = artifact_utils.KnowledgeBaseInterpolation(
        pattern="ping %%fqdn%%",
        kb=kb,
    )

    self.assertLen(interpolation.results, 1)
    self.assertEqual(interpolation.results[0], "ping foo.example.com")

  def testMultiplePatterns(self):
    kb = knowledge_base_pb2.KnowledgeBase()
    kb.os = "Linux"
    kb.fqdn = "foo.example.com"

    interpolation = artifact_utils.KnowledgeBaseInterpolation(
        pattern="%%fqdn%% (%%os%%)",
        kb=kb,
    )

    self.assertLen(interpolation.results, 1)
    self.assertEqual(interpolation.results[0], "foo.example.com (Linux)")

  def testSingleUserSinglePattern(self):
    kb = knowledge_base_pb2.KnowledgeBase()
    kb.users.add(username="user0")

    interpolation = artifact_utils.KnowledgeBaseInterpolation(
        pattern="X:\\Users\\%%users.username%%",
        kb=kb,
    )

    self.assertLen(interpolation.results, 1)
    self.assertEqual(interpolation.results[0], "X:\\Users\\user0")

  def testSingleUserMultiplePatterns(self):
    kb = knowledge_base_pb2.KnowledgeBase()
    kb.environ_systemdrive = "X:"
    kb.users.add(username="user0")

    interpolation = artifact_utils.KnowledgeBaseInterpolation(
        pattern="%%environ_systemdrive%%\\Users\\%%users.username%%",
        kb=kb,
    )

    self.assertLen(interpolation.results, 1)
    self.assertEqual(interpolation.results[0], "X:\\Users\\user0")

  def testMultipleUsers(self):
    kb = knowledge_base_pb2.KnowledgeBase()
    kb.environ_systemdrive = "X:"
    kb.users.add(username="user0", sid="S-0-X-X-770")
    kb.users.add(username="user1", sid="S-1-X-X-771")
    kb.users.add(username="user2", sid="S-2-X-X-772")

    interpolation = artifact_utils.KnowledgeBaseInterpolation(
        pattern="%%environ_systemdrive%%\\%%users.sid%%\\%%users.username%%",
        kb=kb,
    )

    self.assertLen(interpolation.results, 3)
    self.assertEqual(interpolation.results[0], "X:\\S-0-X-X-770\\user0")
    self.assertEqual(interpolation.results[1], "X:\\S-1-X-X-771\\user1")
    self.assertEqual(interpolation.results[2], "X:\\S-2-X-X-772\\user2")

  def testMultipleUsersNoPatterns(self):
    kb = knowledge_base_pb2.KnowledgeBase()
    kb.users.add(username="foo")
    kb.users.add(username="bar")

    interpolation = artifact_utils.KnowledgeBaseInterpolation(
        pattern="X:\\Users\\foo",
        kb=kb,
    )

    self.assertLen(interpolation.results, 1)
    self.assertEqual(interpolation.results[0], "X:\\Users\\foo")

  def testNoUsers(self):
    kb = knowledge_base_pb2.KnowledgeBase()

    interpolation = artifact_utils.KnowledgeBaseInterpolation(
        pattern="X:\\Users\\%%users.username%%",
        kb=kb,
    )
    self.assertEmpty(interpolation.results)
    self.assertEmpty(interpolation.logs)

  def testNoUsersNoPatterns(self):
    kb = knowledge_base_pb2.KnowledgeBase()

    interpolation = artifact_utils.KnowledgeBaseInterpolation(
        pattern="X:\\Users\\foo",
        kb=kb,
    )
    self.assertLen(interpolation.results, 1)
    self.assertEqual(interpolation.results[0], "X:\\Users\\foo")

  def testUserWithoutUsername(self):
    kb = knowledge_base_pb2.KnowledgeBase()
    kb.users.add(sid="S-0-X-X-770")

    interpolation = artifact_utils.KnowledgeBaseInterpolation(
        pattern="X:\\Users\\%%users.username%%",
        kb=kb,
    )
    self.assertEmpty(interpolation.results)
    self.assertIn("without username", interpolation.logs[0])

  def testWindowsSingleUserMissingAttribute(self):
    kb = knowledge_base_pb2.KnowledgeBase()
    kb.os = "Windows"
    kb.users.add(username="foo")

    interpolation = artifact_utils.KnowledgeBaseInterpolation(
        pattern="X:\\SID\\%%users.sid%%",
        kb=kb,
    )
    self.assertEmpty(interpolation.results)
    self.assertIn(
        "user 'foo' is missing 'sid' (no Windows default available)",
        interpolation.logs,
    )

  def testWindowsMultipleUsersMissingAttribute(self):
    kb = knowledge_base_pb2.KnowledgeBase()
    kb.os = "Windows"
    kb.users.add(username="foo", sid="S-0-X-X-770")
    kb.users.add(username="bar")

    interpolation = artifact_utils.KnowledgeBaseInterpolation(
        pattern="X:\\SID\\%%users.sid%%",
        kb=kb,
    )
    self.assertLen(interpolation.results, 1)
    self.assertEqual(interpolation.results[0], "X:\\SID\\S-0-X-X-770")
    self.assertIn(
        "user 'bar' is missing 'sid' (no Windows default available)",
        interpolation.logs,
    )

  def testMissingAttribute(self):
    kb = knowledge_base_pb2.KnowledgeBase()
    kb.fqdn = "foo.example.com"

    interpolation = artifact_utils.KnowledgeBaseInterpolation(
        pattern="%%fqdn%% (%%os%%)",
        kb=kb,
    )
    self.assertEmpty(interpolation.results)
    self.assertIn("'os' is missing", interpolation.logs)

  def testUserNonExistingAttribute(self):
    kb = knowledge_base_pb2.KnowledgeBase()
    kb.os = "Windows"
    kb.users.add(username="foo")

    with self.assertRaises(ValueError) as context:
      artifact_utils.KnowledgeBaseInterpolation(
          pattern="X:\\Users\\%%users.foobar%%",
          kb=kb,
      )

    error = context.exception
    self.assertEqual(str(error), "`%%users.foobar%%` does not exist")

  def testNonExistingAttribute(self):
    with self.assertRaises(ValueError) as context:
      artifact_utils.KnowledgeBaseInterpolation(
          pattern="X:\\%%foobar%%",
          kb=knowledge_base_pb2.KnowledgeBase(),
      )

    error = context.exception
    self.assertEqual(str(error), "`%%foobar%%` does not exist")

  def testUserprofileFromUserprofile(self):
    kb = knowledge_base_pb2.KnowledgeBase()
    kb.os = "Windows"
    kb.users.add(username="foo", userprofile="X:\\Users\\foo")

    interpolation = artifact_utils.KnowledgeBaseInterpolation(
        pattern="%%users.userprofile%%\\file.txt",
        kb=kb,
    )
    self.assertLen(interpolation.results, 1)
    self.assertEqual(interpolation.results[0], "X:\\Users\\foo\\file.txt")

  def testDefaultUserprofileFromHomedir(self):
    kb = knowledge_base_pb2.KnowledgeBase()
    kb.os = "Windows"
    kb.users.add(username="foo", homedir="X:\\Users\\foo")

    interpolation = artifact_utils.KnowledgeBaseInterpolation(
        pattern="%%users.userprofile%%\\file.txt",
        kb=kb,
    )
    self.assertLen(interpolation.results, 1)
    self.assertEqual(interpolation.results[0], "X:\\Users\\foo\\file.txt")
    self.assertIn(
        "using default 'X:\\\\Users\\\\foo' for 'userprofile' for user 'foo'",
        interpolation.logs,
    )

  def testDefaultUserprofileFromUsernameSystemDrive(self):
    kb = knowledge_base_pb2.KnowledgeBase()
    kb.os = "Windows"
    kb.environ_systemdrive = "X:"
    kb.users.add(username="foo")

    interpolation = artifact_utils.KnowledgeBaseInterpolation(
        pattern="%%users.userprofile%%\\file.txt",
        kb=kb,
    )
    self.assertLen(interpolation.results, 1)
    self.assertEqual(interpolation.results[0], "X:\\Users\\foo\\file.txt")
    self.assertIn(
        "using default 'X:\\\\Users\\\\foo' for 'userprofile' for user 'foo'",
        interpolation.logs,
    )

  def testDefaultUserprofileFromUsername(self):
    kb = knowledge_base_pb2.KnowledgeBase()
    kb.os = "Windows"
    kb.environ_systemdrive = "C:"
    kb.users.add(username="foo")

    interpolation = artifact_utils.KnowledgeBaseInterpolation(
        pattern="%%users.userprofile%%\\file.txt",
        kb=kb,
    )
    self.assertLen(interpolation.results, 1)
    self.assertEqual(interpolation.results[0], "C:\\Users\\foo\\file.txt")
    self.assertIn(
        "using default 'C:\\\\Users\\\\foo' for 'userprofile' for user 'foo'",
        interpolation.logs,
    )

  def testLinuxDefaultUserprofile(self):
    kb = knowledge_base_pb2.KnowledgeBase()
    kb.os = "Linux"
    kb.users.add(username="foo")

    interpolation = artifact_utils.KnowledgeBaseInterpolation(
        pattern="%%users.homedir%%\\file.log",
        kb=kb,
    )
    self.assertEmpty(interpolation.results)
    self.assertIn(
        "user 'foo' is missing 'homedir' (no fallback available)",
        interpolation.logs,
    )


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
