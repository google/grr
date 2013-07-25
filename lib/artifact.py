#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.

"""Base classes for artifacts.

Artifacts are classes that describe a system artifact. They describe a number
of key properties about the artifact:

  Collectors: How to collect it from the client.
  Processors: How to process the data from the client.
  Storage: How to store the processed data.
"""

from grr.lib import parsers
from grr.lib import registry
from grr.lib import type_info


class Error(Exception):
  """Base exception."""


class ArtifactDefinitionError(Error):
  """Artifact was not well defined."""


class ConditionError(Error):
  """A condition was called that cannot be decided."""


class ArtifactProcessingError(Error):
  """An artifact could not be processed."""


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
    "Software"         # Installed software.
    ]


class Collector(object):
  """A wrapper class to define an object for collecting data."""

  def __init__(self, action, conditions=None, args=None):
    self.action = action
    self.args = args or {}
    self.conditions = conditions or []


class AFF4ResultWriter(object):
  """A wrapper class to allow writing objects to the AFF4 space."""

  def __init__(self, path, aff4_type, aff4_attribute, mode):
    self.path = path
    self.aff4_type = aff4_type
    self.aff4_attribute = aff4_attribute
    self.mode = mode


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
      if not hasattr(collector.conditions, "__iter__"):
        raise ArtifactDefinitionError("Artifact %s collector has invalid"
                                      " conditions %s" %
                                      (cls_name, collector.conditions))

    for label in self.LABELS:
      if label not in ARTIFACT_LABELS:
        raise ArtifactDefinitionError("Artifact %s has an invalid label %s."
                                      " Please use one from ARTIFACT_LABELS."
                                      % (cls_name, label))

    if hasattr(self, "PROCESSOR"):
      processor = parsers.Parser.classes.get(self.PROCESSOR)
      if not processor:
        raise ArtifactDefinitionError("Artifact %s has an invalid processor %s."
                                      " The processor must be registered as a"
                                      " parser."
                                      % (cls_name, self.PROCESSOR))
      if (not hasattr(processor, "out_type")
          or processor.out_type not in GRRArtifactMappings.rdf_map):
        raise ArtifactDefinitionError("Artifact %s has a a process with an"
                                      " output_type %s which is not in the "
                                      " GRRArtifactMappings."
                                      % (cls_name, processor.out_type))

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


class GRRArtifactMappings(object):
  """SemanticProto to AFF4 storage mappings.

  Class defining mappings between RDFValues collected by Artifacts, and the
  location they are stored in the AFF4 hierarchy.

  Each entry in the map contains:
    1. Location stored relative to the client.
    2. Name of the AFF4 type.
    3. Name of the attribute to be changed.
    4. Method for adding the RDFValue to the Attribute (Set, Append)
  """

  rdf_map = {
      "SoftwarePackage": ("info/software", "InstalledSoftwarePackages",
                          "INSTALLED_PACKAGES", "Append")
      }
