#!/usr/bin/env python
from grr_response_core.lib.rdfvalues import mig_protodict
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_proto import artifact_pb2
from grr_response_server.databases import db


class DatabaseTestArtifactsMixin(object):

  def testReadArtifactThrowsForUnknownArtifacts(self):
    with self.assertRaises(db.UnknownArtifactError) as context:
      self.db.ReadArtifact("Foo")

    self.assertEqual(context.exception.name, "Foo")

  def testReadArtifactReadsWritten(self):
    artifact = artifact_pb2.Artifact(
        name="Foo",
        doc="Lorem ipsum dolor sit amet.",
        urls=["http://example.com/foo"],
    )

    self.db.WriteArtifact(artifact)

    result = self.db.ReadArtifact("Foo")
    self.assertEqual(result.name, "Foo")
    self.assertEqual(result.doc, "Lorem ipsum dolor sit amet.")
    self.assertEqual(result.urls, ["http://example.com/foo"])

  def testReadArtifactReadsCopy(self):
    self.db.WriteArtifact(artifact_pb2.Artifact(name="Foo"))
    self.db.ReadArtifact("Foo").name = "Bar"
    self.assertEqual(self.db.ReadArtifact("Foo").name, "Foo")

  def testWriteArtifactThrowsForDuplicatedArtifacts(self):
    self.db.WriteArtifact(artifact_pb2.Artifact(name="Foo", doc="Lorem."))

    with self.assertRaises(db.DuplicatedArtifactError) as context:
      self.db.WriteArtifact(artifact_pb2.Artifact(name="Foo", doc="Ipsum."))

    self.assertEqual(context.exception.name, "Foo")

  def testWriteArtifactThrowsForEmptyName(self):
    with self.assertRaises(ValueError):
      self.db.WriteArtifact(artifact_pb2.Artifact(name=""))

  def testWriteAndReadArtifactWithLongName(self):
    name = "x" + "🧙" * (db.MAX_ARTIFACT_NAME_LENGTH - 2) + "x"
    self.db.WriteArtifact(artifact_pb2.Artifact(name=name))
    self.assertEqual(self.db.ReadArtifact(name).name, name)

  def testWriteArtifactRaisesWithTooLongName(self):
    name = "a" * (db.MAX_ARTIFACT_NAME_LENGTH + 1)
    with self.assertRaises(ValueError):
      self.db.WriteArtifact(artifact_pb2.Artifact(name=name))

  def testWriteArtifactWithSources(self):
    file_source = artifact_pb2.ArtifactSource(
        type=artifact_pb2.ArtifactSource.SourceType.FILE,
        conditions=["os_major_version < 6"],
        attributes=mig_protodict.ToProtoDict(
            rdf_protodict.Dict().FromDict({
                "paths": ["/tmp/foo", "/tmp/bar"],
            })
        ),
    )

    registry_key_source = artifact_pb2.ArtifactSource(
        type=artifact_pb2.ArtifactSource.SourceType.REGISTRY_KEY,
        attributes=mig_protodict.ToProtoDict(
            rdf_protodict.Dict().FromDict({
                "key_value_pairs": [
                    {
                        "key": "HKEY_LOCAL_MACHINE\\Foo\\Bar\\Baz",
                        "value": "Quux",
                    },
                ],
            })
        ),
    )

    artifact = artifact_pb2.Artifact(
        name="Foo",
        sources=[file_source, registry_key_source],
        supported_os=["Windows", "Linux"],
        urls=["http://foobar.com/"],
    )

    self.db.WriteArtifact(artifact)
    self.assertEqual(self.db.ReadArtifact("Foo"), artifact)

  def testWriteArtifactMany(self):
    for i in range(42):
      self.db.WriteArtifact(artifact_pb2.Artifact(name="Art%s" % i))

    for i in range(42):
      self.assertEqual(self.db.ReadArtifact("Art%s" % i).name, "Art%s" % i)

  def testWriteArtifactWritesCopy(self):
    artifact = artifact_pb2.Artifact()

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
    self.db.WriteArtifact(artifact_pb2.Artifact(name="Foo"))
    self.db.DeleteArtifact("Foo")

    with self.assertRaises(db.UnknownArtifactError):
      self.db.ReadArtifact("Foo")

  def testDeleteArtifactDeletesMultiple(self):
    for i in range(42):
      self.db.WriteArtifact(artifact_pb2.Artifact(name="Art%s" % i))

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
      artifacts.append(artifact_pb2.Artifact(name="Art%s" % i))

    for artifact in artifacts:
      self.db.WriteArtifact(artifact)

    self.assertCountEqual(self.db.ReadAllArtifacts(), artifacts)

  def testReadAllArtifactsReturnsCopy(self):
    name = lambda artifact: artifact.name

    self.db.WriteArtifact(artifact_pb2.Artifact(name="Foo"))
    self.db.WriteArtifact(artifact_pb2.Artifact(name="Bar"))

    artifacts = self.db.ReadAllArtifacts()
    self.assertCountEqual(map(name, artifacts), ["Foo", "Bar"])

    artifacts[0].name = "Quux"
    artifacts[1].name = "Norf"

    artifacts = self.db.ReadAllArtifacts()
    self.assertCountEqual(map(name, artifacts), ["Foo", "Bar"])


# This file is a test library and thus does not require a __main__ block.
