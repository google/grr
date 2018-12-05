#!/usr/bin/env python
"""Tests for grr.lib.rdfvalues.cloud."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from grr_response_core.lib import flags
from grr_response_core.lib.rdfvalues import cloud as rdf_cloud
from grr.test_lib import test_lib


class CloudTest(test_lib.GRRBaseTest):

  def testMakeGoogleUniqueID(self):
    google_cloud_instance = rdf_cloud.GoogleCloudInstance(
        instance_id="1771384456894610289",
        zone="projects/123456789733/zones/us-central1-a",
        project_id="myproject")
    self.assertEqual(
        rdf_cloud.MakeGoogleUniqueID(google_cloud_instance),
        "us-central1-a/myproject/1771384456894610289")


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
