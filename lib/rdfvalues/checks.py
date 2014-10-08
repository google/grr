#!/usr/bin/env python
"""Implementation of check types."""
from grr.lib.checks import checks
from grr.lib.checks import filters
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
    self.hint = hint
    self.target = target
    if method is None:
      method = []
    self.triggers = triggers.Triggers()
    self.matcher = checks.Matcher([str(x) for x in self.match])
    for method_def in method:
      # Use the value of "target" as a default for each method, if defined.
      # Targets defined in methods or probes override this default value.
      if target:
        method_def.setdefault("target", target)
      # Create the method and add its triggers to the check.
      m = Method(**method_def)
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

  def UsesArtifact(self, artifact):
    """Determines if the check uses the specified artifact."""
    return artifact in self.artifacts

  def Parse(self, unused_conditions, unused_host_data):
    """Runs methods that evaluate whether collected host_data has an issue."""
    pass

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
    self.probe = [Probe(**c) for c in probe]
    self.match = MatchStrToList(kwargs.get("match"))
    self.matcher = checks.Matcher(self.match)
    self.resource = [Probe(**r) for r in resource]
    self.target = Target(**target)
    self.hint = Hint(**hint)
    self.triggers = triggers.Triggers()
    for p in self.probe:
      # If the probe has a target, use it. Otherwise, use the method's target.
      target = p.target or self.target
      self.triggers.Add(p.artifact, target, p)

  def Parse(self, conditions, host_data):
    """Runs probes that evaluate whether collected data has an issue."""
    pass

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
    self.matcher = checks.Matcher(self.match)

  def Parse(self, rdf_data):
    """Process rdf data through filters. Test if results match expectations."""
    pass

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

  def __init__(self, initializer=None, age=None, **kwargs):
    if isinstance(initializer, dict):
      conf = initializer
    else:
      conf = kwargs
    super(Hint, self).__init__(initializer=initializer, age=age, **conf)

  def Parse(self, rdf_data):
    """Processes data according to formatting rules."""
    pass

  def Validate(self):
    """Ensures that required values are set and formatting rules compile."""
    pass
