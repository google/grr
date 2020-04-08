#!/usr/bin/env python
from absl.testing import absltest

from grr_response_server import cronjobs
from grr_response_server.rdfvalues import cronjobs as rdf_cronjobs
from grr.test_lib import test_lib
from grr.test_lib import testing_startup


class CronJobRegistryTest(test_lib.GRRBaseTest):

  @classmethod
  def setUpClass(cls):
    super(CronJobRegistryTest, cls).setUpClass()
    testing_startup.TestInit()

  # TODO: Remove once metaclass registry madness is resolved.
  def testCronJobRegistryInstantiation(self):
    # We import the `server_startup` module to ensure that all cron jobs classes
    # that are really used on the server are imported and populate the registry.
    # pylint: disable=unused-variable, g-import-not-at-top
    from grr_response_server import server_startup
    # pylint: enable=unused-variable, g-import-not-at-top

    for job_cls in cronjobs.CronJobRegistry.CRON_REGISTRY.values():
      job = rdf_cronjobs.CronJob(cron_job_id="foobar")
      job_run = rdf_cronjobs.CronJobRun(cron_job_id="foobar", status="RUNNING")

      job_cls(job_run, job)  # Should not fail.


if __name__ == "__main__":
  absltest.main()
