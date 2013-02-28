#!/usr/bin/env python
"""This is the GRR class registry.

A central place responsible for registring plugins. Any class can have plugins
if it defines __metaclass__ = MetaclassRegistry.  Any derived class from this
baseclass will have the member classes as a dict containing class name by key
and class as value.
"""


# The following are abstract base classes
import abc
import threading

import logging

# This is required to monkey patch various older libraries so
# pylint: disable=W0611
from grr.lib import compatibility
# pylint: enable=W0611


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
          logging.warn("Duplicate names for registered classes: %s, %s",
                       cls, cls.classes[cls.__name__])

        cls.classes[cls.__name__] = cls
        cls.classes_by_name[getattr(cls, "name", None)] = cls
        cls.class_list.append(cls)
      except AttributeError:
        cls.classes = {cls.__name__: cls}
        cls.classes_by_name = {getattr(cls, "name", None): cls}
        cls.class_list = [cls]
        cls.plugin_feature = cls.__name__
        # Keep a reference to the top level class
        cls.top_level_class = cls

      try:
        if cls.top_level_class.include_plugins_as_attributes:
          setattr(cls.top_level_class, cls.__name__, cls)

      except AttributeError:
        pass

  def NewPlugin(cls, name):
    """Return the class of the implementation that carries that name.

    Args:
       name: The name of the plugin to return.

    Raises:
       KeyError: If the plugin does not exist.

    Returns:
       A the registered class referred to by the name.
    """
    return cls.classes[name]


# Utility functions
class InitHook(object):
  """An initializer that can be extended by plugins.

  Any classes which extend this will be instantiated exactly once when the
  system is initialized. This allows plugin modules to register initialization
  routines.
  """

  __metaclass__ = MetaclassRegistry

  # A list of class names that have to be initialized before this hook.
  pre = []

  # A rough order that can be imposed on init hook. Lower number runs earlier.
  order = 100

  # Already run hooks
  already_run_once = set()

  # If false this hook is disabled.
  active = True

  lock = threading.RLock()

  def _RunSingleHook(self, hook_cls, executed_set, required=None):
    """Run the single hook specified by resolving all its prerequisites."""
    # If we already ran do nothing.
    if hook_cls in executed_set:
      return

    # Ensure all the pre execution hooks are run.
    for pre_hook in hook_cls.pre:
      pre_hook_cls = self.classes.get(pre_hook)
      if pre_hook_cls is None:
        raise RuntimeError("Pre Init Hook %s in %s could not"
                           " be found. Missing import?" % (pre_hook, hook_cls))

      self._RunSingleHook(self.classes[pre_hook], executed_set,
                          required=hook_cls.__name__)

    if hook_cls.active:
      # Now run this hook.
      cls_instance = hook_cls()
      if required:
        logging.info("Initializing %s (order %s), required by %s",
                     hook_cls.__name__, hook_cls.order, required)
      else:
        logging.info("Initializing %s (order %s)", hook_cls.__name__,
                     hook_cls.order)

      # Always call the Run hook.
      cls_instance.Run()
      executed_set.add(hook_cls)

      # Only call the RunOnce() hook if not already called.
      if hook_cls not in self.already_run_once:
        cls_instance.RunOnce()
        self.already_run_once.add(hook_cls)
    else:
      logging.info("Skipping %s (order %s) since its disabled.",
                   hook_cls.__name__, hook_cls.order)
      executed_set.add(hook_cls)

  def _RunAllHooks(self, executed_hooks):
    for hook_cls in sorted(self.__class__.classes.values(),
                           key=lambda x: x.order):
      self._RunSingleHook(hook_cls, executed_hooks)

  def Init(self):
    with InitHook.lock:
      executed_hooks = set()
      while 1:
        # This code allows init hooks to import modules which have more hooks
        # defined - We ensure we only run each hook only once.
        last_run_hooks = len(executed_hooks)
        self._RunAllHooks(executed_hooks)
        if last_run_hooks == len(executed_hooks):
          break

  def RunOnce(self):
    """Hooks which only want to be run once."""

  def Run(self):
    """Hooks that can be called more than once."""

  @staticmethod
  def OverrideInitHook(new_cls, hook_cls):
    """Override an existing hook with a new one."""
    hook_cls.pre = hook_cls.pre[:] + [new_cls.__name__]
    hook_cls.active = False


# This method is only used in tests and will rerun all the hooks to create a
# clean state.
def TestInit():
  InitHook().Init()


def Init():
  if InitHook.already_run_once:
    return

  # This initializes any class which inherits from InitHook.
  InitHook().Init()
