#!/usr/bin/env python
"""Library for processing of artifacts.

This file contains non-GRR specific pieces of artifact processing and is
intended to end up as an independent library.
"""

import itertools
import json
import re

from grr.lib import objectfilter
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import utils


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


class KnowledgeBaseUninitializedError(Error):
  """Attempt to process artifact without a valid Knowledge Base."""


# These labels represent the full set of labels that an Artifact can have.
# This set is tested on creation to ensure our list of labels doesn't get out
# of hand.
# Labels are used to logicaly group Artifacts for ease of use.

ARTIFACT_LABELS = {
    "Antivirus": "Antivirus related artifacts, e.g. quarantine files.",
    "Authentication": "Authentication artifacts.",
    "Configuration Files": "Configuration files artifacts.",
    "Execution": "Contain execution events.",
    "External Media": "Contain external media data or events e.g. USB drives.",
    "KnowledgeBase": "Artifacts used in knowledgebase generation.",
    "Logs": "Contain log files.",
    "Memory": "Artifacts retrieved from Memory.",
    "Network": "Describe networking state.",
    "Processes": "Describe running processes.",
    "Software": "Installed software.",
    "System": "Core system artifacts.",
    "Users": "Information about users.",
    "Volatility": "Artifacts using the Volatility memory forensics framework."
    }

OUTPUT_UNDEFINED = "Undefined"

ACTIONS_MAP = {"RunGrrClientAction": {"required_args": ["client_action"],
                                      "output_type": OUTPUT_UNDEFINED},
               "GetFile": {"required_args": ["path"],
                           "output_type": "StatEntry"},
               "GetFiles": {"required_args": ["path_list"],
                            "output_type": "StatEntry"},
               "GetRegistryKeys": {"required_args": ["path_list"],
                                   "output_type": "StatEntry"},
               "GetRegistryValue": {"required_args": ["path"],
                                    "output_type": "RDFString"},
               "WMIQuery": {"required_args": ["query"],
                            "output_type": "Dict"},
               "RunCommand": {"required_args": ["cmd", "args"],
                              "output_type": "ExecuteResponse"},
               "VolatilityPlugin": {"required_args": ["plugin"],
                                    "output_type": "VolatilityResponse"},
               "CollectArtifacts": {"required_args": ["artifact_list"],
                                    "output_type": OUTPUT_UNDEFINED},
               "CollectArtifactFiles": {"required_args": ["artifact_list"],
                                        "output_type": "StatEntry"},
               "Bootstrap": {"required_args": [],
                             "output_type": OUTPUT_UNDEFINED},
              }


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

  LABELS = []       # A list of labels that describe what the artifact provides.

  def Collect(self):
    pass

  def Process(self, responses):
    pass

  @classmethod
  def GetKnowledgeBaseArtifacts(cls, os):
    """Retrieve artifact classes that provide Knowledge Base values."""
    return [a for a in cls.classes.values() if (
        hasattr(a, "PROVIDES") and os in a.SUPPORTED_OS)]

  @classmethod
  def GetKnowledgeBaseBootstrapArtifacts(cls, os):
    """Retrieve  Knowledge Base artifact classes that must be bootstrapped."""
    bootstrap_classes = []
    for artifact_cls in cls.GetKnowledgeBaseArtifacts(os):
      collector_actions = [c.action for c in artifact_cls.COLLECTORS]
      if "Bootstrap" in collector_actions:
        bootstrap_classes.append(artifact_cls)
    return bootstrap_classes

  @classmethod
  def GetArtifactDependencies(cls, recursive=False, depth=1):
    """Return a set of artifact dependencies.

    Args:
      recursive: If True recurse into dependencies to find their dependencies.
      depth: Used for limiting recursion depth.

    Returns:
      A set of strings containing the dependent artifact names.

    Raises:
      RuntimeError: If maximum recursion depth reached.
    """
    deps = set()
    for collector in cls.COLLECTORS:
      if collector.action == "CollectArtifacts":
        if hasattr(collector, "args") and collector.args.get("artifact_list"):
          deps.update(collector.args.get("artifact_list"))

    if depth > 10:
      raise RuntimeError("Max artifact recursion depth reached.")

    deps_set = set(deps)
    if recursive:
      for dep in deps:
        new_dep = Artifact.classes[dep].GetArtifactDependencies(True,
                                                                depth=depth+1)
        if new_dep:
          deps_set.update(new_dep)

    return deps

  @classmethod
  def GetArtifactPathDependencies(cls):
    """Return a set of knowledgebase path dependencies.

    Returns:
      A set of strings for the required kb objects e.g.
      ["users.appdata", "systemroot"]
    """
    deps = set()
    for collector in cls.COLLECTORS:
      if hasattr(collector, "args"):   # Not all collections have args.
        for arg, value in collector.args.items():
          paths = []
          if arg in ["path", "query"]:
            paths.append(value)
          if arg in ["paths", "path_list"]:
            paths.extend(value)
          for path in paths:
            for match in INTERPOLATED_REGEX.finditer(path):
              deps.add(match.group()[2:-2])   # Strip off %%.
    return deps

  @classmethod
  def FromDict(cls, input_dict):
    """Generate an artifact class from a dict."""
    newclass = type(utils.SmartStr(input_dict["name"]), (cls,), {})
    for attr in ["CONDITIONS", "LABELS", "SUPPORTED_OS", "URLS"]:
      setattr(newclass, attr, input_dict.get(attr.lower(), []))
    newclass.COLLECTORS = []
    for collector_dict in input_dict.get("collectors", []):
      newclass.COLLECTORS.append(Collector(**collector_dict))
    newclass.__doc__ = input_dict["doc"]
    return newclass

  @classmethod
  def ToDict(cls):
    """Convert artifact to a basic dict."""
    out = {}
    for attr in ["CONDITIONS", "LABELS", "SUPPORTED_OS", "URLS"]:
      out[attr.lower()] = getattr(cls, attr, [])
    out["collectors"] = [c.ToDict() for c in cls.COLLECTORS]
    out["name"] = cls.__name__
    out["doc"] = cls.__doc__
    return out

  @classmethod
  def ToExtendedDict(cls):
    """Convert artifact to an extended dict that contains extra info."""
    out = cls.ToDict()
    out["doc"] = cls.GetDescription()
    out["short_description"] = cls.GetShortDescription()
    out["dependencies"] = [str(c) for c in cls.GetArtifactPathDependencies()]
    return out

  @classmethod
  def ToRdfValue(cls):
    """Convert artifact to an RDFValue."""
    return rdfvalue.Artifact(**cls.ToDict())


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

  # URLs that link to information describing what this artifact collects.
  URLS = []

  # A list of Collector objects.
  COLLECTORS = []

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
      try:
        of = objectfilter.Parser(condition).Parse()
        of.Compile(objectfilter.BaseFilterImplementation)
      except ConditionError as e:
        raise ArtifactDefinitionError("Artifact %s has invalid condition %s. %s"
                                      % (cls_name, condition, e))

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

        # Check all returned types.
        if collector.returned_types:
          for rdf_type in collector.returned_types:
            if rdf_type not in rdfvalue.RDFValue.classes:
              raise ArtifactDefinitionError("Artifact %s has a Collector with "
                                            "an invalid return type %s"
                                            % (cls_name, rdf_type))

      if collector.action not in ACTIONS_MAP:
        raise ArtifactDefinitionError("Artifact %s has invalid action %s." %
                                      (cls_name, collector.action))

      required_args = ACTIONS_MAP[collector.action].get("required_args", [])
      missing_args = set(required_args).difference(collector.args.keys())
      if missing_args:
        raise ArtifactDefinitionError("Artifact %s is missing some required "
                                      "args: %s." % (cls_name, missing_args))

    for label in self.LABELS:
      if label not in ARTIFACT_LABELS:
        raise ArtifactDefinitionError("Artifact %s has an invalid label %s."
                                      " Please use one from ARTIFACT_LABELS."
                                      % (cls_name, label))

    # Check all path dependencies exist in the knowledge base.
    valid_fields = rdfvalue.KnowledgeBase().GetKbFieldNames()
    for dependency in self.GetArtifactPathDependencies():
      if dependency not in valid_fields:
        raise ArtifactDefinitionError("Artifact %s has an invalid dependency %s"
                                      ". Artifacts must use defined knowledge "
                                      "attributes." % (cls_name, dependency))

    # Check all artifact dependencies exist.
    for dependency in self.GetArtifactDependencies():
      if dependency not in Artifact.classes:
        raise ArtifactDefinitionError("Artifact %s has an invalid dependency %s"
                                      ". Could not find artifact definition."
                                      % (cls_name, dependency))

  @classmethod
  def GetShortDescription(cls):
    return cls.__doc__.split("\n")[0]

  @classmethod
  def GetDescription(cls):
    return cls.__doc__


class Collector(object):
  """A basic interface to define an object for collecting data."""

  def __init__(self, action, conditions=None, args=None, returned_types=None):
    self.action = action
    self.args = args or {}
    self.conditions = conditions or []
    self.returned_types = returned_types or []

  def ToDict(self):
    """Return a dict representing the collector."""
    coll_dict = {}
    coll_dict["conditions"] = self.conditions
    coll_dict["args"] = self.args
    coll_dict["action"] = self.action
    coll_dict["returned_types"] = self.returned_types
    return coll_dict


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
        kb_value = knowledge_base.Get(base_name.lower())
        if not kb_value:
          raise AttributeError(base_name.lower())
        elif isinstance(kb_value, basestring):
          alternatives.append(kb_value)
        else:
          for value in kb_value:
            sub_attr = value.Get(attr_name)
            alternatives.append(unicode(sub_attr))
      else:
        kb_value = knowledge_base.Get(match.group(1).lower())
        if not kb_value:
          raise AttributeError(match.group(1).lower())
        elif isinstance(kb_value, basestring):
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
    kb_value = getattr(knowledge_base, "environ_%s" % match.group(1).lower(),
                       None)
    if isinstance(kb_value, basestring) and kb_value:
      components.append(kb_value)
    else:
      components.append("%%%s%%" % match.group(1))
    offset = match.end()
  components.append(data_string[offset:])    # Append the final chunk.
  return "".join(components)


def CheckCondition(condition, check_object):
  """Check if a condition matches an object.

  Args:
    condition: A string condition e.g. "os == 'Windows'"
    check_object: Object to validate, e.g. an rdfvalue.KnowledgeBase()

  Returns:
    True or False depending on whether the condition matches.

  Raises:
    ConditionError: If condition is bad.
  """
  try:
    of = objectfilter.Parser(condition).Parse()
    compiled_filter = of.Compile(objectfilter.BaseFilterImplementation)
    return compiled_filter.Matches(check_object)
  except objectfilter.Error as e:
    raise ConditionError(e)


def ExpandWindowsUserEnvironmentVariables(data_string, knowledge_base, sid=None,
                                          username=None):
  """Take a string and expand windows user environment variables based.

  Args:
    data_string: A string, e.g. "%TEMP%\\LogFiles"
    knowledge_base: A knowledgebase object.
    sid: A Windows SID for a user to expand for.
    username: A Windows user name to expand for.

  Returns:
    A string with available environment variables expanded.
  """
  win_environ_regex = re.compile(r"%([^%]+?)%")
  components = []
  offset = 0
  for match in win_environ_regex.finditer(data_string):
    components.append(data_string[offset:match.start()])
    kb_user = knowledge_base.GetUser(sid=sid, username=username)
    kb_value = None
    if kb_user:
      kb_value = getattr(kb_user, match.group(1).lower(), None)
    if isinstance(kb_value, basestring) and kb_value:
      components.append(kb_value)
    else:
      components.append("%%%s%%" % match.group(1))
    offset = match.end()

  components.append(data_string[offset:])    # Append the final chunk.
  return "".join(components)


def ArtifactsFromJson(json_content):
  """Get a list of Artifacts from json."""
  # Read in the json and check its valid json.
  try:
    dat = json.loads(json_content)
    if isinstance(dat, dict):
      raw_list = [dat]
    elif isinstance(dat, list):
      raw_list = dat
    else:
      raise ValueError("Not list or dict.")

  except ValueError as e:
    raise ArtifactDefinitionError("Invalid json for artifact: %s" % e)
  # Convert json into artifact and validate.
  valid_artifacts = []
  for artifact_dict in raw_list:
    # In this case we are feeding parameters directly from potentially
    # untrusted json to our RDFValue class. However, json ensures these are
    # all primitive types as long as there is no other deserialization
    # involved.
    try:
      artifact_value = rdfvalue.Artifact(**artifact_dict)
      artifact_value.Validate()
      valid_artifacts.append(artifact_value)
    except AttributeError as e:
      raise ArtifactDefinitionError("Invalid artifact definition: %s" % e)
  return valid_artifacts
