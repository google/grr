#!/usr/bin/env python
from absl import app
from absl.testing import absltest

from grr_response_proto import flows_pb2
from grr_response_proto import hunts_pb2
from grr_response_server.models import hunts as models_hunts
from grr.test_lib import test_lib


class HuntsTest(absltest.TestCase):

  def testCreateHunt_UsesDefaultValues(self):
    with test_lib.ConfigOverrider({
        "Hunt.default_crash_limit": 10,
        "Hunt.default_avg_results_per_client_limit": 20,
        "Hunt.default_avg_cpu_seconds_per_client_limit": 30,
        "Hunt.default_avg_network_bytes_per_client_limit": 40,
    }):
      hunt = models_hunts.CreateHuntFromHuntRunnerArgs(
          flows_pb2.HuntRunnerArgs()
      )
      self.assertEqual(hunt.crash_limit, 10)
      self.assertEqual(hunt.avg_results_per_client_limit, 20)
      self.assertEqual(hunt.avg_cpu_seconds_per_client_limit, 30)
      self.assertEqual(hunt.avg_network_bytes_per_client_limit, 40)

      self.assertEqual(hunt.hunt_state, hunts_pb2.Hunt.HuntState.PAUSED)
      self.assertEqual(hunt.client_rate, 20.5)
      self.assertEqual(hunt.client_limit, 100)
      self.assertEqual(hunt.duration, 2 * 7 * 24 * 60 * 60)

  def testCreateHunt_DoesOverwriteDefaultValuesIfValuesAreExplicitlySet(self):
    with test_lib.ConfigOverrider({
        "Hunt.default_crash_limit": 100,
        "Hunt.default_avg_results_per_client_limit": 200,
        "Hunt.default_avg_cpu_seconds_per_client_limit": 300,
        "Hunt.default_avg_network_bytes_per_client_limit": 400,
    }):
      hunt = models_hunts.CreateHuntFromHuntRunnerArgs(
          flows_pb2.HuntRunnerArgs(
              crash_limit=1,
              avg_results_per_client_limit=2,
              avg_cpu_seconds_per_client_limit=3,
              avg_network_bytes_per_client_limit=4,
              client_rate=5,
              client_limit=6,
              expiry_time=7,
          )
      )
      self.assertEqual(hunt.crash_limit, 1)
      self.assertEqual(hunt.avg_results_per_client_limit, 2)
      self.assertEqual(hunt.avg_cpu_seconds_per_client_limit, 3)
      self.assertEqual(hunt.avg_network_bytes_per_client_limit, 4)

      self.assertEqual(hunt.client_rate, 5)
      self.assertEqual(hunt.client_limit, 6)
      self.assertEqual(hunt.duration, 7)


def main(argv):
  # Initializes `config.CONFIG`.
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
