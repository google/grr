#!/usr/bin/env python
import textwrap
from unittest import mock

from absl import app
from absl.testing import absltest

from grr_response_core.lib.rdfvalues import artifacts as rdf_artifacts
from grr_response_core.lib.util import temp
from grr_response_server import artifact_registry as ar
from grr_response_server import data_store
from grr.test_lib import test_lib


class ArtifactRegistrySourcesTest(absltest.TestCase):

  def setUp(self):
    super().setUp()
    self.sources = ar.ArtifactRegistrySources()

  def testDuplicatedAddFile(self):
    self.assertTrue(self.sources.AddFile("foo/bar.yaml"))
    self.assertFalse(self.sources.AddFile("foo/bar.yaml"))

  def testDuplicatedAddDir(self):
    self.assertTrue(self.sources.AddDir("foo/"))
    self.assertFalse(self.sources.AddDir("foo/"))

  def testGetFiles(self):
    self.assertTrue(self.sources.AddFile("foo/bar.json"))
    self.assertTrue(self.sources.AddFile("foo/baz.yaml"))

    files = list(self.sources.GetFiles())
    self.assertIn("foo/bar.json", files)
    self.assertIn("foo/baz.yaml", files)

  def testGetDirs(self):
    self.assertTrue(self.sources.AddDir("foo/"))
    self.assertTrue(self.sources.AddDir("bar/"))

    dirs = list(self.sources.GetDirs())
    self.assertIn("foo/", dirs)
    self.assertIn("bar/", dirs)

  def testGetAllFiles(self):
    with temp.AutoTempDirPath(remove_non_empty=True) as tmpdir_path:
      foo_path = temp.TempFilePath(suffix="foo.yaml")
      bar_path = temp.TempFilePath(suffix="bar.json")
      baz_path = temp.TempFilePath(suffix="baz.yaml")
      quux_path = temp.TempFilePath(dir=tmpdir_path, suffix="quux.yaml")
      norf_path = temp.TempFilePath(dir=tmpdir_path, suffix="norf.json")
      thud_path = temp.TempFilePath(dir=tmpdir_path, suffix="thud.xml")

      self.sources.AddFile(foo_path)
      self.sources.AddFile(bar_path)
      self.sources.AddDir(tmpdir_path)

      files = list(self.sources.GetAllFiles())
      self.assertIn(foo_path, files)
      self.assertIn(bar_path, files)
      self.assertIn(quux_path, files)
      self.assertIn(norf_path, files)
      self.assertNotIn(baz_path, files)
      self.assertNotIn(thud_path, files)

  @mock.patch("logging.warning")
  def testGetAllFilesErrors(self, warning):
    with temp.AutoTempDirPath() as foo_dirpath,\
         temp.AutoTempDirPath() as bar_dirpath:
      self.assertTrue(self.sources.AddDir(foo_dirpath))
      self.assertTrue(self.sources.AddDir("/baz/quux/norf"))
      self.assertTrue(self.sources.AddDir(bar_dirpath))
      self.assertTrue(self.sources.AddDir("/thud"))
      self.assertTrue(self.sources.AddDir("/foo/bar"))

      files = list(self.sources.GetAllFiles())
      self.assertFalse(files)

      self.assertTrue(warning.called)
      self.assertEqual(warning.call_count, 3)


class ArtifactTest(absltest.TestCase):

  def testValidateSyntaxSimple(self):
    artifact = rdf_artifacts.Artifact(
        name="Foo",
        doc="This is Foo.",
        provides=["fqdn", "domain"],
        supported_os=["Windows"],
        urls=["https://example.com"])
    ar.ValidateSyntax(artifact)

  def testValidateSyntaxWithSources(self):
    registry_key_source = {
        "type": rdf_artifacts.ArtifactSource.SourceType.REGISTRY_KEY,
        "attributes": {
            "keys": [
                r"%%current_control_set%%\Control\Session "
                r"Manager\Environment\Path"
            ],
        }
    }

    file_source = {
        "type": rdf_artifacts.ArtifactSource.SourceType.FILE,
        "attributes": {
            "paths": [r"%%environ_systemdrive%%\Temp"]
        }
    }

    artifact = rdf_artifacts.Artifact(
        name="Bar",
        doc="This is Bar.",
        provides=["environ_windir"],
        supported_os=["Windows"],
        urls=["https://example.com"],
        sources=[registry_key_source, file_source])
    ar.ValidateSyntax(artifact)

  def testValidateSyntaxMissingDoc(self):
    artifact = rdf_artifacts.Artifact(
        name="Baz", provides=["os"], supported_os=["Linux"])

    with self.assertRaisesRegex(rdf_artifacts.ArtifactSyntaxError,
                                "missing doc"):
      ar.ValidateSyntax(artifact)

  def testValidateSyntaxInvalidSupportedOs(self):
    artifact = rdf_artifacts.Artifact(
        name="Quux",
        doc="This is Quux.",
        provides=["os"],
        supported_os=["Solaris"])

    with self.assertRaisesRegex(rdf_artifacts.ArtifactSyntaxError, "'Solaris'"):
      ar.ValidateSyntax(artifact)

  def testValidateSyntaxBrokenProvides(self):
    artifact = rdf_artifacts.Artifact(
        name="Thud", doc="This is Thud.", provides=["fqdn", "garbage"])

    with self.assertRaisesRegex(rdf_artifacts.ArtifactSyntaxError, "'garbage'"):
      ar.ValidateSyntax(artifact)

  def testValidateSyntaxBadSource(self):
    source = {
        "type": rdf_artifacts.ArtifactSource.SourceType.ARTIFACT_GROUP,
        "attributes": {}
    }

    artifact = rdf_artifacts.Artifact(
        name="Barf",
        doc="This is Barf.",
        provides=["os"],
        sources=[source])

    with self.assertRaisesRegex(rdf_artifacts.ArtifactSyntaxError,
                                "required attributes"):
      ar.ValidateSyntax(artifact)


class ArtifactSourceTest(absltest.TestCase):

  def testValidateDirectory(self):
    source = rdf_artifacts.ArtifactSource(
        type=rdf_artifacts.ArtifactSource.SourceType.PATH,
        attributes={
            "paths": ["/home", "/usr"],
        })

    source.Validate()

  def testValidateRegistrykey(self):
    source = rdf_artifacts.ArtifactSource(
        type=rdf_artifacts.ArtifactSource.SourceType.REGISTRY_KEY,
        attributes={
            "keys": [r"Foo\Bar\Baz"],
        })

    source.Validate()

  def testValidateCommand(self):
    source = rdf_artifacts.ArtifactSource(
        type=rdf_artifacts.ArtifactSource.SourceType.COMMAND,
        attributes={
            "cmd": "quux",
            "args": ["-foo", "-bar"],
        })

    source.Validate()

  def testValidateCommandWithSingleArgumentContainingSpace(self):
    source = rdf_artifacts.ArtifactSource(
        type=rdf_artifacts.ArtifactSource.SourceType.COMMAND,
        attributes={
            "cmd": "quux",
            "args": ["-foo -bar"],
        })

    with self.assertRaisesRegex(rdf_artifacts.ArtifactSourceSyntaxError,
                                "'-foo -bar'"):
      source.Validate()

  def testValidatePathsIsAList(self):
    source = rdf_artifacts.ArtifactSource(
        type=rdf_artifacts.ArtifactSource.SourceType.FILE,
        attributes={
            "paths": "/bin",
        })

    with self.assertRaisesRegex(rdf_artifacts.ArtifactSourceSyntaxError,
                                "not a list"):
      source.Validate()

  def testValidatePathIsAString(self):
    source = rdf_artifacts.ArtifactSource(
        type=rdf_artifacts.ArtifactSource.SourceType.ARTIFACT_GROUP,
        attributes={
            "names": ["Foo", "Bar"],
            "path": ["/tmp", "/var"],
        })

    with self.assertRaisesRegex(rdf_artifacts.ArtifactSourceSyntaxError,
                                "not a string"):
      source.Validate()

  def testValidateMissingRequiredAttributes(self):
    source = rdf_artifacts.ArtifactSource(
        type=rdf_artifacts.ArtifactSource.SourceType.GREP,
        attributes={
            "paths": ["/etc", "/dev", "/opt"],
        })

    expected = "missing required attributes: 'content_regex_list'"
    with self.assertRaisesRegex(rdf_artifacts.ArtifactSourceSyntaxError,
                                expected):
      source.Validate()


class ArtifactRegistryTest(absltest.TestCase):

  def testArtifactsFromYamlIgnoresDeprecatedFields(self):
    registry = ar.ArtifactRegistry()

    yaml = textwrap.dedent("""\
    name: Foo
    doc: Lorem ipsum.
    labels: ['bar', 'baz']
    sources:
      - type: PATH
        attributes:
          paths: ['/bar', '/baz']
    ---
    name: Quux
    doc: Lorem ipsum.
    labels: ['norf', 'thud']
    sources:
      - type: PATH
        attributes:
          paths: ['/norf', '/thud']
    """)
    artifacts = registry.ArtifactsFromYaml(yaml)
    artifacts.sort(key=lambda artifact: artifact.name)

    self.assertLen(artifacts, 2)
    self.assertEqual(artifacts[0].name, "Foo")
    self.assertFalse(artifacts[0].HasField("labels"))
    self.assertEqual(artifacts[1].name, "Quux")
    self.assertFalse(artifacts[1].HasField("labels"))

  def testDatabaseArtifactsAreLoadedEvenIfNoDatastoreIsRegistered(self):
    rel_db = data_store.REL_DB

    artifact = rdf_artifacts.Artifact(name="Foo")
    rel_db.WriteArtifact(artifact)

    registry = ar.ArtifactRegistry()
    registry.ReloadDatastoreArtifacts()

    self.assertIsNotNone(registry.GetArtifact("Foo"))


if __name__ == "__main__":
  app.run(test_lib.main)
