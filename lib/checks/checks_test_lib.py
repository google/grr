#!/usr/bin/env python
"""A library for check-specific tests."""
import collections
import os
import StringIO


import yaml

from grr.lib import config_lib
from grr.lib import registry
from grr.lib import test_lib
from grr.lib import type_info
from grr.lib.checks import checks
from grr.lib.checks import filters
from grr.lib.checks import hints
from grr.lib.rdfvalues import anomaly as rdf_anomaly
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths


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
    kb = rdf_client.KnowledgeBase()
    kb.hostname = hostname
    kb.os = host_os
    host_data["KnowledgeBase"] = kb
    return host_data

  def AddData(self, parser, *args, **kwargs):
    # Initialize the parser and add parsed data to host_data.
    return [parser().Parse(*args, **kwargs)]

  def AddListener(self, ip, port, family="INET", sock_type="SOCK_STREAM"):
    conn = rdf_client.NetworkConnection()
    conn.state = "LISTEN"
    conn.family = family
    conn.type = sock_type
    conn.local_address = rdf_client.NetworkEndpoint(ip=ip, port=port)
    return conn

  def RunChecks(self, host_data, labels=None):
    return {r.check_id: r for r in checks.CheckHost(host_data, labels=labels)}

  def GetCheckErrors(self, check_spec):
    errors = []
    try:
      check = checks.Check(**check_spec)
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
      p = rdf_paths.PathSpec(path=path)
      stats.append(rdf_client.StatEntry(pathspec=p))
      files.append(StringIO.StringIO(lines))
    rdfs = [rdf for rdf in parser.ParseMultiple(stats, files, kb)]
    host_data[artifact] = rdfs
    return host_data

  def GetParsedFile(self, artifact, data, parser):
    host_data = self.SetKnowledgeBase()
    kb = host_data["KnowledgeBase"]
    for path, lines in data.items():
      p = rdf_paths.PathSpec(path=path)
      stat = rdf_client.StatEntry(pathspec=p)
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
    self.assertIsInstance(rslt, checks.CheckResult)
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

  def assertCheckDetectedAnom(self, check_id, results, exp=None, findings=None):
    """Assert a check was performed and specific anomalies were found.

    Results may contain multiple anomalies. The check will hold true if any
    one of them matches. As some results can contain multiple anomalies we
    will need to make sure the right anomaly is selected.

    If an explanation is provided, look for an anomaly that matches the
    expression string and use that anomaly. Otherwise, all anomalies in the
    check should be used.

    If finding strings are provided, the check tests if the substring is present
    in the findings of the anomalies that are selected for testing. If the
    finding results can have variable ordering, use a substring that will remain
    constant for each finding.

    Args:
      check_id: The check_id as a string.
      results: A dictionary of check results, mapped to check_ids
      exp: An explanation string. This is the "title" of an advisory.
      findings: A list of finding strings that should be present in the findings
        of the selected anomaly.

    Returns:
      True if tests have succeeded and no further processing is required.
    """
    chk = results.get(check_id)
    self.assertTrue(chk is not None, "check %s did not run" % check_id)
    # Checks return true if there were anomalies.
    self.assertTrue(chk, "check %s did not generate anomalies" % check_id)
    # If exp or results are passed as args, look for anomalies with these
    # values.
    if exp is not None or findings is not None:
      # By default, check all the anomalies in the check result.
      anomalies = chk.anomaly
      rslts = {rslt.explanation: rslt for rslt in anomalies}
      if exp:
        rslt = rslts.get(exp)
        # Anomalies evaluate false if there are no finding strings.
        self.assertTrue(rslt is not None,
                        "Didn't get expected explanation string '%s' in '%s'" %
                        (exp, ",".join(rslts)))
        anomalies = [rslt]
      # Stop now if there are no findings to test.
      if not findings:
        return True
      # Now check whether the selected anomaly/anomalies contain the specified
      # finding strings.
      for rslt in anomalies:
        if findings:
          # Should be the same number of findings. If not, this may not be the
          # right result.
          if len(findings) != len(rslt.finding):
            continue
          # Each expected finding string should be in a result finding.
          # We do a substring match to prevent ordering effects within anomaly
          # strings from making the tests flake.
          for want_str in findings:
            found = any([want_str in rslt_str for rslt_str in rslt.finding])
            if not found:
              continue
          # If we get here, the number and content of finding strings matched.
          # The test passes!
          return True
      # If we get to here, none of the result anomalies matched expectations.
      others = "\n".join([str(a) for a in chk.anomaly])
      self.fail("No anomalies matched\nexpression:%s:\nfinding strings %s\n"
                "Got:\n%s" % (exp, ",".join(findings), others))

  def assertCheckUndetected(self, check_id, results):
    """Assert a check_id was performed, and resulted in no anomalies."""
    if not isinstance(results, collections.Mapping):
      self.fail("Invalid arg, %s should be dict-like.\n" % type(results))
    if check_id not in results:
      self.fail("Check %s was not performed.\n" % check_id)
    if isinstance(results.get(check_id), rdf_anomaly.Anomaly):
      self.fail("Check %s unexpectedly produced an anomaly.\n" % check_id)

  def assertChecksUndetected(self, check_ids, results):
    """Assert multiple check_ids were performed & they produced no anomalies."""
    for check_id in check_ids:
      self.assertCheckUndetected(check_id, results)
