#!/usr/bin/env python
"""Map the conditions that trigger checks to the methods that perform them."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import itertools


from builtins import map  # pylint: disable=redefined-builtin

from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import checks_pb2


class Error(Exception):
  """Base error class."""


class DefinitionError(Error):
  """A check was defined badly."""


class Target(rdf_structs.RDFProtoStruct):
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


class Condition(object):
  """Conditions specify match criteria for a check."""

  def __init__(self, artifact, os_name=None, cpe=None, label=None):
    if not artifact:
      raise DefinitionError("Trigger condition needs artifact")
    self.artifact = artifact
    self.os_name = os_name
    self.cpe = cpe
    self.label = label
    self.attr = (artifact, os_name, cpe, label)

  def __hash__(self):
    return hash(self.attr)

  def __eq__(self, other):
    return isinstance(other, Condition) and self.attr == other.attr

  def Match(self, artifact, os_name=None, cpe=None, label=None):
    """Whether the condition applies to external data.

    Args:
      artifact: A string identifier for the artifact.
      os_name: An OS string.
      cpe: A CPE string.
      label: A label string.

    Returns:
      True if the query values match non-empty condition values. Empty values
      are ignored in the comparison.
    """
    hit = lambda x: x[0] == x[1] or not x[0]
    seq = [(self.artifact, artifact), (self.os_name, os_name), (self.cpe, cpe),
           (self.label, label)]
    return all(map(hit, seq))

  def Artifacts(self, os_name=None, cpe=None, label=None):
    """Whether the conditions applies, modulo host data.

    Args:
      os_name: An OS string.
      cpe: A CPE string.
      label: A label string.

    Returns:
      True if os_name, cpe or labels match. Empty values are ignored.
    """
    hit = lambda x: x[0] == x[1] or not x[0]
    seq = [(self.os_name, os_name), (self.cpe, cpe), (self.label, label)]
    return all(map(hit, seq))

  def Search(self, artifact, os_name=None, cpe=None, label=None):
    """Whether the condition contains the specified values.

    Args:
      artifact: A string identifier for the artifact.
      os_name: An OS string.
      cpe: A CPE string.
      label: A label string.

    Returns:
      True if the values match the non-empty query attributes.
      Empty query attributes are ignored in the comparison.
    """
    hit = lambda x: x[0] == x[1] or not x[0]
    seq = [(artifact, self.artifact), (os_name, self.os_name), (cpe, self.cpe),
           (label, self.label)]
    return all(map(hit, seq))


class Triggers(object):
  """Triggers inventory the conditions where a check applies."""

  def __init__(self):
    self.conditions = set()
    self._registry = {}

  def __len__(self):
    return len(self.conditions)

  def _Register(self, conditions, callback):
    """Map functions that should be called if the condition applies."""
    for condition in conditions:
      registered = self._registry.setdefault(condition, [])
      if callback and callback not in registered:
        registered.append(callback)

  def Add(self, artifact=None, target=None, callback=None):
    """Add criteria for a check.

    Args:
      artifact: An artifact name.
      target: A tuple of artifact necessary to process the data.
      callback: Entities that should be called if the condition matches.
    """
    # Cases where a target field is undefined or empty need special handling.
    # Repeated field helper in target yields results, so expand this out into a
    # list. If the attribute doesn't exist, default to an empty list.
    # Then, in either case, replace the empty list with one containing a single
    # None value.
    if target is None:
      target = Target()
    os_name = target.Get("os") or [None]
    cpe = target.Get("cpe") or [None]
    label = target.Get("label") or [None]
    attributes = itertools.product(os_name, cpe, label)
    new_conditions = [Condition(artifact, *attr) for attr in attributes]
    self.conditions.update(new_conditions)
    self._Register(new_conditions, callback)

  def Update(self, other, callback):
    """Adds existing triggers to this set, optionally rebuilding the registry.

    Used to aggregate trigger methods from Probes to Methods to Checks.

    Args:
      other: Another Triggers object.
      callback: Registers all the updated triggers to the specified function.
    """
    self.conditions.update(other.conditions)
    self._Register(other.conditions, callback)

  def Match(self, artifact=None, os_name=None, cpe=None, label=None):
    """Test if host data should trigger a check.

    Args:
      artifact: An artifact name.
      os_name: An OS string.
      cpe: A CPE string.
      label: A label string.

    Returns:
      A list of conditions that match.
    """
    return [
        c for c in self.conditions if c.Match(artifact, os_name, cpe, label)
    ]

  def Search(self, artifact=None, os_name=None, cpe=None, label=None):
    """Find the host attributes that trigger data collection.

    Args:
      artifact: An artifact name.
      os_name: An OS string.
      cpe: A CPE string.
      label: A label string.

    Returns:
      A list of conditions that contain the specified attributes.
    """
    return [
        c for c in self.conditions if c.Search(artifact, os_name, cpe, label)
    ]

  def Artifacts(self, os_name=None, cpe=None, label=None):
    """Find the artifacts that correspond with other trigger conditions.

    Args:
      os_name: An OS string.
      cpe: A CPE string.
      label: A label string.

    Returns:
      A list of artifacts to be processed.
    """
    return [
        c.artifact for c in self.conditions if c.Artifacts(os_name, cpe, label)
    ]

  def Calls(self, conditions=None):
    """Find the methods that evaluate data that meets this condition.

    Args:
      conditions: A tuple of (artifact, os_name, cpe, label)

    Returns:
      A list of methods that evaluate the data.
    """
    results = set()
    if conditions is None:
      conditions = [None]
    for condition in conditions:
      for c in self.Match(*condition):
        results.update(self._registry.get(c, []))
    return results
