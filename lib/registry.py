#!/usr/bin/env python
# Copyright 2010 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""This is the GRR class registry.

A central place responsible for registring plugins. Any class can have plugins
if it defines __metaclass__ = MetaclassRegistry.  Any derived class from this
baseclass will have the member classes as a dict containing class name by key
and class as value.
"""


# The following are abstract base classes
import abc
import threading

from grr.client import conf as flags
import logging

# This is required to monkey patch various older libraries so
# pylint: disable=W0611
from grr.lib import compatibility
# pylint: enable=W0611

flags.DEFINE_bool("debug", default=False,
                  help="Print debugging statements to the console.")

flags.DEFINE_bool("verbose", default=False,
                  help="Enable debugging. This will enable file logging "
                  "for the service and increase verbosity.")


class MetaclassRegistry(abc.ABCMeta):
  """Automatic Plugin Registration through metaclasses."""

  def __init__(mcs, name, bases, env_dict):
    abc.ABCMeta.__init__(mcs, name, bases, env_dict)

    # Abstract classes should not be registered. We define classes as abstract
    # by giving them the __abstract attribute (this is not inheritable) or by
    # naming them Abstract<ClassName>.
    abstract_attribute = "_%s__abstract" % name

    if (not mcs.__name__.startswith("Abstract") and
        not hasattr(mcs, abstract_attribute)):
      # Attach the classes dict to the baseclass and have all derived classes
      # use the same one:
      for base in bases:
        try:
          mcs.classes = base.classes
          mcs.plugin_feature = base.plugin_feature
          mcs.top_level_class = base.top_level_class
          break
        except AttributeError:
          pass

      try:
        mcs.classes[mcs.__name__] = mcs
        mcs.class_list.append(mcs)
      except AttributeError:
        mcs.classes = {mcs.__name__: mcs}
        mcs.class_list = [mcs]
        mcs.plugin_feature = mcs.__name__
        # Keep a reference to the top level class
        mcs.top_level_class = mcs

      try:
        if mcs.top_level_class.include_plugins_as_attributes:
          setattr(mcs.top_level_class, mcs.__name__, mcs)

      except AttributeError:
        pass

  def NewPlugin(mcs, name):
    """Return the class of the implementation that carries that name.

    Args:
       name: The name of the plugin to return.

    Raises:
       KeyError: If the plugin does not exist.

    Returns:
       A the registered class referred to by the name.
    """
    return mcs.classes[name]


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

  # Already run hooks
  already_run_once = set()

  lock = threading.RLock()

  def Init(self):
    with InitHook.lock:
      executed_hooks = []
      while True:
        hooks = []
        for cl in self.__class__.classes.itervalues():
          if cl.__name__ not in executed_hooks:
            # We only care about classes that are actually imported.
            pre = [x for x in cl.pre if x in self.__class__.classes]
            if all([hook in executed_hooks for hook in pre]):
              hooks.append(cl)

        if not hooks:
          break

        for cls in hooks:
          executed_hooks.append(cls.__name__)

          cls_instance = cls()
          logging.info("Initializing %s", cls.__name__)
          # Always call the Run hook.
          cls_instance.Run()

          # Call the RunOnce hook if it has not been called.
          if cls.__name__ not in InitHook.already_run_once:
            cls_instance.RunOnce()
            InitHook.already_run_once.add(cls.__name__)

  def RunOnce(self):
    """Hooks which only want to be run once."""

  def Run(self):
    """Hooks that can be called more than once."""


# This method is only used in tests and will rerun all the hooks to create a
# clean state.
def TestInit():
  InitHook().Init()


def Init():
  if InitHook.already_run_once:
    return
  # This initializes any class which inherits from InitHook.
  InitHook().Init()
