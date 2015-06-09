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

  def SetArtifactData(self, anomaly=None, parsed=None, raw=None):
    if anomaly is None:
      anomaly = []
    if parsed is None:
      parsed = []
    if raw is None:
      raw = []
    return {"ANOMALY": anomaly, "PARSER": parsed, "RAW": raw}

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
    host_data[artifact] = self.SetArtifactData(parsed=rdfs)
    return host_data

  def GetParsedFile(self, artifact, data, parser):
    host_data = self.SetKnowledgeBase()
    kb = host_data["KnowledgeBase"]
    for path, lines in data.items():
      p = rdf_paths.PathSpec(path=path)
      stat = rdf_client.StatEntry(pathspec=p)
      file_obj = StringIO.StringIO(lines)
      rdfs = [rdf for rdf in parser.Parse(stat, file_obj, kb)]
      host_data[artifact] = self.SetArtifactData(parsed=rdfs)
      # Return on the first item
      break
    return host_data

  def assertRanChecks(self, check_ids, results):
    """Check that the specified checks were run."""
    self.assertTrue(set(check_ids).issubset(set(results.keys())))

  def assertChecksNotRun(self, check_ids, results):
    """Check that the specified checks were not run."""
    self.assertFalse(set(check_ids).intersection(set(results.keys())))

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

  def _HasExplanation(self, anomalies, exp):
    if exp is None:
      return True
    rslts = {rslt.explanation: rslt for rslt in anomalies}
    rslt = rslts.get(exp)
    # Anomalies evaluate false if there are no finding strings.
    self.assertTrue(rslt is not None,
                    "Didn't get expected explanation string '%s' in '%s'" %
                    (exp, ",".join(rslts)))

  def _GetFindings(self, anomalies, exp):
    """Generate a set of findings from anomalys that match the explanation."""
    result = set()
    for anomaly in anomalies:
      if anomaly.explanation == exp:
        result.update(set(anomaly.finding))
    return result

  def _MatchFindings(self, expected, found):
    """Check that every expected finding is a substring of a found finding."""
    matched_so_far = set()
    for finding_str in expected:
      no_match = True
      for found_str in found:
        if finding_str in found_str:
          matched_so_far.add(found_str)
          no_match = False
          break
      if no_match:
        return False
    # If we got here, all expected's match at least one item.
    # Now check if every item in found was matched at least once.
    # If so, everything is as expected, If not, Badness.
    if not matched_so_far.symmetric_difference(found):
      return True

  def assertCheckDetectedAnom(self, check_id, results, exp=None, findings=None):
    """Assert a check was performed and specific anomalies were found.

    Results may contain multiple anomalies. The check will hold true if any
    one of them matches. As some results can contain multiple anomalies we
    will need to make sure the right anomalies are selected.

    If an explanation is provided, look for anomalies that matches the
    expression string and use those. Otherwise, all anomalies in the
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
    self._HasExplanation(chk.anomaly, exp)
    if findings is None:
      # We are not expecting to match on findings, so skip checking them.
      return True
    findings = set(findings)
    found = self._GetFindings(chk.anomaly, exp)
    if self._MatchFindings(findings, found):
      # Everything matches, and nothing unexpected, so all is good.
      return True
    # If we have made it here, we have the expected explanation but
    # the findings didn't match up.
    others = "\n".join([str(a) for a in chk.anomaly])
    self.fail("Findings don't match for explanation '%s':\nExpected:\n  %s\n"
              "Got:\n  %s\nFrom:\n%s"
              % (exp, ", ".join(findings), ", ".join(found), others))

  def assertCheckUndetected(self, check_id, results):
    """Assert a check_id was performed, and resulted in no anomalies."""
    if not isinstance(results, collections.Mapping):
      self.fail("Invalid arg, %s should be dict-like.\n" % type(results))
    if check_id not in results:
      self.fail("Check %s was not performed.\n" % check_id)
    # A check result will evaluate as True if it contains an anomaly.
    if results.get(check_id):
      self.fail("Check %s unexpectedly produced an anomaly.\nGot: %s\n"
                % (check_id, results.get(check_id).anomaly))

  def assertChecksUndetected(self, check_ids, results):
    """Assert multiple check_ids were performed & they produced no anomalies."""
    for check_id in check_ids:
      self.assertCheckUndetected(check_id, results)
