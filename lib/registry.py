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

from grr.client import conf as flags
import logging

# This is required to monkey patch various older libraries so
from grr.lib import compatibility

# ones.
flags.DEFINE_bool("debug", default=False,
                  help="Print debugging statements to the console.")

flags.DEFINE_bool("verbose", default=False,
                  help="Enable debugging. This will enable file logging "
                  "for the service and increase verbosity.")


class MetaclassRegistry(abc.ABCMeta):
  """Automatic Plugin Registration through metaclasses."""

  def __init__(mcs, name, bases, env_dict):
    abc.ABCMeta.__init__(mcs, name, bases, env_dict)

    if not mcs.__name__.startswith("Abstract"):
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

  # This controls the order for execution of initialization functions - the
  # higher the altitude, the later in the process this is executed.
  altitude = 10

  # Already run hooks
  already_run_once = set()

  def __init__(self):
    """Default init hook entry point.

    This can be extended by other init hookers.
    """
    if self.__class__.__name__ not in self.already_run_once:
      self.RunOnce()
      self.already_run_once.add(self.__class__.__name__)

  def RunOnce(self):
    """Hooks which only want to be run once."""

  @classmethod
  def Run(cls):
    """Run all the initialization tasks derived from this class."""
    executed_hooks = []
    # Handle the case where hooks cause an import which adds more hooks.
    while True:
      hooks = [c for c in cls.class_list
               if issubclass(c, cls) and c not in executed_hooks]
      if not hooks: break

      hooks.sort(key=lambda x: x.altitude)

      for cls in hooks:
        logging.info("Running Hook %s", cls.__name__)
        cls()
        executed_hooks.append(cls)


def Init():
  # This initializes any class which inherits from InitHook.
  InitHook().Run()
