#!/usr/bin/env python
from absl.testing import absltest

from grr_response_server.gui import api_integration_test_lib
from grr.test_lib import testing_startup


class ArtifactTest(api_integration_test_lib.ApiIntegrationTest):

  @classmethod
  def setUpClass(cls):
    testing_startup.TestInit()
    super().setUpClass()

  def testUploadArtifact(self):
    self.api.UploadArtifact(yaml="""
name: Foo
doc: Lorem ipsum dolor sit amet.
sources:
- type: FILE
  attributes:
    paths:
      - '%%users.homedir%%/foo.txt'
supported_os: [Linux]
urls:
- 'https://example.com'
    """)

    artifacts = list(self.api.ListArtifacts())
    artifact_names = [_.data.artifact.name for _ in artifacts]

    self.assertIn("Foo", artifact_names)

  def testUploadArtifactMulti(self):
    self.api.UploadArtifact(yaml="""
name: Foo
doc: Lorem ipsum dolor sit amet.
sources:
- type: FILE
  attributes:
    paths:
      - '%%users.homedir%%/foo.txt'
supported_os: [Linux]
urls:
- 'https://example.com'
---
name: Bar
doc: Ut enim ad minim veniam.
sources:
- type: FILE
  attributes:
    paths:
      - '%%users.homedir%%/bar.txt'
supported_os: [Linux]
urls:
- 'https://example.com'
    """)

    artifacts = list(self.api.ListArtifacts())
    artifact_names = [_.data.artifact.name for _ in artifacts]

    self.assertIn("Foo", artifact_names)
    self.assertIn("Bar", artifact_names)

  def testUploadArtifactInvalid(self):
    with self.assertRaises(Exception) as context:
      self.api.UploadArtifact(yaml="""
name: Foo
sources:
- type: NOT_A_SOURCE
      """)

    self.assertIn("not a valid enum value", str(context.exception))


if __name__ == "__main__":
  absltest.main()
