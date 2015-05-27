#!/usr/bin/env python
"""A library for check-specific tests."""
import collections
import os
import StringIO


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
      loaded = []
      for chk_id in check_ids:
        loaded.append(checks.LoadCheckFromFile(cfg, chk_id))
      return loaded
    else:
      return checks.LoadChecksFromFiles([cfg])

  def SetKnowledgeBase(self, hostname="test.example.com", host_os="Linux",
                       host_data=None):
    if not host_data:
      host_data = {}
    kb = rdfvalue.KnowledgeBase()
    kb.hostname = hostname
    kb.os = host_os
    host_data["KnowledgeBase"] = kb
    return host_data

  def AddData(self, parser, *args, **kwargs):
    # Initialize the parser and add parsed data to host_data.
    return [parser().Parse(*args, **kwargs)]

  def AddListener(self, ip, port, family="INET", sock_type="SOCK_STREAM"):
    conn = rdfvalue.NetworkConnection()
    conn.state = "LISTEN"
    conn.family = family
    conn.type = sock_type
    conn.local_address = rdfvalue.NetworkEndpoint(ip=ip, port=port)
    return conn

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

  def GetParsedMultiFile(self, artifact, data, parser):
    stats = []
    files = []
    host_data = self.SetKnowledgeBase()
    kb = host_data["KnowledgeBase"]
    for path, lines in data.items():
      p = rdfvalue.PathSpec(path=path)
      stats.append(rdfvalue.StatEntry(pathspec=p))
      files.append(StringIO.StringIO(lines))
    rdfs = [rdf for rdf in parser.ParseMultiple(stats, files, kb)]
    host_data[artifact] = rdfs
    return host_data

  def GetParsedFile(self, artifact, data, parser):
    host_data = self.SetKnowledgeBase()
    kb = host_data["KnowledgeBase"]
    for path, lines in data.items():
      p = rdfvalue.PathSpec(path=path)
      stat = rdfvalue.StatEntry(pathspec=p)
      file_obj = StringIO.StringIO(lines)
      rdfs = [rdf for rdf in parser.Parse(stat, file_obj, kb)]
      host_data[artifact] = rdfs
      # Return on the first item
      break
    return host_data

  def assertRanChecks(self, check_ids, results):
    """Check that the specified checks were run."""
    residual = set(check_ids) - set(results.keys())
    self.assertFalse(residual)

  def assertResultEqual(self, rslt1, rslt2):
    # Build a map of anomaly explanations to findings.
    if rslt1.check_id != rslt2.check_id:
      self.fail("Check IDs differ: %s vs %s" % (rslt1.check_id, rslt2.check_id))

    # Quick check to see if anomaly counts are the same and they have the same
    # ordering, using explanation as a measure.
    rslt1_anoms = {}
    for a in rslt1.anomaly:
      anoms = rslt1_anoms.setdefault(a.explanation, [])
      anoms.extend(a.finding)
    rslt2_anoms = {}
    for a in rslt2.anomaly:
      anoms = rslt2_anoms.setdefault(a.explanation, [])
      anoms.extend(a.finding)

    self.assertItemsEqual(rslt1_anoms, rslt2_anoms,
                          "Results have different anomaly items.:\n%s\n%s" %
                          (rslt1_anoms.keys(), rslt2_anoms.keys()))

    # Now check that the anomalies are the same.
    for explanation, findings in rslt1_anoms.iteritems():
      self.assertItemsEqual(findings, rslt2_anoms[explanation])

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

  def assertCheckDetectedAnom(self, check_id, results, exp=None, found=None):
    """Assert a check was performed and specific anomalies were found."""
    chk = results.get(check_id)
    self.assertTrue(chk is not None, "check %s did not run" % check_id)
    # Checks return true if there were anomalies.
    self.assertTrue(chk, "check %s did not detect anomalies" % check_id)
    # If exp or results are passed as args, look for anomalies with these
    # values.
    if exp or found:
      expect = rdfvalue.Anomaly(explanation=exp, finding=found,
                                type="ANALYSIS_ANOMALY")
      # Results may contain multiple anomalies. The check will hold true if any
      # one of them matches.
      for rslt in chk.anomaly:
        # If an anomaly matches return True straight away.
        if exp and expect.explanation != rslt.explanation:
          continue
        if found and expect.finding != rslt.finding:
          continue
        return True
      self.fail("No matching anomalies found")

  def assertCheckUndetected(self, check_id, results):
    """Assert a check_id was performed, and resulted in no anomalies."""
    if not isinstance(results, collections.Mapping):
      self.fail("Invalid arg, %s should be dict-like.\n" % type(results))
    if check_id not in results:
      self.fail("Check %s was not performed.\n" % check_id)
    if isinstance(results.get(check_id), rdfvalue.Anomaly):
      self.fail("Check %s unexpectedly produced an anomaly.\n" % check_id)

  def assertChecksUndetected(self, check_ids, results):
    """Assert multiple check_ids were performed & they produced no anomalies."""
    for check_id in check_ids:
      self.assertCheckUndetected(check_id, results)
