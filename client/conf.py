#!/usr/bin/env python
# Copyright 2011 Google Inc.
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

"""A module to allow option processing from files or registry."""


import collections
import ConfigParser
import exceptions
import optparse
import os
import pdb
import platform
import sys


import logging

if platform.system() == "Windows":
  import _winreg  # pylint: disable=C6204

# This constant is not always present in _winreg if the python version
# is too old.
KEY_WOW64_64KEY = 0x100


class MyOption(optparse.Option):
  """A special option class for delayed processing of help."""

  def take_action(self, action, dest, opt, value, values, parser):
    """Delay processing the help action until all config sources are read."""
    if action == "help":
      # We have not parsed everything yet.
      if parser.state != "Final":
        return

      else:
        # Fill in the metavars from the calculated values
        for option in parser.option_list:
          dest = option.dest
          if dest:
            # Account for possibly large defaults.
            calculated_value = str(
                getattr(parser.values, option.dest)).splitlines()
            if len(calculated_value) == 1 and len(calculated_value[0]) < 50:
              calculated_value = calculated_value[0]
            elif calculated_value:
              # Append the ... if the line is too long
              calculated_value = calculated_value[0] + " ..."

            option.metavar = calculated_value

    optparse.Option.take_action(self, action, dest, opt, value, values, parser)


class MyHelpFormatter(optparse.IndentedHelpFormatter):
  """A special help formatter that displays user helpful messages."""

  def format_usage(self, usage):
    return optparse.IndentedHelpFormatter.format_usage(
        self, usage + "\nNOTE: Defaults shown are currently configured values.")

  def expand_default(self, option):
    """Customized default handler to handle init/registry defaults."""
    if self.parser is None or not self.default_tag:
      return option.help

    default_value = None
    if option.dest:
      default_value = getattr(self.parser.values, option.dest, None)
    if default_value is optparse.NO_DEFAULT or default_value is None:
      default_value = self.NO_DEFAULT_VALUE

    return option.help.replace(self.default_tag, str(default_value))


class OptionParser(optparse.OptionParser):
  """An option parser which supports reading from other sources.

  Argument priority is:
  - Defaults are taken from the code.
  - Read from windows registry (on windows)
  - Read from ini file (Overrides Registry settings).
  - Command line args override previous settings.

  The exception to these is the location of the ini file (--config)
  and (--regpath) which can be specified on the command line before
  evaluating the registry and configuration file.
  """
  state = "PreParse"

  def __init__(self, *args, **kwargs):
    self.flags = optparse.Values()
    kwargs["option_class"] = MyOption
    kwargs["formatter"] = MyHelpFormatter()
    optparse.OptionParser.__init__(self, *args, **kwargs)

  def error(self, msg):
    # This suppresses errors during intermediate parses.
    if self.state == "PreParse":
      raise RuntimeError(msg)

    # This terminates the program on errors.
    optparse.OptionParser.error(self, msg)

  def SetArg(self, key, value):
    # Do not set booleans to false.
    if value == "False":
      return
    optparse.OptionParser.parse_args(self, ["--" + key, value],
                                     values=self.values)

  def ProcessConfigFile(self):
    """Parse options from a config file."""
    try:
      self.values.config
    except AttributeError:
      # Config file was not set so we don't do anything here.
      return

    self._ProcessConfigFile(self.values.config.split(","))

  def _ProcessConfigFile(self, files):
    """Do the real work."""
    conf_file = ConfigParser.SafeConfigParser()
    for path in files:
      try:
        conf_file.read(path)
      except ConfigParser.Error as e:
        logging.error("Config parsing error: %s: %s", path, e)

    for section in conf_file.sections():
      logging.error("Section [%s] is not supported (Only use [DEFAULT])",
                    section)

    # Now parse the args in order:
    for k, v in conf_file.defaults().items():
      try:
        self.SetArg(k, v)
      except RuntimeError as e:
        pass

  def ProcessEnvironment(self):
    """Merge values into options from the environment."""
    for option in self.option_list:
      opt_string = option.get_opt_string()
      if opt_string.startswith("--"):
        opt_string = opt_string[2:]

        try:
          value = os.environ[opt_string.upper()]
          self.SetArg(opt_string, value)
        except (KeyError, RuntimeError):
          pass

  def ProcessRegistry(self):
    """Parse options from a registry key.

    Note that we use the 32 bit registry by not passing KEY_WOW64_64KEY.
    This means that our configuration is stored by default in:
      HKLM\\Software\\Wow6432Node\\Software\\GRR
    """
    try:
      hive, path = self.values.regpath.split("\\", 1)
    except TypeError:
      logging.warn("Registry path invalid: %s", self.values.regpath)
      return
    except AttributeError:
      return

    try:
      sid = _winreg.OpenKey(
          getattr(_winreg, hive),
          path, 0, KEY_WOW64_64KEY | _winreg.KEY_READ)
    except exceptions.WindowsError as e:
      logging.debug("Unable to open config registry key: %s", e)
      return

    i = 0
    while True:
      try:
        name, value, _ = _winreg.EnumValue(sid, i)
      except exceptions.WindowsError as e:
        break
      i += 1

      try:
        self.SetArg(name, str(value))
      except RuntimeError as e:
        pass

  def parse_args(self, args=None, values=None):
    """Parse the args via ini files or windows registry."""
    # Turn off strict parsing - this prevents --help from firing right now.
    self.state = "PreParse"

    # Parse the options once to pick up config files/reg keys etc.
    self.values, self.args = optparse.OptionParser.parse_args(
        self, args=args, values=self.values)

    # Add a config file option
    if platform.system() == "Windows":
      self.ProcessRegistry()
    else:
      # For unix like systems read from ini files or environment.
      self.ProcessEnvironment()
      self.ProcessConfigFile()

    # Turn strict parsing back on. If --help fires now it will show the config
    # file options.
    self.state = "Final"

    # Parse the options again in order to override anything specified in the
    # config file.
    self.values, self.args = optparse.OptionParser.parse_args(
        self, args=args, values=self.values)

    # Copy the new results to the flags. This is required since there may be
    # references still to the old flags object so we cant just swap it.
    for k, v in self.values.__dict__.items():
      self.flags.ensure_value(k, v)

    return self.flags, self.args

  def UpdateConfig(self, update_args):
    """Rewrites the config file with new options.

    Args:
      update_args: list of strings representing the args to update.

    Raises:
     IOError or OSError if we fail to write on the file.
    """
    if getattr(self.flags, "config", None):
      # Deal with config stored in the config file. Only write back things that
      # were read from the file or were specified in args_to_update.

      conf_parser = ConfigParser.SafeConfigParser()
      for path in self.flags.config.split(","):
        try:
          conf_parser.read(path)
        except ConfigParser.Error as e:
          logging.error("Error reading config: %s: %s", path, e)

      # Now override with our new values
      for arg in update_args:
        conf_parser.set(ConfigParser.DEFAULTSECT, arg,
                        str(getattr(self.flags, arg)))

      # Ensure intermediate directories exist
      try:
        os.makedirs(os.path.dirname(self.flags.config))
      except (IOError, OSError):
        pass

      try:
        # We can not use the standard open() call because we need to
        # enforce restrictive file permissions on the created file.
        mode = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        fd = os.open(self.flags.config, mode, 0600)
        with os.fdopen(fd, "wb") as config_file:
          conf_parser.write(config_file)
      except OSError:
        logging.warn("Unable to write config file %s.", self.flags.config)

    elif getattr(self.flags, "regpath", None):
      # Deal with config stored in the registry.
      key = CreateRegistryKeys(self.flags.regpath)
      if not key:
        logging.warn("Failed to update registry config.")
        return
      # Now update the keys with our new values.
      for arg in update_args:
        try:
          _winreg.SetValueEx(key, arg, 0, _winreg.REG_SZ,
                             str(getattr(self.flags, arg)))
        except exceptions.WindowsError as e:
          logging.warn("Unable to write config registry key: %s", e)
      if key:
        key.Close()

  def FlagDict(self):
    """Gets the flags as a dict.

    Returns:
      A dict of named tuples with name, value, type.
    """
    flag_obj = collections.namedtuple("FlagObj", "name value type")
    f_dict = {}
    for flag in self.option_list:
      if not flag.dest:  # Skip special vars such as --help.
        continue
      f_dict[flag.dest] = flag_obj(flag.dest, getattr(self.values, flag.dest),
                                   flag.type)
    return f_dict


# A global flags parser
PARSER = OptionParser()
FLAGS = PARSER.flags




def CreateRegistryKeys(reg_path):
  """Get a handle to our config registry key, creating if it doesn't exist.

  Args:
    reg_path: A path in the registry to create e.g. "HKLM\\Software\\GRR"

  Returns:
    A PyHKEY object or None on failure.

  Note: Nearly this entire function is a hack due to python26 not supporting
        CreateKeyEx which gives us 64 bit registry.
        Remove this all once we move to python27.
  """
  try:
    hive, path = reg_path.split("\\", 1)
    hive = getattr(_winreg, hive)
  except TypeError:
    logging.warn("Registry path invalid: %s", reg_path)
    return

  try:
    return _winreg.OpenKey(
        hive, path, 0, KEY_WOW64_64KEY | _winreg.KEY_WRITE | _winreg.KEY_READ)
  except exceptions.WindowsError as e:
    logging.debug("Unable to open config registry key: %s", e)

  try:
    return _winreg.CreateKeyEx(
        hive, path, 0,
        KEY_WOW64_64KEY | _winreg.KEY_WRITE | _winreg.KEY_READ)
  except exceptions.WindowsError:
    return


# Helper functions for setting options on the global parser object
# pylint: disable=C6409
# pylint: disable=W0622
def DEFINE_string(longopt, default, help):
  PARSER.add_option("", "--%s" % longopt, default=default, type="str",
                    help=help)


def DEFINE_bool(longopt, default, help):
  PARSER.add_option("", "--%s" % longopt, default=default, action="store_true",
                    help=help)


def DEFINE_integer(longopt, default, help):
  PARSER.add_option("", "--%s" % longopt, default=default, type="int",
                    help=help)


def DEFINE_float(longopt, default, help):
  PARSER.add_option("", "--%s" % longopt, default=default, type="float",
                    help=help)


def DEFINE_enum(longopt, default, choices, help):
  PARSER.add_option("", "--%s" % longopt, default=default, choices=choices,
                    type="choice", help=help)


# pylint: enable=W0622
# pylint: enable=C6409


def StartMain(main, argv=None):
  """The main entry point to start applications.

  Parses flags and catches all exceptions for debugging.

  Args:
     main: A main function to call.
     argv: The argv to parse. Default from sys.argv.
  """
  # Make sure we parse all the args
  PARSER.parse_args(args=argv)

  # Call the main function
  try:
    main([sys.argv[0]] + PARSER.args)
  except Exception:
    if PARSER.flags.debug:
      pdb.post_mortem()

    raise
