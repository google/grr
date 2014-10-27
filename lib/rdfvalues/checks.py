#!/usr/bin/env python
"""Implementation of check types."""
from grr.lib import config_lib
from grr.lib import rdfvalue
from grr.lib.checks import checks
from grr.lib.checks import filters
from grr.lib.checks import hints
from grr.lib.checks import triggers
from grr.lib.rdfvalues import structs
from grr.proto import checks_pb2


def ValidateMultiple(component, hint):
  errors = []
  for item in component:
    try:
      item.Validate()
    except (checks.DefinitionError) as e:
      errors.append(str(e))
  if errors:
    raise checks.DefinitionError("%s:\n  %s" % (hint, "\n  ".join(errors)))


def MatchStrToList(match=None):
  # Set a default match type of ANY, if unset.
  # Allow multiple match types, either as a list or as a string.
  if match is None:
    match = ["ANY"]
  elif isinstance(match, basestring):
    match = match.split()
  return match


class CheckResult(structs.RDFProtoStruct):
  """Results of a single check performed on a host."""
  protobuf = checks_pb2.CheckResult

  def __nonzero__(self):
    return bool(self.anomaly)

  def ExtendAnomalies(self, other):
    """Merge anomalies from another CheckResult."""
    for o in other:
      if o is not None:
        self.anomaly.Extend(list(o.anomaly))


class CheckResults(structs.RDFProtoStruct):
  """All results for a single host."""
  protobuf = checks_pb2.CheckResults

  def __nonzero__(self):
    return bool(self.result)


class Target(structs.RDFProtoStruct):
  """Definitions of hosts to target."""
  protobuf = checks_pb2.Target

  def __init__(self, initializer=None, age=None, **kwargs):
    if isinstance(initializer, dict):
      conf = initializer
      initializer = None
    else:
      conf = kwargs
    super(Target, self).__init__(initializer=initializer, age=age, **conf)

  def __nonzero__(self):
    return any([self.cpe, self.os, self.label])

  def Validate(self):
    if self.cpe:
      # TODO(user): Add CPE library to GRR.
      pass
    if self.os:
      pass
    if self.label:
      pass


class Check(structs.RDFProtoStruct):
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

  def __init__(self, initializer=None, age=None, check_id=None, target=None,
               match=None, method=None, hint=None):
    super(Check, self).__init__(initializer=initializer, age=age)
    self.check_id = check_id
    self.match = MatchStrToList(match)
    self.hint = Hint(hint, reformat=False)
    self.target = target
    if method is None:
      method = []
    self.triggers = triggers.Triggers()
    self.matcher = checks.Matcher(self.match, self.hint)
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
    if isinstance(artifacts, basestring):
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
      raise checks.DefinitionError("Check has missing check_id value")
    cls_name = self.check_id
    if not self.method:
      raise checks.DefinitionError("Check %s has no methods" % cls_name)
    ValidateMultiple(self.method,
                     "Check %s has invalid method definitions" % cls_name)


class Method(structs.RDFProtoStruct):
  """A specific test method using 0 or more filters to process data."""

  protobuf = checks_pb2.Method

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
    self.matcher = checks.Matcher(self.match, self.hint)
    self.resource = [rdfvalue.Dict(**r) for r in resource]
    self.target = Target(**target)
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
      # TODO(user): Need to use the (artifact, rdf_data tuple).
      # Get the data required for the probe.
      rdf_data = host_data.get(p.artifact)
      result = p.Parse(rdf_data)
      if result:
        processed.append(result)
    # Matcher compares the number of probes that triggered with results.
    return self.matcher.Detect(probes, processed)

  def Validate(self):
    """Check the Method is well constructed."""
    ValidateMultiple(self.probe, "Method has invalid probes")
    ValidateMultiple(self.target, "Method has invalid target")
    ValidateMultiple(self.hint, "Method has invalid hint")


class Probe(structs.RDFProtoStruct):
  """The suite of filters applied to host data."""

  protobuf = checks_pb2.Probe

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
    self.matcher = checks.Matcher(conf["match"], hinter)

  def Parse(self, rdf_data):
    """Process rdf data through filters. Test if results match expectations.

    Processing of rdf data is staged by a filter handler, which manages the
    processing of host data. The output of the filters are compared against
    expected results.

    Args:
      rdf_data: An iterable containing 0 or more rdf values.

    Returns:
      An anomaly if data didn't match expectations.

    """
    # TODO(user): Make sure that the filters are called on collected data.
    if self.baseline:
      comparison = self.baseliner.Parse(rdf_data)
    else:
      comparison = rdf_data
    found = self.handler.Parse(comparison)
    results = self.hint.Render(found)
    return self.matcher.Detect(comparison, results)

  def Validate(self):
    """Check the test set is well constructed."""
    ValidateMultiple(self.baseliner, "Probe has invalid baseline filters")
    ValidateMultiple(self.handler, "Probe has invalid filters")
    ValidateMultiple(self.target, "Probe has invalid target")
    ValidateMultiple(self.hint, "Probe has invalid hint")


class Filter(structs.RDFProtoStruct):
  """Generic filter to provide an interface for different types of filter."""

  protobuf = checks_pb2.Filter

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
    Otherwise, a list of parsed data items are returned.

    Args:
      rdf_data: Host data that has already been processed by a Parser into RDF.

    Returns:
      A list of data items that matched the filter rules.
    """
    if not self._filter:
      if isinstance(rdf_data, basestring):
        return [rdf_data]
      return list(rdf_data)
    # TODO(user): filters need to return data as a list if no expression
    # is provided.
    return [x for x in self._filter.Parse(rdf_data, self.expression)]

  def Validate(self):
    """The filter exists, and has valid filter and hint expressions."""
    if self.type not in filters.Filter.classes:
      raise checks.DefinitionError("Undefined filter type %s" % self.type)
    self._filter.Validate(self.expression)
    ValidateMultiple(self.hint, "Filter has invalid hint")


class Hint(structs.RDFProtoStruct):
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
      self.max_results = config_lib.CONFIG.Get("Checks.max_results")
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

  def Explanation(self, state):
    """Creates an anomaly explanation string."""
    if self.problem:
      return "%s: %s" % (state, self.problem)

  def Validate(self):
    """Ensures that required values are set and formatting rules compile."""
    # TODO(user): Default format string.
    if self.problem:
      pass

