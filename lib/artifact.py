#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.

"""Base classes for artifacts.

Artifacts are classes that describe a system artifact. They describe a number
of key properties about the artifact:

  Collectors: How to collect it from the client.
  Processors: How to process the data from the client.
  Storage: How to store the processed data.
"""

import logging

from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import type_info


class Error(Exception):
  """Base exception."""


class ArtifactDefinitionError(Error):
  """Artifact was not well defined."""


class ConditionError(Error):
  """A condition was called that cannot be decided."""


# These labels represent the full set of labels that an Artifact can have.
# This set is tested on creation to ensure our list of labels doesn't get out
# of hand.
# Labels are used to logicaly group Artifacts for ease of use.

ARTIFACT_LABELS = [
    "Execution",       # Contain execution events.
    "Logs",            # Contain log files.
    "Ext Media",       # Contain external media data or events e.g. (USB drives)
    "Network",         # Describe networking state.
    "Auth",            # Authentication artifacts.
    ]


class Collector(object):
  """A wrapper class to define an object for collecting data."""

  def __init__(self, action, conditions=None, args=None):
    self.action = action
    self.args = args or {}
    self.conditions = conditions or []


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

  def __init__(self, parent_flow, use_tsk=True, validate=True):
    """Initialize an artifact.

    Args:
      parent_flow: The flow requesting the artifact.
      use_tsk: Use raw access to access the filesystem.
      validate: Run validation checks.

    The parent flow will be the ArtifactCollectorFlow which will handle the
    download of the artifact. Any flows needed to collect the artifact will
    be children of this flow and any functions required will be implemented
    in that flow.
    """
    super(GenericArtifact, self).__init__()
    self.client = parent_flow.state.get("client")
    self.parent_flow = parent_flow
    if use_tsk:
      self.path_type = rdfvalue.PathSpec.PathType.TSK
    else:
      self.path_type = rdfvalue.PathSpec.PathType.OS

    # Ensure we've been written sanely.
    # Note that this could be removed if it turns out to be expensive. The
    # artifact tests catch anything that this would.
    if validate:
      self.Validate()

  def Collect(self):
    """Collect the raw data from the client for this artifact."""

    # Turn SUPPORTED_OS into a condition.
    for supported_os in self.SUPPORTED_OS:
      self.CONDITIONS.append(SUPPORTED_OS_MAP[supported_os])

    # Check each of the conditions match our target.
    for condition in self.CONDITIONS:
      if not condition(self.client):
        logging.debug("Artifact %s condition %s failed on %s",
                      self.__class__.__name__, condition.func_name,
                      self.client.client_id)
        return

    # Call the collector defined action for each collector.
    for collector in self.COLLECTORS:
      for condition in collector.conditions:
        if not condition(self.client):
          logging.debug("Artifact Collector %s condition %s failed on %s",
                        self.__class__.__name__, condition.func_name,
                        self.client.client_id)
          continue

      action_name = collector.action
      action = getattr(self.parent_flow, action_name)
      action(path_type=self.path_type, **collector.args)

  def Process(self, responses):
    """Process the collected data.

    Args:
      responses: A flow responses object.

    """
    # By default do no processing.
    pass

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
      if supp_os not in SUPPORTED_OS_MAP:
        raise ArtifactDefinitionError("Artifact %s has invalid SUPPORTED_OS %s"
                                      % (cls_name, supp_os))

    for condition in self.CONDITIONS:
      if not hasattr(condition, "__call__"):
        raise ArtifactDefinitionError("Artifact %s has invalid condition %s" %
                                      (cls_name, condition))

    for collector in self.COLLECTORS:
      if not hasattr(self.parent_flow, collector.action):
        raise ArtifactDefinitionError("Artifact %s collector has invalid action"
                                      " %s" % (cls_name, collector.action))
      if not hasattr(collector.conditions, "__iter__"):
        raise ArtifactDefinitionError("Artifact %s collector has invalid"
                                      "conditions %s" % (cls_name,
                                                         collector.conditions))

    for label in self.LABELS:
      if label not in ARTIFACT_LABELS:
        raise ArtifactDefinitionError("Artifact %s has an invalid label %s."
                                      "Please use one from ARTIFACT_LABELS."
                                      % (cls_name, label))

  @classmethod
  def GetDescription(cls):
    return cls.__doc__.split("\n")[0]


def IsLinux(client):
  return client.Get(client.Schema.SYSTEM) == "Linux"


def IsDarwin(client):
  return client.Get(client.Schema.SYSTEM) == "Darwin"


def IsWindows(client):
  return client.Get(client.Schema.SYSTEM) == "Windows"


SUPPORTED_OS_MAP = {
    "Windows": IsWindows,
    "Linux": IsLinux,
    "Darwin": IsDarwin
}


class ArtifactList(type_info.TypeInfoObject):
  """A list of Artifacts names."""

  renderer = "ArtifactListRenderer"

  def Validate(self, value):
    """Value must be a list of artifact names."""
    try:
      iter(value)
    except TypeError:
      raise type_info.TypeValueError(
          "%s not a valid iterable for ArtifactList" % value)
    for val in value:
      if not isinstance(val, basestring):
        raise type_info.TypeValueError("%s not a valid instance string." % val)
      artifact_cls = Artifact.classes.get(val)
      if not artifact_cls or not issubclass(artifact_cls, Artifact):
        raise type_info.TypeValueError("%s not a valid Artifact class." % val)

    return value
