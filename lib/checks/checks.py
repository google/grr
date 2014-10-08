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


class Matcher(object):
  """Performs comparisons between baseline and result data."""

  def __init__(self, matches):
    method_map = {"NONE": self.GotNone,
                  "ONE": self.GotOne,
                  "ANY": self.GotAny,
                  "ALL": self.GotAll}
    try:
      self.detectors = [method_map.get(match) for match in matches]
    except KeyError:
      raise DefinitionError("Match uses undefined check condition: %s" % match)

  def Detect(self, baseline, results):
    """Run results through detectors and return them if a detector triggers."""
    for detector in self.detectors:
      if detector(baseline, results):
        pass

  @staticmethod
  def GotNone():
    """No baseline data, or zero results."""
    pass

  @staticmethod
  def GotOne():
    """Baseline data with exactly one result."""
    pass

  @staticmethod
  def GotAny():
    """Baseline data with 1+ results."""
    pass

  @staticmethod
  def GotAll():
    """Baseline data with an equal number of baseline and result items."""
    pass


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
    """Runs checks over all host data."""
    pass


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

