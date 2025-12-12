#!/usr/bin/env python
"""This is the GRR class registry.

A central place responsible for registering plugins. Any class can have plugins
if it defines __metaclass__ = MetaclassRegistry.  Any derived class from this
baseclass will have the member classes as a dict containing class name by key
and class as value.
"""

# The following are abstract base classes
import abc
from collections.abc import Mapping
from typing import Any


# TODO: Remove registry once migration is complete.
# Maps name to the RDFProtoStruct class (circular dep).
_RDFPROTOSTRUCT_NAME_TO_CLS: dict[str, type[Any]] = {}


def RegisterRDFProtoStruct(name: str, cls: type[Any]) -> None:
  _RDFPROTOSTRUCT_NAME_TO_CLS[name] = cls


def GetAllRDFProtoStructs() -> Mapping[str, type[Any]]:
  return _RDFPROTOSTRUCT_NAME_TO_CLS


# Metaclasses confuse the linter so: pylint: disable=no-value-for-parameter


class MetaclassRegistry(abc.ABCMeta):
  """Automatic Plugin Registration through metaclasses."""

  def IsAbstract(cls):
    # Abstract classes should not be registered. We define classes as abstract
    # by giving them the __abstract attribute (this is not inheritable) or by
    # naming them Abstract<ClassName>.
    abstract_attribute = "_%s__abstract" % cls.__name__

    return cls.__name__.startswith("Abstract") or hasattr(
        cls, abstract_attribute
    )

  def IsDeprecated(cls):
    return hasattr(cls, "deprecated")

  def __init__(cls, name, bases, env_dict):
    abc.ABCMeta.__init__(cls, name, bases, env_dict)

    if not cls.IsAbstract():
      # Attach the classes dict to the baseclass and have all derived classes
      # use the same one:
      for base in bases:
        try:
          cls.classes = base.classes
          cls.classes_by_name = base.classes_by_name
          cls.plugin_feature = base.plugin_feature
          cls.top_level_class = base.top_level_class
          break
        except AttributeError:
          pass

      try:
        if cls.classes and cls.__name__ in cls.classes:
          raise RuntimeError(
              "Duplicate names for registered classes: %s, %s"
              % (cls, cls.classes[cls.__name__])
          )

        cls.classes[cls.__name__] = cls
        cls.classes_by_name[getattr(cls, "name", None)] = cls
      except AttributeError:
        cls.classes = {cls.__name__: cls}
        cls.classes_by_name = {getattr(cls, "name", None): cls}
        cls.plugin_feature = cls.__name__
        # Keep a reference to the top level class
        cls.top_level_class = cls

    else:
      # Abstract classes should still have all the metadata attributes
      # registered.
      for base in bases:
        try:
          cls.classes = base.classes
          cls.classes_by_name = base.classes_by_name
          break
        except AttributeError:
          pass

      if not hasattr(cls, "classes"):
        cls.classes = {}

      if not hasattr(cls, "classes_by_name"):
        cls.classes_by_name = {}

  def GetPlugin(cls, name):
    """Return the class of the implementation that carries that name.

    Args:
       name: The name of the plugin to return.

    Raises:
       KeyError: If the plugin does not exist.

    Returns:
       A the registered class referred to by the name.
    """
    return cls.classes[name]


class EventRegistry(MetaclassRegistry):
  """Event registry."""

  EVENT_NAME_MAP = {}
  EVENTS = []

  def __init__(cls, name, bases, env_dict):
    MetaclassRegistry.__init__(cls, name, bases, env_dict)

    if not cls.IsAbstract():
      # Register ourselves as listeners for the events in cls.EVENTS.
      for ev in cls.EVENTS:
        EventRegistry.EVENT_NAME_MAP.setdefault(ev, set()).add(cls)


class FlowRegistry(MetaclassRegistry):
  """A dedicated registry that only contains new style flows."""

  FLOW_REGISTRY = {}
  DEPRECATED_FLOWS = {}

  def __init__(cls, name, bases, env_dict):
    MetaclassRegistry.__init__(cls, name, bases, env_dict)

    if cls.IsAbstract():
      pass
    elif cls.IsDeprecated():
      cls.DEPRECATED_FLOWS[name] = cls
    else:
      cls.FLOW_REGISTRY[name] = cls

  @classmethod
  def FlowClassByName(mcs, flow_name):
    flow_cls = mcs.FLOW_REGISTRY.get(flow_name)
    if flow_cls is None:
      flow_cls = mcs.DEPRECATED_FLOWS.get(flow_name)
      if flow_cls is None:
        raise ValueError("Flow '%s' not known." % flow_name)

    return flow_cls


class CronJobRegistry(MetaclassRegistry):
  """A dedicated registry that only contains cron jobs."""

  CRON_REGISTRY = {}

  def __init__(cls, name, bases, env_dict):
    MetaclassRegistry.__init__(cls, name, bases, env_dict)

    if not cls.IsAbstract():
      cls.CRON_REGISTRY[name] = cls

  @classmethod
  def CronJobClassByName(mcs, job_name):
    job_cls = mcs.CRON_REGISTRY.get(job_name)
    if job_cls is None:
      raise ValueError("CronJob '%s' not known." % job_name)

    return job_cls


class SystemCronJobRegistry(CronJobRegistry):
  """A dedicated registry that only contains cron jobs."""

  SYSTEM_CRON_REGISTRY = {}

  def __init__(cls, name, bases, env_dict):
    super().__init__(name, bases, env_dict)

    if not cls.IsAbstract():
      cls.SYSTEM_CRON_REGISTRY[name] = cls

  @classmethod
  def CronJobClassByName(mcs, job_name):
    job_cls = mcs.SYSTEM_CRON_REGISTRY.get(job_name)
    if job_cls is None:
      raise ValueError("CronJob '%s' not known." % job_name)

    return job_cls


class OutputPluginRegistry(MetaclassRegistry):
  """A dedicated registry that only contains output plugins."""

  PLUGIN_REGISTRY = {}

  def __init__(cls, name, bases, env_dict):
    MetaclassRegistry.__init__(cls, name, bases, env_dict)

    if not cls.IsAbstract():
      cls.PLUGIN_REGISTRY[name] = cls

  @classmethod
  def PluginClassByName(mcs, plugin_name):
    return mcs.PLUGIN_REGISTRY.get(plugin_name)
