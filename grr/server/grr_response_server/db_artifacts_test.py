#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib.rdfvalues import artifacts as rdf_artifacts
from grr_response_server import db


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
