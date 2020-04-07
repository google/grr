#!/usr/bin/env python
# Lint as: python3
# -*- encoding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib.rdfvalues import artifacts as rdf_artifacts
from grr_response_server import artifact_registry
from grr_response_server.databases import db


class DatabaseTestArtifactsMixin(object):

  def testReadArtifactThrowsForUnknownArtifacts(self):
    with self.assertRaises(db.UnknownArtifactError) as context:
      self.db.ReadArtifact("Foo")

    self.assertEqual(context.exception.name, "Foo")

  def testReadArtifactReadsWritten(self):
    artifact = rdf_artifacts.Artifact(
        name="Foo",
        doc="Lorem ipsum dolor sit amet.",
        labels=["foo", "bar", "baz"],
        urls=["http://example.com/foo"])

    self.db.WriteArtifact(artifact)

    result = self.db.ReadArtifact("Foo")
    self.assertEqual(result.name, "Foo")
    self.assertEqual(result.doc, "Lorem ipsum dolor sit amet.")
    self.assertEqual(result.labels, ["foo", "bar", "baz"])
    self.assertEqual(result.urls, ["http://example.com/foo"])

  def testReadArtifactReadsCopy(self):
    self.db.WriteArtifact(rdf_artifacts.Artifact(name="Foo"))
    self.db.ReadArtifact("Foo").name = "Bar"
    self.assertEqual(self.db.ReadArtifact("Foo").name, "Foo")

  def testWriteArtifactThrowsForDuplicatedArtifacts(self):
    self.db.WriteArtifact(rdf_artifacts.Artifact(name="Foo", doc="Lorem."))

    with self.assertRaises(db.DuplicatedArtifactError) as context:
      self.db.WriteArtifact(rdf_artifacts.Artifact(name="Foo", doc="Ipsum."))

    self.assertEqual(context.exception.name, "Foo")

  def testWriteArtifactThrowsForEmptyName(self):
    with self.assertRaises(ValueError):
      self.db.WriteArtifact(rdf_artifacts.Artifact(name=""))

  def testWriteAndReadArtifactWithLongName(self):
    name = "x" + "🧙" * (db.MAX_ARTIFACT_NAME_LENGTH - 2) + "x"
    self.db.WriteArtifact(rdf_artifacts.Artifact(name=name))
    self.assertEqual(self.db.ReadArtifact(name).name, name)

  def testWriteArtifactRaisesWithTooLongName(self):
    name = "a" * (db.MAX_ARTIFACT_NAME_LENGTH + 1)
    with self.assertRaises(ValueError):
      self.db.WriteArtifact(rdf_artifacts.Artifact(name=name))

  def testWriteArtifactWithSources(self):
    file_source = rdf_artifacts.ArtifactSource(
        type=rdf_artifacts.ArtifactSource.SourceType.FILE,
        conditions=["os_major_version < 6"],
        attributes={
            "paths": ["/tmp/foo", "/tmp/bar"],
        })

    registry_key_source = rdf_artifacts.ArtifactSource(
        type=rdf_artifacts.ArtifactSource.SourceType.REGISTRY_KEY,
        attributes={
            "key_value_pairs": [{
                "key": "HKEY_LOCAL_MACHINE\\Foo\\Bar\\Baz",
                "value": "Quux"
            },],
        })

    artifact = rdf_artifacts.Artifact(
        name="Foo",
        sources=[file_source, registry_key_source],
        labels=["quux"],
        supported_os=["Windows", "Linux"],
        urls=["http://foobar.com/"])

    self.db.WriteArtifact(artifact)
    self.assertEqual(self.db.ReadArtifact("Foo"), artifact)

  def testWriteArtifactMany(self):
    for i in range(42):
      self.db.WriteArtifact(rdf_artifacts.Artifact(name="Art%s" % i))

    for i in range(42):
      self.assertEqual(self.db.ReadArtifact("Art%s" % i).name, "Art%s" % i)

  def testWriteArtifactWritesCopy(self):
    artifact = rdf_artifacts.Artifact()

    artifact.name = "Foo"
    artifact.doc = "Lorem ipsum."
    self.db.WriteArtifact(artifact)

    artifact.name = "Bar"
    artifact.doc = "Dolor sit amet."
    self.db.WriteArtifact(artifact)

    foo = self.db.ReadArtifact("Foo")
    self.assertEqual(foo.name, "Foo")
    self.assertEqual(foo.doc, "Lorem ipsum.")

    bar = self.db.ReadArtifact("Bar")
    self.assertEqual(bar.name, "Bar")
    self.assertEqual(bar.doc, "Dolor sit amet.")

  def testDeleteArtifactThrowsForUnknownArtifacts(self):
    with self.assertRaises(db.UnknownArtifactError) as context:
      self.db.DeleteArtifact("Quux")

    self.assertEqual(context.exception.name, "Quux")

  def testDeleteArtifactDeletesSingle(self):
    self.db.WriteArtifact(rdf_artifacts.Artifact(name="Foo"))
    self.db.DeleteArtifact("Foo")

    with self.assertRaises(db.UnknownArtifactError):
      self.db.ReadArtifact("Foo")

  def testDeleteArtifactDeletesMultiple(self):
    for i in range(42):
      self.db.WriteArtifact(rdf_artifacts.Artifact(name="Art%s" % i))

    for i in range(42):
      if i % 2 == 0:
        continue

      self.db.DeleteArtifact("Art%s" % i)

    for i in range(42):
      if i % 2 == 0:
        self.assertEqual(self.db.ReadArtifact("Art%s" % i).name, "Art%s" % i)
      else:
        with self.assertRaises(db.UnknownArtifactError):
          self.db.ReadArtifact("Art%s" % i)

  def testReadAllArtifactsEmpty(self):
    self.assertEqual(self.db.ReadAllArtifacts(), [])

  def testReadAllArtifactsReturnsAllArtifacts(self):
    artifacts = []
    for i in range(42):
      artifacts.append(rdf_artifacts.Artifact(name="Art%s" % i))

    for artifact in artifacts:
      self.db.WriteArtifact(artifact)

    self.assertCountEqual(self.db.ReadAllArtifacts(), artifacts)

  def testReadAllArtifactsReturnsCopy(self):
    name = lambda artifact: artifact.name

    self.db.WriteArtifact(rdf_artifacts.Artifact(name="Foo"))
    self.db.WriteArtifact(rdf_artifacts.Artifact(name="Bar"))

    artifacts = self.db.ReadAllArtifacts()
    self.assertCountEqual(map(name, artifacts), ["Foo", "Bar"])

    artifacts[0].name = "Quux"
    artifacts[1].name = "Norf"

    artifacts = self.db.ReadAllArtifacts()
    self.assertCountEqual(map(name, artifacts), ["Foo", "Bar"])

  # TODO: Remove once artifact patching is no longer needed.
  def testReadArtifactPatching(self):
    source = rdf_artifacts.ArtifactSource()
    source.type = rdf_artifacts.ArtifactSource.SourceType.GREP
    source.attributes = {
        b"paths": ["foo/bar", "norf/thud"],
        b"content_regex_list": ["ba[rz]"],
    }

    artifact = rdf_artifacts.Artifact()
    artifact.name = "foobar"
    artifact.sources = [source]

    self.db.WriteArtifact(artifact)

    artifact = self.db.ReadArtifact("foobar")
    self.assertLen(artifact.sources, 1)

    source = artifact.sources[0]
    source.Validate()  # Should not raise.
    self.assertEqual(source.attributes["paths"], ["foo/bar", "norf/thud"])
    self.assertEqual(source.attributes["content_regex_list"], ["ba[rz]"])

    # Should not raise.
    source.Validate()

    self.assertEqual(artifact, self.db.ReadArtifact("foobar"))

  def testReadArtifactPatchingDeep(self):
    source = rdf_artifacts.ArtifactSource()
    source.type = rdf_artifacts.ArtifactSource.SourceType.REGISTRY_VALUE
    source.attributes = {
        b"key_value_pairs": [
            {
                b"key": "foo",
                b"value": "bar",
            },
            {
                b"key": b"quux",
                b"value": 1337,
            },
        ],
    }

    artifact = rdf_artifacts.Artifact()
    artifact.name = "foobar"
    artifact.doc = "Lorem ipsum."
    artifact.sources = [source]

    self.db.WriteArtifact(artifact)

    artifact = self.db.ReadArtifact("foobar")
    artifact_registry.Validate(artifact)  # Should not raise.

    self.assertLen(artifact.sources, 1)

    source = artifact.sources[0]
    self.assertEqual(source.attributes["key_value_pairs"][0]["key"], "foo")
    self.assertEqual(source.attributes["key_value_pairs"][0]["value"], "bar")
    self.assertEqual(source.attributes["key_value_pairs"][1]["key"], "quux")
    self.assertEqual(source.attributes["key_value_pairs"][1]["value"], 1337)

    # Read again, to ensure that we retrieve what is stored in the database.
    artifact = self.db.ReadArtifact("foobar")
    artifact_registry.Validate(artifact)  # Should not raise.

  # TODO: Remove once artifact patching is no longer needed.
  def testReadAllArtifactsPatching(self):
    source0 = rdf_artifacts.ArtifactSource()
    source0.type = rdf_artifacts.ArtifactSource.SourceType.PATH
    source0.attributes = {
        b"paths": ["norf/thud"],
    }

    source1 = rdf_artifacts.ArtifactSource()
    source1.type = rdf_artifacts.ArtifactSource.SourceType.COMMAND
    source1.attributes = {
        b"cmd": "quux",
        b"args": ["foo", "bar"],
    }

    artifact = rdf_artifacts.Artifact()
    artifact.name = "foobar"
    artifact.sources = [source0, source1]

    self.db.WriteArtifact(artifact)

    artifacts = self.db.ReadAllArtifacts()
    self.assertLen(artifacts, 1)
    self.assertEqual(artifacts[0].sources[0].attributes["paths"], ["norf/thud"])
    self.assertEqual(artifacts[0].sources[1].attributes["cmd"], "quux")
    self.assertEqual(artifacts[0].sources[1].attributes["args"], ["foo", "bar"])

    # Should not raise.
    artifacts[0].sources[0].Validate()
    artifacts[0].sources[1].Validate()


# This file is a test library and thus does not require a __main__ block.
