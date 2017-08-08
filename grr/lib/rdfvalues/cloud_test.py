#!/usr/bin/env python
"""Tests for grr.lib.rdfvalues.cloud."""


from grr.lib import flags
from grr.lib.rdfvalues import cloud
from grr.test_lib import test_lib


class CloudTest(test_lib.GRRBaseTest):

  def testMakeGoogleUniqueID(self):
    google_cloud_instance = cloud.GoogleCloudInstance(
        instance_id="1771384456894610289",
        zone="projects/123456789733/zones/us-central1-a",
        project_id="myproject")
    self.assertEqual(
        cloud.MakeGoogleUniqueID(google_cloud_instance),
        "us-central1-a/myproject/1771384456894610289")


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
