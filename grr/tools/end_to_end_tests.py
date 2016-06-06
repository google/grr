#!/usr/bin/env python
"""Helper script for running endtoend tests."""

import unittest

import logging

# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.endtoend_tests import base
from grr.lib import access_control
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import startup
from grr.lib.aff4_objects import users as aff4_users

flags.DEFINE_bool("local_client", True,
                  "The target client(s) are running locally.")

flags.DEFINE_bool("local_worker", False, "Run tests with a local worker.")

flags.DEFINE_list("client_ids", [],
                  "List of client ids to test. If unset we use "
                  "Test.end_to_end_client_ids from the config.")

flags.DEFINE_list("hostnames", [],
                  "List of client hostnames to test. If unset we use "
                  "Test.end_to_end_client_hostnames from the config.")

flags.DEFINE_list("testnames", [],
                  "List of test names to run. If unset we run all "
                  "relevant tests.")


def RunEndToEndTests():
  runner = unittest.TextTestRunner()

  # We are running a test so let the config system know that.
  config_lib.CONFIG.AddContext("Test Context",
                               "Context applied when we run tests.")
  startup.Init()

  token = access_control.ACLToken(username="GRREndToEndTest",
                                  reason="Running end to end client tests.")

  # We need this for the launchbinary test
  with aff4.FACTORY.Create("aff4:/users/GRREndToEndTest",
                           aff4_users.GRRUser,
                           mode="rw",
                           token=token) as test_user:
    test_user.AddLabels("admin")

  client_id_set = base.GetClientTestTargets(client_ids=flags.FLAGS.client_ids,
                                            hostnames=flags.FLAGS.hostnames,
                                            checkin_duration_threshold="1h",
                                            token=token)

  for cls in base.ClientTestBase.classes.values():
    for p in cls.platforms:
      if p not in set(["Linux", "Darwin", "Windows"]):
        raise ValueError("Unsupported platform: %s in class %s" %
                         (p, cls.__name__))

  if not client_id_set:
    print("No clients to test on.  Define Test.end_to_end_client* config "
          "options, or pass them as parameters.")

  results_by_client = {}
  for client in aff4.FACTORY.MultiOpen(client_id_set, token=token):
    client_summary = client.GetSummary()

    if hasattr(client_summary, "system_info"):
      sysinfo = client_summary.system_info
    else:
      raise RuntimeError("Unknown system type, likely waiting on interrogate"
                         " to complete.")

    results = {}
    results_by_client[client.urn] = results
    for cls in base.ClientTestBase.classes.values():
      if flags.FLAGS.testnames and (cls.__name__ not in flags.FLAGS.testnames):
        continue

      if not aff4.issubclass(cls, base.ClientTestBase):
        continue

      if cls.__name__.startswith("Abstract"):
        continue

      # Fix the call method so we can use the test runner.  See doco in
      # base.ClientTestBase
      def _RealCall(testcase, *args, **kwds):
        return testcase.run(*args, **kwds)

      cls.__call__ = _RealCall

      if sysinfo.system in cls.platforms:
        print "Running %s on %s (%s: %s, %s, %s)" % (cls.__name__,
                                                     client_summary.client_id,
                                                     sysinfo.fqdn,
                                                     sysinfo.system,
                                                     sysinfo.version,
                                                     sysinfo.machine)

        try:
          # Mixin the unittest framework so we can use the test runner to run
          # the test and get nice output.  We don't want to depend on unitttest
          # code in the tests themselves.
          testcase = cls(client_id=client_summary.client_id,
                         platform=sysinfo.system,
                         token=token,
                         local_client=flags.FLAGS.local_client,
                         local_worker=flags.FLAGS.local_worker)
          results[cls.__name__] = runner.run(testcase)
        except Exception:  # pylint: disable=broad-except
          logging.exception("Failed to run test %s", cls)

    # Print a little summary.

    for client, results in results_by_client.iteritems():
      print "Results for %s:" % client
      for testcase, result in sorted(results.items()):
        res = "[  OK  ]"
        if result.errors or result.failures:
          res = "[ FAIL ]"
        print "%45s: %s" % (testcase, res)


def main(unused_argv):
  RunEndToEndTests()


if __name__ == "__main__":
  flags.StartMain(main)
