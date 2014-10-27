#!/usr/bin/env python
"""Registry for filters and abstract classes for basic filter functionality."""
import collections
import itertools

import yaml

import logging

from grr.lib import rdfvalue
from grr.lib.checks import triggers as triggers_lib


class Error(Exception):
  """Base error class."""


class DefinitionError(Error):
  """A check was defined badly."""


class ProcessingError(Error):
  """A check generated bad results."""


class Matcher(object):
  """Performs comparisons between baseline and result data."""

  def __init__(self, matches, hint):
    method_map = {"NONE": self.GotNone,
                  "ONE": self.GotSingle,
                  "SOME": self.GotMultiple,
                  "ANY": self.GotAny,
                  "ALL": self.GotAll}
    try:
      self.detectors = [method_map.get(str(match)) for match in matches]
    except KeyError:
      raise DefinitionError("Match uses undefined check condition: %s" % match)
    self.hint = hint

  def Detect(self, baseline, host_data):
    """Run host_data through detectors and return them if a detector triggers.

    Args:
      baseline: The base set of rdf values used to evaluate whether an issue
        exists.
      host_data: The rdf values passed back by the filters.

    Returns:
      A CheckResult message containing anomalies if any detectors identified an
      issue, None otherwise.
    """
    result = rdfvalue.CheckResult()
    for detector in self.detectors:
      for finding in detector(baseline, host_data):
        if finding:
          result.ExtendAnomalies(finding)
    if result:
      return result

  def Issue(self, state, results):
    """Collect anomalous findings into a CheckResult.

    Comparisons with anomalous conditions collect anomalies into a single
    CheckResult message. The contents of the result varies depending on whether
    the method making the comparison is a Check, Method or Probe.
    - Probes evaluate raw host data and generate Anomalies. These are condensed
      into a new CheckResult.
    - Checks and Methods evaluate the results of probes (i.e. CheckResults). If
      there are multiple probe results, all probe anomalies are aggregated into
      a single new CheckResult for the Check or Method.

    Args:
      state: A text description of what combination of results were anomalous
        (e.g. some condition was missing or present.)
      results: Anomalies or CheckResult messages.

    Returns:
      A CheckResult message.
    """
    result = rdfvalue.CheckResult()
    anomaly = rdfvalue.Anomaly(type="ANALYSIS_ANOMALY",
                               explanation=self.hint.Explanation(state))
    # If there are CheckResults we're aggregating methods or probes.
    # Merge all current results into one CheckResult.
    # Otherwise, the results are raw host data.
    # Generate a new CheckResult and add the specific findings.
    if results and all(isinstance(r, rdfvalue.CheckResult) for r in results):
      result.ExtendAnomalies(results)
    else:
      anomaly.finding = self.hint.Render(results)
      result.anomaly = anomaly
    return result

  def GotNone(self, _, results):
    """Anomaly for no results, an empty list otherwise."""
    if not results:
      return self.Issue("Missing attribute", [])
    return []

  def GotSingle(self, _, results):
    """Anomaly for exactly one result, an empty list otherwise."""
    if len(results) == 1:
      return self.Issue("Found one", results)
    return []

  def GotMultiple(self, _, results):
    """Anomaly for >1 result, an empty list otherwise."""
    if len(results) > 1:
      return self.Issue("Found multiple", results)
    return []

  def GotAny(self, _, results):
    """Anomaly for 1+ results, an empty list otherwise."""
    if results:
      return self.Issue("Found", results)
    return []

  def GotAll(self, baseline, results):
    """Anomaly if baseline vs result counts differ, an empty list otherwise."""
    num_base = len(baseline)
    num_rslt = len(results)
    if num_rslt > num_base:
      raise ProcessingError("Filter generated more results than base data: "
                            "%s > %s" % (num_rslt, num_base))
    if num_rslt == num_base and num_base > 0:
      return self.Issue("Found all", results)
    return []


class CheckRegistry(object):
  """A class to register the mapping between checks and host data.

  This is used to trigger all relevant checks when we collect the data.
  The method registry maps the combination of platform, environment and host
  data required by a given method.
  """
  checks = {}

  triggers = triggers_lib.Triggers()

  @classmethod
  def Clear(cls):
    """Remove all checks and triggers from the registry."""
    cls.checks = {}
    cls.triggers = triggers_lib.Triggers()

  @classmethod
  def RegisterCheck(cls, check, source="unknown", overwrite_if_exists=False):
    """Adds a check to the registry, refresh the trigger to check map."""
    if not overwrite_if_exists and check.check_id in cls.checks:
      raise DefinitionError("Check named %s already exists and "
                            "overwrite_if_exists is set to False." %
                            check.check_id)
    check.loaded_from = source
    cls.checks[check.check_id] = check
    cls.triggers.Update(check.triggers, check)

  @staticmethod
  def _AsList(arg):
    """Encapsulates an argument in a list, if it's not already iterable."""
    if isinstance(arg, basestring) or not isinstance(arg, collections.Iterable):
      return [arg]
    else:
      return list(arg)

  @classmethod
  def Conditions(cls, artifact=None, os=None, cpe=None, labels=None):
    """Provide a series of condition tuples.

    A Target can specify multiple artifact, os, cpe or label entries. These are
    expanded to all distinct tuples. When an entry is undefined or None, it is
    treated as a single definition of None, meaning that the condition does not
    apply.

    Args:
      artifact: Names of artifacts that should trigger an action.
      os: Names of OS' that should trigger an action.
      cpe: CPE strings that should trigger an action.
      labels: Host labels that should trigger an action.

    Yields:
      a permuted series of (artifact, os, cpe, label) tuples.
    """
    artifact = cls._AsList(artifact)
    os = cls._AsList(os)
    cpe = cls._AsList(cpe)
    labels = cls._AsList(labels)
    for condition in itertools.product(artifact, os, cpe, labels):
      yield condition

  @classmethod
  def FindChecks(cls, artifact=None, os=None, cpe=None, labels=None):
    """Takes targeting info, identifies relevant checks.

    FindChecks will return results when a host has the conditions necessary for
    a check to occur. Conditions with partial results are not returned. For
    example, FindChecks will not return checks that if a check targets
    os=["Linux"], labels=["foo"] and a host only has the os=["Linux"] attribute.

    Args:
      artifact: 0+ artifact names.
      os: 0+ OS names.
      cpe: 0+ CPE identifiers.
      labels: 0+ GRR labels.

    Returns:
      the check_ids that apply.
    """
    check_ids = set()
    conditions = list(cls.Conditions(artifact, os, cpe, labels))
    for chk_id, chk in cls.checks.iteritems():
      # A quick test to determine whether to dive into the checks.
      if chk.UsesArtifact(artifact):
        for condition in conditions:
          if chk.triggers.Match(*condition):
            check_ids.add(chk_id)
            break  # No need to keep checking other conditions.
    return check_ids

  @classmethod
  def SelectArtifacts(cls, os=None, cpe=None, labels=None):
    """Takes targeting info, identifies artifacts to fetch.

    Args:
      os: 0+ OS names.
      cpe: 0+ CPE identifiers.
      labels: 0+ GRR labels.

    Returns:
      the artifacts that should be collected.
    """
    results = set()
    for condition in cls.Conditions(None, os, cpe, labels):
      trigger = condition[1:]
      for chk in cls.checks.values():
        results.update(chk.triggers.Artifacts(*trigger))
    return results

  @classmethod
  def Process(cls, host_data, os=None, cpe=None, labels=None):
    """Runs checks over all host data.

    Args:
      host_data: The data collected from a host, mapped to artifact name.
      os: 0+ OS names.
      cpe: 0+ CPE identifiers.
      labels: 0+ GRR labels.

    Yields:
      A CheckResult message for each check that was performed.
    """
    # All the conditions that apply to this host.
    artifacts = host_data.keys()
    check_ids = cls.FindChecks(artifacts, os, cpe, labels)
    conditions = list(cls.Conditions(artifacts, os, cpe, labels))
    for check_id in check_ids:
      chk = cls.checks[check_id]
      yield chk.Parse(conditions, host_data)


def CheckHost(host_data, os=None, cpe=None, labels=None):
  """Perform all checks on a host using acquired artifacts.

  Checks are selected based on the artifacts available and the host attributes
  (e.g. os/cpe/labels) provided as either parameters, or in the knowledgebase
  artifact.

  A KnowledgeBase artifact should be provided that contains, at a minimum:
  - OS
  - Hostname or IP
  Other knowldegebase attributes may be required for specific checks.

  CPE is currently unused, pending addition of a CPE module in the GRR client.

  Labels are arbitrary string labels attached to a client.

  Args:
    host_data: A dictionary with artifact names as keys, and rdf data as values.
    os: An OS name (optional).
    cpe: A CPE string (optional).
    labels: An iterable of labels (optional).

  Returns:
    A CheckResults object that contains results for all checks that were
      performed on the host.
  """
  # Get knowledgebase, os from hostdata
  kb = host_data.get("KnowledgeBase")
  if os is None:
    os = kb.os
  if cpe is None:
    # TODO(user): Get CPE (requires new artifact/parser)
    pass
  if labels is None:
    # TODO(user): Get labels (see grr/lib/export.py for acquisition
    # from client)
    pass
  return CheckRegistry.Process(host_data, os=os, cpe=cpe, labels=labels)


def LoadConfigsFromFile(file_path):
  """Loads check definitions from a file."""
  with open(file_path) as data:
    return {d["check_id"]: d for d in yaml.safe_load_all(data)}


def LoadChecksFromFiles(file_paths, overwrite_if_exists=True):
  for file_path in file_paths:
    configs = LoadConfigsFromFile(file_paths)
    for conf in configs.values():
      check = rdfvalue.Check(**conf)
      check.Validate()
      CheckRegistry.RegisterCheck(check, source="file:%s" % file_path,
                                  overwrite_if_exists=overwrite_if_exists)
      logging.debug("Loaded check %s from %s", check.check_id, file_path)

