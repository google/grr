#!/usr/bin/env python
"""A library for check-specific tests."""
import collections
import os
import StringIO


import yaml

from grr.lib import config_lib
from grr.lib import parsers
from grr.lib import registry
from grr.lib import test_lib
from grr.lib import type_info
from grr.lib.checks import checks
from grr.lib.checks import filters
from grr.lib.checks import hints
from grr.lib.rdfvalues import anomaly as rdf_anomaly
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths
from grr.parsers import linux_service_parser


class HostCheckTest(test_lib.GRRBaseTest):
  """The base class for host check tests."""
  __metaclass__ = registry.MetaclassRegistry

  loaded_checks = None

  @classmethod
  def LoadCheck(cls, cfg_file, *check_ids):
    if HostCheckTest.loaded_checks is None:
      HostCheckTest.loaded_checks = {}

    cfg = os.path.join(config_lib.CONFIG["Test.srcdir"], "grr", "checks",
                       cfg_file)
    if check_ids:
      key = "%s:%s" % (cfg, ",".join(check_ids))
      if key in HostCheckTest.loaded_checks:
        return HostCheckTest.loaded_checks[key]
      loaded = []
      for chk_id in check_ids:
        loaded.append(checks.LoadCheckFromFile(cfg, chk_id))
      HostCheckTest.loaded_checks[key] = loaded
      return loaded
    else:
      key = "%s:*" % cfg_file
      if key in HostCheckTest.loaded_checks:
        return HostCheckTest.loaded_checks[key]
      else:
        result = checks.LoadChecksFromFiles([cfg])
        HostCheckTest.loaded_checks[key] = result
        return result

  def TestDataPath(self, file_name):
    path = os.path.join(config_lib.CONFIG["Test.data_dir"], file_name)
    if not os.path.isfile(path):
      raise test_lib.Error("Missing test data: %s" % file_name)
    return path

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

  def CreateStat(self, path, uid=0, gid=0, mode=0o0100640):
    """Given path, uid, gid and file mode, this returns a StatEntry."""
    pathspec = rdf_paths.PathSpec(path=path, pathtype="OS")
    return rdf_client.StatEntry(pathspec=pathspec, st_uid=uid, st_gid=gid,
                                st_mode=mode)

  def _AddToHostData(self, host_data, artifact, data, parser):
    if type(data) != dict:
      raise test_lib.Error("Data for %s is not of type dictionary." % artifact)

    rdfs = []
    stats = []
    for path, lines in data.items():
      stat = self.CreateStat(path)
      stats.append(stat)
      file_obj = StringIO.StringIO(lines)
      rdfs.extend(list(parser.Parse(stat, file_obj, None)))
    host_data[artifact] = self.SetArtifactData(
        anomaly=[a for a in rdfs if isinstance(a, rdf_anomaly.Anomaly)],
        parsed=[r for r in rdfs if not isinstance(r, rdf_anomaly.Anomaly)],
        raw=stats)
    return host_data

  def GenResults(self, artifact_list, sources_list, parser_list=None):
    """Given a list of artifacts, sources and parsers, will RunChecks on them.

    Sample: (["Artifact1", "Artifact2"], [artifact1_data, artifact2_data],
             [config_file.artifact1_Parser(), config_file.artifact2_Parser()]

    artifact1_Parser().parse will run on artifact1_data & parsed results, along
    with raw and anomalies will be inserted into the host_data["Artifact1"].

    artifact2_Parser().parse will run on artifact2_data & parsed results, along
    with raw and anomalies will be inserted into the host_data["Artifact2"].

    Once artifacts added to host_data, loaded checks will be run against it.

    Args:
      artifact_list: list of artifacts to add to host_data for running checks
      sources_list: list of dictionaries containing file names and file data.
        If parser_list is empty then sources_list must contain a list of lists
        containing StatEntry or lists of other raw artifact data.
      parser_list: list of parsers to apply to file data from sources_list.
        This can be empty if no parser is to be applied.

    Returns:
      CheckResult containing any findings in sources_list against loaded checks.
    """
    if parser_list is None:
      parser_list = [None] * len(artifact_list)

    # make sure all vars are lists
    if any(type(lst) != list for lst in [artifact_list, sources_list,
                                         parser_list]):
      raise test_lib.Error("All inputs are not lists.")
    # make sure all lists are of equal length
    if any(len(lst) != len(artifact_list) for lst in [sources_list,
                                                      parser_list]):
      raise test_lib.Error("All lists are not of the same length.")

    host_data = self.SetKnowledgeBase()
    for artifact, sources, parser in zip(artifact_list, sources_list,
                                         parser_list):
      if parser is None:
        host_data[artifact] = self.SetArtifactData(raw=sources)
      else:
        host_data = self._AddToHostData(host_data, artifact, sources, parser)
    return self.RunChecks(host_data)

  def GenProcessData(self, processes):
    """Create some process-based host data."""
    host_data = self.SetKnowledgeBase()
    data = []
    for (name, pid, cmdline) in processes:
      data.append(rdf_client.Process(name=name, pid=pid, cmdline=cmdline))
    host_data["ListProcessesGrr"] = self.SetArtifactData(parsed=data)
    return host_data

  def _GenFileData(self, paths, data, stats=None, files=None, st_mode=33188):
    """Generate a tuple of list of stats and list of file contents."""
    if stats is None:
      stats = []
    if files is None:
      files = []
    for path in paths:
      p = rdf_paths.PathSpec(path=path, pathtype="OS")
      stats.append(rdf_client.StatEntry(pathspec=p, st_mode=st_mode))
    for val in data:
      files.append(StringIO.StringIO(val))
    return stats, files

  def GenFileData(self, artifact, data, parser=parsers.FileParser,
                  st_mode=33188):
    """Create some generic file-based host data."""
    host_data = self.SetKnowledgeBase()
    stats = []
    files = []
    for path in data:
      stats, files = self._GenFileData([path], [data[path]], stats=stats,
                                       files=files, st_mode=st_mode)
    rdfs = parser().ParseMultiple(stats, files, host_data["KnowledgeBase"])
    if rdfs is None:
      rdfs = []
    else:
      rdfs = list(rdfs)
    host_data[artifact] = self.SetArtifactData(parsed=rdfs, raw=stats)
    return host_data

  def GenSysVInitData(self, links):
    """Create some Sys V init host data."""
    return self.GenFileData("LinuxServices",
                            {x: "" for x in links},
                            linux_service_parser.LinuxSysVInitParser,
                            st_mode=41471)

  # The assert methods

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
