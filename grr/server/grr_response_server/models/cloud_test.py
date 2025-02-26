#!/usr/bin/env python
from absl.testing import absltest

from grr_response_proto import jobs_pb2
from grr_response_server.models import cloud as models_cloud


class CloudTest(absltest.TestCase):

  def testMakeGoogleUniqueID(self):
    google_cloud_instance = jobs_pb2.GoogleCloudInstance(
        instance_id="1771384456894610289",
        zone="projects/123456789733/zones/us-central1-a",
        project_id="myproject",
    )
    self.assertEqual(
        models_cloud.MakeGoogleUniqueID(google_cloud_instance),
        "us-central1-a/myproject/1771384456894610289",
    )


if __name__ == "__main__":
  absltest.main()
