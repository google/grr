#!/usr/bin/env python
"""Generator of regression tests data for API call handlers."""



# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
from grr.gui.api_plugins import tests as tests_lib
# pylint: enable=unused-import,g-bad-import-order

import json

from grr.gui import api_test_lib
from grr.gui import http_api

from grr.lib import flags
from grr.lib import startup


def GroupRegressionTestsByHandler():
  result = {}
  for cls in api_test_lib.ApiCallHandlerRegressionTest.classes.values():
    if getattr(cls, "handler", None):
      result.setdefault(cls.handler, []).append(cls)

  return result


def main(unused_argv):
  sample_data = {}

  tests = GroupRegressionTestsByHandler()
  for handler, test_classes in tests.items():

    for test_class in sorted(test_classes, key=lambda cls: cls.__name__):
      if flags.FLAGS.tests and test_class.__name__ not in flags.FLAGS.tests:
        continue

      test_instance = test_class()

      # Recreate a new data store each time.
      startup.TestInit()
      try:
        test_instance.setUp()

        test_instance.Run()
        sample_data.setdefault(handler, []).extend(test_instance.checks)
      finally:
        try:
          test_instance.tearDown()
        except Exception:  # pylint: disable=broad-except
          pass

  encoded_sample_data = json.dumps(
      sample_data,
      indent=2,
      sort_keys=True,
      separators=(",", ": "),
      cls=http_api.JSONEncoderWithRDFPrimitivesSupport)
  print encoded_sample_data


if __name__ == "__main__":
  flags.StartMain(main)
