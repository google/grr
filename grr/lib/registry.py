#!/usr/bin/env python
"""This is the GRR class registry.

A central place responsible for registering plugins. Any class can have plugins
if it defines __metaclass__ = MetaclassRegistry.  Any derived class from this
baseclass will have the member classes as a dict containing class name by key
and class as value.
"""

# The following are abstract base classes
import abc
import logging
import threading


class MetaclassRegistry(abc.ABCMeta):
  """Automatic Plugin Registration through metaclasses."""

  def __init__(cls, name, bases, env_dict):
    abc.ABCMeta.__init__(cls, name, bases, env_dict)

    # Abstract classes should not be registered. We define classes as abstract
    # by giving them the __abstract attribute (this is not inheritable) or by
    # naming them Abstract<ClassName>.
    abstract_attribute = "_%s__abstract" % name

    if (not cls.__name__.startswith("Abstract") and
        not hasattr(cls, abstract_attribute)):
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
          raise RuntimeError("Duplicate names for registered classes: %s, %s" %
                             (cls, cls.classes[cls.__name__]))

        cls.classes[cls.__name__] = cls
        cls.classes_by_name[getattr(cls, "name", None)] = cls
        if hasattr(cls, "_ClsHelpEpilog"):
          cls.__doc__ = "%s\n\n%s" % (getattr(cls, "__doc__", ""),
                                      cls._ClsHelpEpilog())
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

  EVENT_NAME_MAP = {}

  def __init__(cls, name, bases, env_dict):
    MetaclassRegistry.__init__(cls, name, bases, env_dict)

    # Register ourselves as listeners for the events in cls.EVENTS.
    for ev in cls.EVENTS:
      EventRegistry.EVENT_NAME_MAP.setdefault(ev, set()).add(cls)


# Utility functions
class HookRegistry(object):
  """An initializer that can be extended by plugins.

  Any classes which extend this will be instantiated exactly once when the
  system is initialized. This allows plugin modules to register initialization
  routines.
  """

  # A list of class names that have to be initialized before this hook.
  pre = []

  # Already run hooks
  already_run_once = set()

  lock = threading.RLock()

  def _RunSingleHook(self, hook_cls, executed_set, required=None):
    """Run the single hook specified by resolving all its prerequisites."""
    # If we already ran do nothing.
    if hook_cls in executed_set:
      return

    # Ensure all the pre execution hooks are run.
    for pre_hook in hook_cls.pre:
      self._RunSingleHook(pre_hook, executed_set, required=hook_cls.__name__)

    # Now run this hook.
    cls_instance = hook_cls()
    if required:
      logging.debug("Initializing %s, required by %s", hook_cls.__name__,
                    required)
    else:
      logging.debug("Initializing %s", hook_cls.__name__)

    # Always call the Run hook.
    cls_instance.Run()
    executed_set.add(hook_cls)

    # Only call the RunOnce() hook if not already called.
    if hook_cls not in self.already_run_once:
      cls_instance.RunOnce()
      self.already_run_once.add(hook_cls)

  def _RunAllHooks(self, executed_hooks, skip_set):
    for hook_cls in self.__class__.classes.values():
      if skip_set and hook_cls.__name__ in skip_set:
        continue
      self._RunSingleHook(hook_cls, executed_hooks)

  def Init(self, skip_set=None):
    with InitHook.lock:
      executed_hooks = set()
      while 1:
        try:
          # This code allows init hooks to import modules which have more hooks
          # defined - We ensure we only run each hook only once.
          last_run_hooks = len(executed_hooks)
          self._RunAllHooks(executed_hooks, skip_set)
          if last_run_hooks == len(executed_hooks):
            break

        except StopIteration:
          logging.debug("Recalculating Hook dependency.")

  def RunOnce(self):
    """Hooks which only want to be run once."""

  def Run(self):
    """Hooks that can be called more than once."""


class InitHook(HookRegistry):
  """Global GRR init registry.

  Any classes which extend this class will be instantiated exactly
  once when the system is initialized. This allows plugin modules to
  register initialization routines.
  """
  __metaclass__ = MetaclassRegistry


# This method is only used in tests and will rerun all the hooks to create a
# clean state.
def TestInit():
  InitHook().Init()


def Init(skip_set=None):
  if InitHook.already_run_once:
    return

  # This initializes any class which inherits from InitHook.
  InitHook().Init(skip_set)
