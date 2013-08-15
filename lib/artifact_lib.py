#!/usr/bin/env python
"""Library for processing of artifacts.

This file contains non-GRR specific pieces of artifact processing and is
intended to end up as an independent library.
"""

import itertools
import re

from grr.lib import registry


class Error(Exception):
  """Base exception."""


class ArtifactDefinitionError(Error):
  """Artifact is not well defined."""


class ConditionError(Error):
  """An invalid artifact condition was specified."""


class ArtifactProcessingError(Error):
  """Unable to process artifact."""


class KnowledgeBaseInterpolationError(Error):
  """Unable to interpolate path using the Knowledge Base."""


# These labels represent the full set of labels that an Artifact can have.
# This set is tested on creation to ensure our list of labels doesn't get out
# of hand.
# Labels are used to logicaly group Artifacts for ease of use.

ARTIFACT_LABELS = [
    "Antivirus",       # Antivirus related artifacts, e.g. quarantine files.
    "Execution",       # Contain execution events.
    "KnowledgeBase",   # Artifacts used in knowledgebase generation.
    "Logs",            # Contain log files.
    "External Media",  # Contain external media data or events e.g. (USB drives)
    "Network",         # Describe networking state.
    "Authentication",  # Authentication artifacts.
    "Software",        # Installed software.
    "Users",           # Information about users.
    ]


SUPPORTED_OS_LIST = ["Windows", "Linux", "Darwin"]


INTERPOLATED_REGEX = re.compile(r"%%([^%]+?)%%")
# A regex indicating if there are shell globs in this path.
GLOB_MAGIC_CHECK = re.compile("[*?[]")


class Artifact(object):
  """Base class for artifact objects.

  All Artifacts must define a Collect, and a Process class method.

  An Artifact Collector will collect and process the artifact by calling these
  methods.

  The base class implements no real functionality. As a general rule most things
  should inherit from GeneralArtifact instead.
  """

  # Register a metaclass registry to track all artifacts.
  __metaclass__ = registry.MetaclassRegistry

  DESCRIPTION = "Abstract Artifact"
  LABELS = []       # A list of labels that describe what the artifact provides.

  def Collect(self):
    pass

  def Process(self, responses):
    pass

  @classmethod
  def GetKnowledgeBaseArtifacts(cls):
    """Retrieve artifact classes that provide Knowledge Base values."""
    return [a for a in cls.classes.values() if hasattr(a, "PROVIDES")]

  @classmethod
  def GetKnowledgeBaseBootstrapArtifacts(cls):
    """Retrieve  Knowledge Base artifact classes that must be bootstrapped."""
    bootstrap_classes = []
    for artifact_cls in cls.GetKnowledgeBaseArtifacts():
      collector_actions = [c.action for c in artifact_cls.COLLECTORS]
      if "Bootstrap" in collector_actions:
        bootstrap_classes.append(artifact_cls)
    return bootstrap_classes

  @classmethod
  def GetArtifactDependencies(cls):
    """Return a list of knowledgebase path dependencies.

    Returns:
      A list of strings for the required kb objects e.g.
      ["users.appdata", "systemroot"]
    """
    deps = []
    for collector in cls.COLLECTORS:
      if hasattr(collector, "args"):   # Not all collections have args.
        for arg, value in collector.args.items():
          paths = []
          if arg == "path":
            paths.append(value)
          if arg == "paths":
            paths.extend(value)
          for path in paths:
            for match in INTERPOLATED_REGEX.finditer(path):
              deps.append(match.group()[2:-2])   # Strip off %%.
    return deps


class GenericArtifact(Artifact):
  """A generalized Artifact that executes based on class variables.

  Artifacts must be processed by an ArtifactCollectorFlow.

  WARNING: The artifact object is re-instantiated between the Collect and
           Process. State is not preserved.
  """

  # Prevents this from automatically registering.
  __abstract = True  # pylint: disable=g-bad-name

  # Which OS are supported by the Artifact e.g. Linux, Windows, Darwin
  # Note that this can be implemented by CONDITIONS as well, but this
  # provides a more obvious interface for users for common cases.
  SUPPORTED_OS = []

  # List of ArtifactCondition function names that define whether Artifact
  # collection should run. These operate as an AND operator, all conditions
  # must pass for it to run. OR operators should be implemented as their own
  # conditions.
  CONDITIONS = []
  LABELS = []

  # A list of Collector objects.
  COLLECTORS = []

  # A dict to use for path interpolation.
  PATH_ARGS = {}

  def Validate(self):
    """Attempt to validate the artifact has been well defined.

    This is used to enforce Artifact rules.

    Raises:
      ArtifactDefinitionError: If COLLECTORS object is invalid.

    """
    cls_name = self.__class__.__name__
    if not self.__doc__:
      raise ArtifactDefinitionError("Artifact %s has missing doc string" %
                                    cls_name)

    for supp_os in self.SUPPORTED_OS:
      if supp_os not in SUPPORTED_OS_LIST:
        raise ArtifactDefinitionError("Artifact %s has invalid SUPPORTED_OS %s"
                                      % (cls_name, supp_os))

    for condition in self.CONDITIONS:
      if not hasattr(condition, "__call__"):
        raise ArtifactDefinitionError("Artifact %s has invalid condition %s" %
                                      (cls_name, condition))

    for collector in self.COLLECTORS:
      if not hasattr(collector.conditions, "__iter__"):
        raise ArtifactDefinitionError("Artifact %s collector has invalid"
                                      " conditions %s" %
                                      (cls_name, collector.conditions))

      # Catch common mistake of path vs paths.
      if hasattr(collector, "args"):
        if collector.args.get("paths"):
          if isinstance(collector.args.get("paths"), basestring):
            raise ArtifactDefinitionError("Artifact %s collector has arg "
                                          "'paths' that is not a list." %
                                          cls_name)
        if collector.args.get("path"):
          if not isinstance(collector.args.get("path"), basestring):
            raise ArtifactDefinitionError("Artifact %s collector has arg 'path'"
                                          " that is not a string." % cls_name)

    for label in self.LABELS:
      if label not in ARTIFACT_LABELS:
        raise ArtifactDefinitionError("Artifact %s has an invalid label %s."
                                      " Please use one from ARTIFACT_LABELS."
                                      % (cls_name, label))

  @classmethod
  def GetDescription(cls):
    return cls.__doc__.split("\n")[0]


class Collector(object):
  """A basic interface to define an object for collecting data."""

  def __init__(self, action, conditions=None, args=None):
    self.action = action
    self.args = args or {}
    self.conditions = conditions or []


def InterpolateKbAttributes(pattern, knowledge_base):
  """Interpolate all knowledgebase attributes in pattern.

  Args:
    pattern: A string with potential interpolation markers. For example:
      "/home/%%users.username%%/Downloads/"
    knowledge_base: The knowledge_base to interpolate parameters from.

  Yields:
    All unique strings generated by expanding the pattern.
  """
  components = []
  offset = 0

  for match in INTERPOLATED_REGEX.finditer(pattern):
    components.append([pattern[offset:match.start()]])
    # Expand the attribute into the set of possibilities:
    alternatives = []

    try:
      if "." in match.group(1):     # e.g. %%users.username%%
        base_name, attr_name = match.group(1).split(".", 1)
        kb_value = getattr(knowledge_base, base_name.lower())
        if isinstance(kb_value, basestring) and kb_value:
          alternatives.append(kb_value)
        else:
          for value in kb_value:
            sub_attr = getattr(value, attr_name)
            alternatives.append(unicode(sub_attr))
      else:
        kb_value = getattr(knowledge_base, match.group(1).lower())
        if isinstance(kb_value, basestring) and kb_value:
          alternatives.append(kb_value)
    except AttributeError as e:
      raise KnowledgeBaseInterpolationError("Failed to interpolate %s with the "
                                            "knowledgebase. %s" % (pattern, e))

    components.append(set(alternatives))
    offset = match.end()

  components.append([pattern[offset:]])

  # Now calculate the cartesian products of all these sets to form all strings.
  for vector in itertools.product(*components):
    yield "".join(vector)


def ExpandWindowsEnvironmentVariables(data_string, knowledge_base):
  """Take a string and expand any windows environment variables.

  Args:
    data_string: A string, e.g. "%SystemRoot%\\LogFiles"
    knowledge_base: A knowledgebase object.

  Returns:
    A string with available environment variables expanded.
  """
  win_environ_regex = re.compile(r"%([^%]+?)%")
  components = []
  offset = 0
  for match in win_environ_regex.finditer(data_string):
    components.append(data_string[offset:match.start()])

    # KB environment variables are prefixed with environ_.
    kb_value = getattr(knowledge_base, "environ_%s" % match.group(1).lower())
    if isinstance(kb_value, basestring) and kb_value:
      components.append(kb_value)
    else:
      components.append(match.group(1))
    offset = match.end()
  components.append(data_string[offset:])    # Append the final chunk.
  return "".join(components)
