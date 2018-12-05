#!/usr/bin/env python
"""Registry for filters and abstract classes for basic filter functionality."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import glob
import itertools
import logging
import os


from future.utils import iteritems
from future.utils import iterkeys
from future.utils import itervalues
from future.utils import string_types
import yaml

from grr_response_core import config
from grr_response_core.lib import registry
from grr_response_core.lib.rdfvalues import anomaly as rdf_anomaly
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import anomaly_pb2
from grr_response_proto import checks_pb2
from grr_response_server.check_lib import filters
from grr_response_server.check_lib import hints
from grr_response_server.check_lib import triggers


class Error(Exception):
  """Base error class."""


class DefinitionError(Error):
  """A check was defined badly."""


class ProcessingError(Error):
  """A check generated bad results."""


def Validate(item, hint):
  try:
    item.Validate()
  except DefinitionError as e:
    raise DefinitionError("%s:\n  %s" % (hint, str(e)))


def ValidateMultiple(component, hint):
  errors = []
  for item in component:
    try:
      item.Validate()
    except DefinitionError as e:
      errors.append(str(e))
  if errors:
    raise DefinitionError("%s:\n  %s" % (hint, "\n  ".join(errors)))


def MatchStrToList(match=None):
  # Set a default match type of ANY, if unset.
  # Allow multiple match types, either as a list or as a string.
  if match is None:
    match = ["ANY"]
  elif isinstance(match, string_types):
    match = match.split()
  return match


class Hint(rdf_structs.RDFProtoStruct):
  """Human-formatted descriptions of problems, fixes and findings."""

  protobuf = checks_pb2.Hint

  def __init__(self, initializer=None, age=None, reformat=True, **kwargs):
    if isinstance(initializer, dict):
      conf = initializer
      initializer = None
    else:
      conf = kwargs
    super(Hint, self).__init__(initializer=initializer, age=age, **conf)
    if not self.max_results:
      self.max_results = config.CONFIG.Get("Checks.max_results")
    if reformat:
      self.hinter = hints.Hinter(self.format)
    else:
      self.hinter = hints.Hinter()

  def Render(self, rdf_data):
    """Processes data according to formatting rules."""
    report_data = rdf_data[:self.max_results]
    results = [self.hinter.Render(rdf) for rdf in report_data]
    extra = len(rdf_data) - len(report_data)
    if extra > 0:
      results.append("...plus another %d issues." % extra)
    return results

  def Problem(self, state):
    """Creates an anomaly symptom/problem string."""
    if self.problem:
      return "%s: %s" % (state, self.problem.strip())

  def Fix(self):
    """Creates an anomaly explanation/fix string."""
    if self.fix:
      return self.fix.strip()

  def Validate(self):
    """Ensures that required values are set and formatting rules compile."""
    # TODO(user): Default format string.
    if self.problem:
      pass


class Filter(rdf_structs.RDFProtoStruct):
  """Generic filter to provide an interface for different types of filter."""

  protobuf = checks_pb2.Filter
  rdf_deps = [
      Hint,
  ]

  def __init__(self, initializer=None, age=None, **kwargs):
    # FIXME(sebastianw): Probe seems to pass in the configuration for filters
    # as a dict in initializer, rather than as kwargs.
    if isinstance(initializer, dict):
      conf = initializer
      initializer = None
    else:
      conf = kwargs
    super(Filter, self).__init__(initializer=initializer, age=age, **conf)
    filter_name = self.type or "Filter"
    self._filter = filters.Filter.GetFilter(filter_name)

  def Parse(self, rdf_data):
    """Process rdf data through the filter.

    Filters sift data according to filter rules. Data that passes the filter
    rule is kept, other data is dropped.

    If no filter method is provided, the data is returned as a list.
    Otherwise, a items that meet filter conditions are returned in a list.

    Args:
      rdf_data: Host data that has already been processed by a Parser into RDF.

    Returns:
      A list containing data items that matched the filter rules.
    """
    if self._filter:
      return list(self._filter.Parse(rdf_data, self.expression))
    return rdf_data

  def Validate(self):
    """The filter exists, and has valid filter and hint expressions."""
    if self.type not in filters.Filter.classes:
      raise DefinitionError("Undefined filter type %s" % self.type)
    self._filter.Validate(self.expression)
    Validate(self.hint, "Filter has invalid hint")


class Probe(rdf_structs.RDFProtoStruct):
  """The suite of filters applied to host data."""

  protobuf = checks_pb2.Probe
  rdf_deps = [
      Filter,
      Hint,
      triggers.Target,
  ]

  def __init__(self, initializer=None, age=None, **kwargs):
    if isinstance(initializer, dict):
      conf = initializer
      initializer = None
    else:
      conf = kwargs
    conf["match"] = MatchStrToList(kwargs.get("match"))
    super(Probe, self).__init__(initializer=initializer, age=age, **conf)
    if self.filters:
      handler = filters.GetHandler(mode=self.mode)
    else:
      handler = filters.GetHandler()
    self.baseliner = handler(artifact=self.artifact, filters=self.baseline)
    self.handler = handler(artifact=self.artifact, filters=self.filters)
    hinter = Hint(conf.get("hint", {}), reformat=False)
    self.matcher = Matcher(conf["match"], hinter)

  def Parse(self, rdf_data):
    """Process rdf data through filters. Test if results match expectations.

    Processing of rdf data is staged by a filter handler, which manages the
    processing of host data. The output of the filters are compared against
    expected results.

    Args:
      rdf_data: An list containing 0 or more rdf values.

    Returns:
      An anomaly if data didn't match expectations.

    Raises:
      ProcessingError: If rdf_data is not a handled type.

    """
    if not isinstance(rdf_data, (list, set)):
      raise ProcessingError("Bad host data format: %s" % type(rdf_data))
    if self.baseline:
      comparison = self.baseliner.Parse(rdf_data)
    else:
      comparison = rdf_data
    found = self.handler.Parse(comparison)
    results = self.hint.Render(found)
    return self.matcher.Detect(comparison, results)

  def Validate(self):
    """Check the test set is well constructed."""
    Validate(self.target, "Probe has invalid target")
    self.baseliner.Validate()
    self.handler.Validate()
    self.hint.Validate()


class Method(rdf_structs.RDFProtoStruct):
  """A specific test method using 0 or more filters to process data."""

  protobuf = checks_pb2.Method
  rdf_deps = [
      rdf_protodict.Dict,
      Hint,
      Probe,
      triggers.Target,
  ]

  def __init__(self, initializer=None, age=None, **kwargs):
    if isinstance(initializer, dict):
      conf = initializer
      initializer = None
    else:
      conf = kwargs
    super(Method, self).__init__(initializer=initializer, age=age)
    probe = conf.get("probe", {})
    resource = conf.get("resource", {})
    hint = conf.get("hint", {})
    target = conf.get("target", {})
    if hint:
      # Add the hint to children.
      for cfg in probe:
        cfg["hint"] = hints.Overlay(child=cfg.get("hint", {}), parent=hint)
    self.probe = [Probe(**cfg) for cfg in probe]
    self.hint = Hint(hint, reformat=False)
    self.match = MatchStrToList(kwargs.get("match"))
    self.matcher = Matcher(self.match, self.hint)
    self.resource = [rdf_protodict.Dict(**r) for r in resource]
    self.target = triggers.Target(**target)
    self.triggers = triggers.Triggers()
    for p in self.probe:
      # If the probe has a target, use it. Otherwise, use the method's target.
      target = p.target or self.target
      self.triggers.Add(p.artifact, target, p)

  def Parse(self, conditions, host_data):
    """Runs probes that evaluate whether collected data has an issue.

    Args:
      conditions: The trigger conditions.
      host_data: A map of artifacts and rdf data.

    Returns:
      Anomalies if an issue exists.
    """
    processed = []
    probes = self.triggers.Calls(conditions)
    for p in probes:
      # Get the data required for the probe. A probe can use a result_context
      # (e.g. Parsers, Anomalies, Raw), to identify the data that is needed
      # from the artifact collection results.
      artifact_data = host_data.get(p.artifact)
      if not p.result_context:
        rdf_data = artifact_data["PARSER"]
      else:
        rdf_data = artifact_data.get(str(p.result_context))
      try:
        result = p.Parse(rdf_data)
      except ProcessingError as e:
        raise ProcessingError("Bad artifact %s: %s" % (p.artifact, e))
      if result:
        processed.append(result)
    # Matcher compares the number of probes that triggered with results.
    return self.matcher.Detect(probes, processed)

  def Validate(self):
    """Check the Method is well constructed."""
    ValidateMultiple(self.probe, "Method has invalid probes")
    Validate(self.target, "Method has invalid target")
    Validate(self.hint, "Method has invalid hint")


class CheckResult(rdf_structs.RDFProtoStruct):
  """Results of a single check performed on a host."""
  protobuf = checks_pb2.CheckResult
  rdf_deps = [
      rdf_anomaly.Anomaly,
  ]

  def __nonzero__(self):
    return bool(self.anomaly)

  def ExtendAnomalies(self, other):
    """Merge anomalies from another CheckResult."""
    for o in other:
      if o is not None:
        self.anomaly.Extend(list(o.anomaly))


class CheckResults(rdf_structs.RDFProtoStruct):
  """All results for a single host."""
  protobuf = checks_pb2.CheckResults
  rdf_deps = [
      CheckResult,
      rdf_client.KnowledgeBase,
  ]

  def __nonzero__(self):
    return bool(self.result)


class Check(rdf_structs.RDFProtoStruct):
  """A definition of a problem, and ways to detect it.

  Checks contain an identifier of a problem (check_id) that is a reference to an
  externally or internally defined vulnerability.

  Checks use one or more Methods to determine if an issue exists. Methods define
  data collection and processing, and return an Anomaly if the conditions tested
  by the method weren't met.

  Checks can define a default platform, OS or environment to target. This
  is passed to each Method, but can be overridden by more specific definitions.
  """
  protobuf = checks_pb2.Check
  rdf_deps = [
      Hint,
      Method,
      triggers.Target,
  ]

  def __init__(self,
               initializer=None,
               age=None,
               check_id=None,
               target=None,
               match=None,
               method=None,
               hint=None):
    super(Check, self).__init__(initializer=initializer, age=age)
    self.check_id = check_id
    self.match = MatchStrToList(match)
    self.hint = Hint(hint, reformat=False)
    self.target = target
    if method is None:
      method = []
    self.triggers = triggers.Triggers()
    self.matcher = Matcher(self.match, self.hint)
    for cfg in method:
      # Use the value of "target" as a default for each method, if defined.
      # Targets defined in methods or probes override this default value.
      if hint:
        cfg["hint"] = hints.Overlay(child=cfg.get("hint", {}), parent=hint)
      if target:
        cfg.setdefault("target", target)
      # Create the method and add its triggers to the check.
      m = Method(**cfg)
      self.method.append(m)
      self.triggers.Update(m.triggers, callback=m)
    self.artifacts = set([t.artifact for t in self.triggers.conditions])

  def SelectChecks(self, conditions):
    """Identifies which check methods to use based on host attributes.

    Queries the trigger map for any check methods that apply to a combination of
    OS, CPE and/or label.

    Args:
      conditions: A list of Condition objects.

    Returns:
      A list of method callbacks that should perform checks.
    """
    return self.triggers.Calls(conditions)

  def UsesArtifact(self, artifacts):
    """Determines if the check uses the specified artifact.

    Args:
      artifacts: Either a single artifact name, or a list of artifact names

    Returns:
      True if the check uses a specific artifact.
    """
    # If artifact is a single string, see if it is in the list of artifacts
    # as-is. Otherwise, test whether any of the artifacts passed in to this
    # function exist in the list of artifacts.
    if isinstance(artifacts, string_types):
      return artifacts in self.artifacts
    else:
      return any(True for artifact in artifacts if artifact in self.artifacts)

  def Parse(self, conditions, host_data):
    """Runs methods that evaluate whether collected host_data has an issue.

    Args:
      conditions: A list of conditions to determine which Methods to trigger.
      host_data: A map of artifacts and rdf data.

    Returns:
      A CheckResult populated with Anomalies if an issue exists.
    """
    result = CheckResult(check_id=self.check_id)
    methods = self.SelectChecks(conditions)
    result.ExtendAnomalies([m.Parse(conditions, host_data) for m in methods])
    return result

  def Validate(self):
    """Check the method is well constructed."""
    if not self.check_id:
      raise DefinitionError("Check has missing check_id value")
    cls_name = self.check_id
    if not self.method:
      raise DefinitionError("Check %s has no methods" % cls_name)
    ValidateMultiple(self.method,
                     "Check %s has invalid method definitions" % cls_name)


class Matcher(object):
  """Performs comparisons between baseline and result data."""

  def __init__(self, matches, hint):
    method_map = {
        "NONE": self.GotNone,
        "ONE": self.GotSingle,
        "SOME": self.GotMultiple,
        "ANY": self.GotAny,
        "ALL": self.GotAll
    }
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
    result = CheckResult()
    for detector in self.detectors:
      finding = detector(baseline, host_data)
      if finding:
        result.ExtendAnomalies([finding])
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
    result = CheckResult()
    # If there are CheckResults we're aggregating methods or probes.
    # Merge all current results into one CheckResult.
    # Otherwise, the results are raw host data.
    # Generate a new CheckResult and add the specific findings.
    if results and all(isinstance(r, CheckResult) for r in results):
      result.ExtendAnomalies(results)
    else:
      result.anomaly = [
          rdf_anomaly.Anomaly(
              type=anomaly_pb2.Anomaly.AnomalyType.Name(
                  anomaly_pb2.Anomaly.ANALYSIS_ANOMALY),
              symptom=self.hint.Problem(state),
              finding=self.hint.Render(results),
              explanation=self.hint.Fix())
      ]
    return result

  def GotNone(self, _, results):
    """Anomaly for no results, an empty list otherwise."""
    if not results:
      return self.Issue("Missing attribute", ["Expected state was not found"])
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

  triggers = triggers.Triggers()

  @classmethod
  def Clear(cls):
    """Remove all checks and triggers from the registry."""
    cls.checks = {}
    cls.triggers = triggers.Triggers()

  @classmethod
  def RegisterCheck(cls, check, source="unknown", overwrite_if_exists=False):
    """Adds a check to the registry, refresh the trigger to check map."""
    if not overwrite_if_exists and check.check_id in cls.checks:
      raise DefinitionError(
          "Check named %s already exists and "
          "overwrite_if_exists is set to False." % check.check_id)
    check.loaded_from = source
    cls.checks[check.check_id] = check
    cls.triggers.Update(check.triggers, check)

  @staticmethod
  def _AsList(arg):
    """Encapsulates an argument in a list, if it's not already iterable."""
    if (isinstance(arg, string_types) or
        not isinstance(arg, collections.Iterable)):
      return [arg]
    else:
      return list(arg)

  @classmethod
  def Conditions(cls, artifact=None, os_name=None, cpe=None, labels=None):
    """Provide a series of condition tuples.

    A Target can specify multiple artifact, os_name, cpe or label entries. These
    are expanded to all distinct tuples. When an entry is undefined or None, it
    is treated as a single definition of None, meaning that the condition does
    not apply.

    Args:
      artifact: Names of artifacts that should trigger an action.
      os_name: Names of OS' that should trigger an action.
      cpe: CPE strings that should trigger an action.
      labels: Host labels that should trigger an action.

    Yields:
      a permuted series of (artifact, os_name, cpe, label) tuples.
    """
    artifact = cls._AsList(artifact)
    os_name = cls._AsList(os_name)
    cpe = cls._AsList(cpe)
    labels = cls._AsList(labels)
    for condition in itertools.product(artifact, os_name, cpe, labels):
      yield condition

  @classmethod
  def FindChecks(cls,
                 artifact=None,
                 os_name=None,
                 cpe=None,
                 labels=None,
                 restrict_checks=None):
    """Takes targeting info, identifies relevant checks.

    FindChecks will return results when a host has the conditions necessary for
    a check to occur. Conditions with partial results are not returned. For
    example, FindChecks will not return checks that if a check targets
    os_name=["Linux"], labels=["foo"] and a host only has the os_name=["Linux"]
    attribute.

    Args:
      artifact: 0+ artifact names.
      os_name: 0+ OS names.
      cpe: 0+ CPE identifiers.
      labels: 0+ GRR labels.
      restrict_checks: A list of check ids to restrict check processing to.

    Returns:
      the check_ids that apply.
    """
    check_ids = set()
    conditions = list(cls.Conditions(artifact, os_name, cpe, labels))
    for chk_id, chk in iteritems(cls.checks):
      if restrict_checks and chk_id not in restrict_checks:
        continue
      for condition in conditions:
        if chk.triggers.Match(*condition):
          check_ids.add(chk_id)
          break  # No need to keep checking other conditions.
    return check_ids

  @classmethod
  def SelectArtifacts(cls,
                      os_name=None,
                      cpe=None,
                      labels=None,
                      restrict_checks=None):
    """Takes targeting info, identifies artifacts to fetch.

    Args:
      os_name: 0+ OS names.
      cpe: 0+ CPE identifiers.
      labels: 0+ GRR labels.
      restrict_checks: A list of check ids whose artifacts should be fetched.

    Returns:
      the artifacts that should be collected.
    """
    results = set()
    for condition in cls.Conditions(None, os_name, cpe, labels):
      trigger = condition[1:]
      for chk in itervalues(cls.checks):
        if restrict_checks and chk.check_id not in restrict_checks:
          continue
        results.update(chk.triggers.Artifacts(*trigger))
    return results

  @classmethod
  def Process(cls,
              host_data,
              os_name=None,
              cpe=None,
              labels=None,
              exclude_checks=None,
              restrict_checks=None):
    """Runs checks over all host data.

    Args:
      host_data: The data collected from a host, mapped to artifact name.
      os_name: 0+ OS names.
      cpe: 0+ CPE identifiers.
      labels: 0+ GRR labels.
      exclude_checks: A list of check ids not to run. A check id in this list
                      will not get run even if included in restrict_checks.
      restrict_checks: A list of check ids that may be run, if appropriate.

    Yields:
      A CheckResult message for each check that was performed.
    """
    # All the conditions that apply to this host.
    artifacts = list(iterkeys(host_data))
    check_ids = cls.FindChecks(artifacts, os_name, cpe, labels)
    conditions = list(cls.Conditions(artifacts, os_name, cpe, labels))
    for check_id in check_ids:
      # skip if check in list of excluded checks
      if exclude_checks and check_id in exclude_checks:
        continue
      if restrict_checks and check_id not in restrict_checks:
        continue
      try:
        chk = cls.checks[check_id]
        yield chk.Parse(conditions, host_data)
      except ProcessingError as e:
        logging.warn("Check ID %s raised: %s", check_id, e)


def CheckHost(host_data,
              os_name=None,
              cpe=None,
              labels=None,
              exclude_checks=None,
              restrict_checks=None):
  """Perform all checks on a host using acquired artifacts.

  Checks are selected based on the artifacts available and the host attributes
  (e.g. os_name/cpe/labels) provided as either parameters, or in the
  knowledgebase artifact.

  A KnowledgeBase artifact should be provided that contains, at a minimum:
  - OS
  - Hostname or IP
  Other knowldegebase attributes may be required for specific checks.

  CPE is currently unused, pending addition of a CPE module in the GRR client.

  Labels are arbitrary string labels attached to a client.

  Args:
    host_data: A dictionary with artifact names as keys, and rdf data as values.
    os_name: An OS name (optional).
    cpe: A CPE string (optional).
    labels: An iterable of labels (optional).
    exclude_checks: A list of check ids not to run. A check id in this list
                    will not get run even if included in restrict_checks.
    restrict_checks: A list of check ids that may be run, if appropriate.

  Returns:
    A CheckResults object that contains results for all checks that were
      performed on the host.
  """
  # Get knowledgebase, os_name from hostdata
  kb = host_data.get("KnowledgeBase")
  if os_name is None:
    os_name = kb.os
  if cpe is None:
    # TODO(user): Get CPE (requires new artifact/parser)
    pass
  if labels is None:
    # TODO(user): Get labels (see grr/lib/export.py for acquisition
    # from client)
    pass
  return CheckRegistry.Process(
      host_data,
      os_name=os_name,
      cpe=cpe,
      labels=labels,
      restrict_checks=restrict_checks,
      exclude_checks=exclude_checks)


def LoadConfigsFromFile(file_path):
  """Loads check definitions from a file."""
  with open(file_path) as data:
    return {d["check_id"]: d for d in yaml.safe_load_all(data)}


def LoadCheckFromFile(file_path, check_id, overwrite_if_exists=True):
  """Load a single check from a file."""
  configs = LoadConfigsFromFile(file_path)
  conf = configs.get(check_id)
  check = Check(**conf)
  check.Validate()
  CheckRegistry.RegisterCheck(
      check,
      source="file:%s" % file_path,
      overwrite_if_exists=overwrite_if_exists)
  logging.debug("Loaded check %s from %s", check.check_id, file_path)
  return check


def LoadChecksFromFiles(file_paths, overwrite_if_exists=True):
  """Load the checks defined in the specified files."""
  loaded = []
  for file_path in file_paths:
    configs = LoadConfigsFromFile(file_path)
    for conf in itervalues(configs):
      check = Check(**conf)
      # Validate will raise if the check doesn't load.
      check.Validate()
      loaded.append(check)
      CheckRegistry.RegisterCheck(
          check,
          source="file:%s" % file_path,
          overwrite_if_exists=overwrite_if_exists)
      logging.debug("Loaded check %s from %s", check.check_id, file_path)
  return loaded


def LoadChecksFromDirs(dir_paths, overwrite_if_exists=True):
  """Load checks from all yaml files in the specified directories."""
  loaded = []
  for dir_path in dir_paths:
    cfg_files = glob.glob(os.path.join(dir_path, "*.yaml"))
    loaded.extend(LoadChecksFromFiles(cfg_files, overwrite_if_exists))
  return loaded


class CheckLoader(registry.InitHook):
  """Loads checks from the filesystem."""

  # TODO(user): Add check loading from datastore.

  def RunOnce(self):
    LoadChecksFromDirs(config.CONFIG["Checks.config_dir"])
    LoadChecksFromFiles(config.CONFIG["Checks.config_files"])
    logging.debug("Loaded checks: %s", ",".join(sorted(CheckRegistry.checks)))
