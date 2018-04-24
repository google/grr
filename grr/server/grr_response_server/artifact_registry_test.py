#!/usr/bin/env python
import mock

import unittest
from grr.lib import rdfvalue
from grr.server.grr_response_server import artifact_registry as ar
from grr.test_lib import test_lib


class ArtifactRegistrySourcesTest(unittest.TestCase):

  def setUp(self):
    super(ArtifactRegistrySourcesTest, self).setUp()
    self.sources = ar.ArtifactRegistrySources()

  def testDuplicatedAddFile(self):
    self.assertTrue(self.sources.AddFile("foo/bar.yaml"))
    self.assertFalse(self.sources.AddFile("foo/bar.yaml"))

  def testDuplicatedAddDir(self):
    self.assertTrue(self.sources.AddDir("foo/"))
    self.assertFalse(self.sources.AddDir("foo/"))

  def testDuplicatedAddDatastore(self):
    sources = self.sources

    self.assertTrue(sources.AddDatastore(rdfvalue.RDFURN("aff4:/artifacts")))
    self.assertFalse(sources.AddDatastore(rdfvalue.RDFURN("aff4:/artifacts")))

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

  def testGetDatastores(self):
    sources = self.sources

    self.assertTrue(sources.AddDatastore(rdfvalue.RDFURN("aff4:/foos")))
    self.assertTrue(sources.AddDatastore(rdfvalue.RDFURN("aff4:/bars")))

    datastores = list(sources.GetDatastores())
    self.assertIn(rdfvalue.RDFURN("aff4:/foos"), datastores)
    self.assertIn(rdfvalue.RDFURN("aff4:/bars"), datastores)

  def testGetAllFiles(self):
    with test_lib.AutoTempDirPath(remove_non_empty=True) as tmpdir_path:
      foo_path = test_lib.TempFilePath(suffix="foo.yaml")
      bar_path = test_lib.TempFilePath(suffix="bar.json")
      baz_path = test_lib.TempFilePath(suffix="baz.yaml")
      quux_path = test_lib.TempFilePath(dir=tmpdir_path, suffix="quux.yaml")
      norf_path = test_lib.TempFilePath(dir=tmpdir_path, suffix="norf.json")
      thud_path = test_lib.TempFilePath(dir=tmpdir_path, suffix="thud.xml")

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

  @mock.patch("logging.warn")
  def testGetAllFilesErrors(self, warn):
    with test_lib.AutoTempDirPath() as foo_dirpath,\
         test_lib.AutoTempDirPath() as bar_dirpath:
      self.assertTrue(self.sources.AddDir(foo_dirpath))
      self.assertTrue(self.sources.AddDir("/baz/quux/norf"))
      self.assertTrue(self.sources.AddDir(bar_dirpath))
      self.assertTrue(self.sources.AddDir("/thud"))
      self.assertTrue(self.sources.AddDir("/foo/bar"))

      files = list(self.sources.GetAllFiles())
      self.assertFalse(files)

      self.assertTrue(warn.called)
      self.assertEqual(warn.call_count, 3)


class ArtifactTest(unittest.TestCase):

  def testValidateSyntaxSimple(self):
    artifact = ar.Artifact(
        name="Foo",
        doc="This is Foo.",
        provides=["fqdn", "domain"],
        supported_os=["Windows"],
        urls=["https://example.com"])
    artifact.ValidateSyntax()

  def testValidateSyntaxWithSources(self):
    registry_key_source = {
        "type": ar.ArtifactSource.SourceType.REGISTRY_KEY,
        "attributes": {
            "keys": [
                r"%%current_control_set%%\Control\Session "
                r"Manager\Environment\Path"
            ],
        }
    }

    file_source = {
        "type": ar.ArtifactSource.SourceType.FILE,
        "attributes": {
            "paths": [r"%%environ_systemdrive%%\Temp"]
        }
    }

    artifact = ar.Artifact(
        name="Bar",
        doc="This is Bar.",
        provides=["environ_windir"],
        supported_os=["Windows"],
        urls=["https://example.com"],
        sources=[registry_key_source, file_source])
    artifact.ValidateSyntax()

  def testValidateSyntaxMissingDoc(self):
    artifact = ar.Artifact(name="Baz", provides=["os"], supported_os=["Linux"])

    with self.assertRaisesRegexp(ar.ArtifactSyntaxError, "missing doc"):
      artifact.ValidateSyntax()

  def testValidateSyntaxInvalidSupportedOs(self):
    artifact = ar.Artifact(
        name="Quux",
        doc="This is Quux.",
        provides=["os"],
        labels=["Cloud", "Logs"],
        supported_os=["Solaris"])

    with self.assertRaisesRegexp(ar.ArtifactSyntaxError, "'Solaris'"):
      artifact.ValidateSyntax()

  def testValidateSyntaxInvalidLabel(self):
    artifact = ar.Artifact(
        name="Norf",
        doc="This is Norf.",
        provides=["domain"],
        labels=["Mail", "Browser", "Reddit"],
        supported_os=["Darwin"])

    with self.assertRaisesRegexp(ar.ArtifactSyntaxError, "'Reddit'"):
      artifact.ValidateSyntax()

  def testValidateSyntaxBrokenProvides(self):
    artifact = ar.Artifact(
        name="Thud",
        doc="This is Thud.",
        provides=["fqdn", "garbage"],
        labels=["Network"])

    with self.assertRaisesRegexp(ar.ArtifactSyntaxError, "'garbage'"):
      artifact.ValidateSyntax()

  def testValidateSyntaxBadSource(self):
    source = {
        "type": ar.ArtifactSource.SourceType.ARTIFACT_GROUP,
        "attributes": {}
    }

    artifact = ar.Artifact(
        name="Barf",
        doc="This is Barf.",
        provides=["os"],
        labels=["Logs", "Memory"],
        sources=[source])

    with self.assertRaisesRegexp(ar.ArtifactSyntaxError, "required attributes"):
      artifact.ValidateSyntax()


class ArtifactSourceTest(unittest.TestCase):

  def testValidateDirectory(self):
    source = ar.ArtifactSource(
        type=ar.ArtifactSource.SourceType.DIRECTORY,
        attributes={
            "paths": ["/home", "/usr"],
        })

    source.Validate()

  def testValidateRegistrykey(self):
    source = ar.ArtifactSource(
        type=ar.ArtifactSource.SourceType.REGISTRY_KEY,
        attributes={
            "keys": [r"Foo\Bar\Baz"],
        })

    source.Validate()

  def testValidateCommand(self):
    source = ar.ArtifactSource(
        type=ar.ArtifactSource.SourceType.COMMAND,
        attributes={
            "cmd": "quux",
            "args": ["-foo", "-bar"],
        })

    source.Validate()

  def testValidateCommandWithSingleArgumentContainingSpace(self):
    source = ar.ArtifactSource(
        type=ar.ArtifactSource.SourceType.COMMAND,
        attributes={
            "cmd": "quux",
            "args": ["-foo -bar"],
        })

    with self.assertRaisesRegexp(ar.ArtifactSourceSyntaxError, "'-foo -bar'"):
      source.Validate()

  def testValidatePathsIsAList(self):
    source = ar.ArtifactSource(
        type=ar.ArtifactSource.SourceType.FILE, attributes={
            "paths": "/bin",
        })

    with self.assertRaisesRegexp(ar.ArtifactSourceSyntaxError, "not a list"):
      source.Validate()

  def testValidatePathIsAString(self):
    source = ar.ArtifactSource(
        type=ar.ArtifactSource.SourceType.ARTIFACT_GROUP,
        attributes={
            "names": ["Foo", "Bar"],
            "path": ["/tmp", "/var"],
        })

    with self.assertRaisesRegexp(ar.ArtifactSourceSyntaxError, "not a string"):
      source.Validate()

  def testValidateMissingRequiredAttributes(self):
    source = ar.ArtifactSource(
        type=ar.ArtifactSource.SourceType.GREP,
        attributes={
            "paths": ["/etc", "/dev", "/opt"],
        })

    expected = "missing required attributes: 'content_regex_list'"
    with self.assertRaisesRegexp(ar.ArtifactSourceSyntaxError, expected):
      source.Validate()


if __name__ == "__main__":
  unittest.main()
