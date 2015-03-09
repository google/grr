#!/usr/bin/env python
"""A library for check-specific tests."""
import collections
import os


import yaml

from grr.lib import config_lib
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import test_lib
from grr.lib import type_info
from grr.lib.checks import checks
from grr.lib.checks import filters
from grr.lib.checks import hints


class HostCheckTest(test_lib.GRRBaseTest):
  """The base class for host check tests."""
  __metaclass__ = registry.MetaclassRegistry

  def TestDataPath(self, file_name):
    path = os.path.join(config_lib.CONFIG["Test.data_dir"], file_name)
    if not os.path.isfile(path):
      raise test_lib.Error("Missing test data: %s" % file_name)
    return path

  def LoadCheck(self, cfg_file, *check_ids):
    cfg = os.path.join(config_lib.CONFIG["Test.srcdir"], "grr", "checks",
                       cfg_file)
    if check_ids:
      for chk_id in check_ids:
        checks.LoadCheckFromFile(cfg, chk_id)
    else:
      checks.LoadChecksFromFiles([cfg])

  def SetKnowledgeBase(self, hostname, host_os, host_data):
    kb = rdfvalue.KnowledgeBase()
    kb.hostname = hostname
    kb.os = host_os
    host_data["KnowledgeBase"] = kb

  def AddData(self, parser, *args, **kwargs):
    # Initialize the parser and add parsed data to host_data.
    return [parser().Parse(*args, **kwargs)]

  def RunChecks(self, host_data):
    return {r.check_id: r for r in checks.CheckHost(host_data)}

  def GetCheckErrors(self, check_spec):
    errors = []
    try:
      check = rdfvalue.Check(**check_spec)
      check.Validate()
    except (checks.Error, filters.Error, hints.Error, type_info.Error) as e:
      errors.append(str(e))
    except Exception as e:
      # TODO(user): More granular exception handling.
      errors.append("Unknown error %s: %s" % (type(e), e))
    return errors

  def assertRanChecks(self, check_ids, results):
    self.assertItemsEqual(check_ids, results.keys())

  def assertResultEqual(self, rslt1, rslt2):
    # Build a map of anomaly explanations to findings.
    if rslt1.check_id != rslt2.check_id:
      self.fail("Check IDs differ: %s vs %s" % (rslt1.check_id, rslt2.check_id))

    # Quick check to see if anomaly counts are the same and they have the same
    # ordering, using explanation as a measure.
    rslt1_anoms = {a.explanation: str(a) for a in rslt1.anomaly}
    rslt2_anoms = {a.explanation: str(a) for a in rslt2.anomaly}
    self.assertItemsEqual(rslt1_anoms, rslt2_anoms,
                          "Results have different anomaly items.")

    # Now check that the anomalies are the same.
    for anom1, anom2 in zip(rslt1_anoms.itervalues(), rslt2_anoms.itervalues()):
      self.assertEqual(anom1, anom2)

  def assertIsCheckIdResult(self, rslt, expected):
    self.assertIsInstance(rslt, rdfvalue.CheckResult)
    self.assertEqual(expected, rslt.check_id)

  def assertValidCheck(self, check_spec):
    errors = self.GetCheckErrors(check_spec)
    if errors:
      self.fail("\n".join(errors))

  def assertValidCheckFile(self, path):
    # Figure out the relative path of the check files.
    prefix = os.path.commonprefix(config_lib.CONFIG["Checks.config_dir"])
    relpath = os.path.relpath(path, prefix)
    # If the config can't load fail immediately.
    try:
      configs = checks.LoadConfigsFromFile(path)
    except yaml.error.YAMLError as e:
      self.fail("File %s could not be parsed: %s\n" % (relpath, e))
    # Otherwise, check all the configs and pass/fail at the end.
    errors = collections.OrderedDict()
    for check_id, check_spec in configs.iteritems():
      check_errors = self.GetCheckErrors(check_spec)
      if check_errors:
        msg = errors.setdefault(relpath, ["check_id: %s" % check_id])
        msg.append(check_errors)
    if errors:
      message = ""
      for k, v in errors.iteritems():
        message += "File %s errors:\n" % k
        message += "  %s\n" % v[0]
        for err in v[1]:
          message += "    %s\n" % err
      self.fail(message)

