#!/usr/bin/env python
"""This is the GRR config management code.

This handles opening and parsing of config files.
"""

import collections
import ConfigParser
import os
import re
import StringIO
import sys
import urlparse
import zipfile

from grr.client import conf as flags
import logging

from grr.lib import defaults
from grr.lib import lexer
from grr.lib import registry
from grr.lib import type_info


flags.DEFINE_string("config", defaults.CONFIG,
                    "Primary Configuration file to use.")

flags.DEFINE_list("secondary_configs", [],
                  "Secondary configuration files to load.")

flags.DEFINE_bool("config_help", False,
                  "Print help about the configuration.")

flags.DEFINE_list("config_execute", "",
                  "Execute these sections after initializing.")

flags.DEFINE_list("plugins", [],
                  "Load these files as additional plugins.")


class Error(Exception):
  """Base class for configuration exceptions."""


class ConfigFormatError(Error):
  """Raised when configuration file is formatted badly."""


class ConfigWriteError(Error):
  """Raised when we failed to update the config."""


class ConfigFilter(object):
  """A configuration filter can transform a configuration parameter."""

  __metaclass__ = registry.MetaclassRegistry

  name = "identity"

  def Filter(self, data):
    return data


class Literal(ConfigFilter):
  """A filter which does not interpolate."""
  name = "literal"


class Lower(ConfigFilter):
  name = "lower"

  def Filter(self, data):
    return data.lower()


class Upper(ConfigFilter):
  name = "upper"

  def Filter(self, data):
    return data.upper()


class Filename(ConfigFilter):
  name = "file"

  def Filter(self, data):
    return open(data, "rb").read(1024000)


class Base64(ConfigFilter):
  name = "base64"

  def Filter(self, data):
    return data.decode("base64")


class Env(ConfigFilter):
  """Interpolate environment variables."""
  name = "env"

  def Filter(self, data):
    return os.environ.get(data.upper(), "")


class Expand(ConfigFilter):
  """Expands the input as a configuration parameter."""
  name = "expand"

  def Filter(self, data):
    return CONFIG.InterpolateValue(data)


class Flags(ConfigFilter):
  """Get the parameter from the flags."""
  name = "flags"

  def Filter(self, data):
    return getattr(flags.FLAGS, data)


# Inherit from object required because RawConfigParser is an old style class.
class GRRConfigParser(ConfigParser.RawConfigParser, object):
  """The base class for all GRR configuration parsers."""
  __metaclass__ = registry.MetaclassRegistry

  # Configuration parsers are named. This name is used to select the correct
  # parser from the --config parameter which is interpreted as a url.
  name = None

  # Set to True by the parsers if the file exists.
  parsed = None

  def RawData(self):
    """Convert the file to a more suitable data structure."""
    raw_data = collections.OrderedDict()
    for section in self.sections():
      raw_data[section] = collections.OrderedDict()
      for key, value in self.items(section):
        raw_data[section][key] = value

    return raw_data


class ConfigFileParser(GRRConfigParser):
  """A parser for ini style config files."""

  name = "file"

  def __init__(self, filename=None, data=None, fd=None):
    super(ConfigFileParser, self).__init__()
    self.optionxform = str

    if fd:
      self.parsed = self.readfp(fd)
      self.filename = filename or fd.name

    elif filename:
      self.parsed = self.read(filename)
      self.filename = filename

    elif data is not None:
      fd = StringIO.StringIO(data)
      self.parsed = self.readfp(fd)
      self.filename = filename
    else:
      raise RuntimeError("Filename not specified.")

  def __str__(self):
    return "<%s filename=\"%s\">" % (self.__class__.__name__, self.filename)

  def SaveData(self, raw_data):
    """Store the raw data as our configuration."""
    if self.filename is None:
      raise IOError("Unknown filename")

    logging.info("Writing back configuration to file %s", self.filename)
    # Ensure intermediate directories exist
    try:
      os.makedirs(os.path.dirname(self.filename))
    except (IOError, OSError):
      pass

    try:
      # We can not use the standard open() call because we need to
      # enforce restrictive file permissions on the created file.
      mode = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
      fd = os.open(self.filename, mode, 0600)
      with os.fdopen(fd, "wb") as config_file:
        self.SaveDataToFD(raw_data, config_file)

    except OSError as e:
      logging.warn("Unable to write config file %s: %s.", self.filename, e)

  def SaveDataToFD(self, raw_data, fd):
    """Merge the raw data with the config file and store it."""
    for section, data in raw_data.items():
      try:
        self.add_section(section)
      except ConfigParser.DuplicateSectionError:
        pass

      for key, value in data.items():
        self.set(section, key, value=value)

    self.write(fd)


class StringInterpolator(lexer.Lexer):
  r"""Implements a lexer for the string interpolation language.

  Config files may specify nested interpolation codes:

  - The following form specifies an interpolation command:
      %(arg string|filter)

    Where arg string is an arbitrary string and filter is the name of a filter
    function which will receive the arg string. If filter is omitted, the arg
    string is interpreted as a section.parameter reference and expanded from
    within the config system.

  - Interpolation commands may be nested. In this case, the interpolation
    proceeds from innermost to outermost:

    e.g. %(arg1 %(arg2|filter2)|filter1)

      1. First arg2 is passed through filter2.
      2. The result of that is appended to arg1.
      3. The combined string is then filtered using filter1.

  - The following characters must be escaped by preceeding them with a single \:
     - ()|
  """

  tokens = [
      # When in literal mode, only allow to escape }
      lexer.Token("Literal", r"\\[^}]", "AppendArg", None),

      # Allow escaping of special characters
      lexer.Token(None, r"\\(.)", "Escape", None),

      # Literal sequence is %{....}. Literal states can not be nested further,
      # i.e. we include anything until the next }. It is still possible to
      # escape } if this character needs to be inserted literally.
      lexer.Token("Literal", r"\}", "EndLiteralExpression,PopState", None),
      lexer.Token("Literal", r"[^}]+", "AppendArg", None),
      lexer.Token(None, r"\%\{", "StartExpression,PushState", "Literal"),

      # Expansion sequence is %(....)
      lexer.Token(None, r"\%\(", "StartExpression", None),
      lexer.Token(None, r"\|([a-zA-Z]+)\)", "Filter", None),
      lexer.Token(None, r"\)", "ExpandArg", None),

      # Glob up as much data as possible to increase efficiency here.
      lexer.Token(None, r"[^()%{}|\\]+", "AppendArg", None),
      lexer.Token(None, r".", "AppendArg", None),

      # Empty input is also ok.
      lexer.Token(None, "^$", None, None)
      ]

  STRING_ESCAPES = {"\\\\": "\\",
                    "\\n": "\n",
                    "\\t": "\t",
                    "\\r": "\r"}

  def __init__(self, data, config, default_section="", parameter=None):
    self.stack = [""]
    self.default_section = default_section
    self.parameter = parameter
    self.config = config
    super(StringInterpolator, self).__init__(data)

  def Escape(self, string="", **_):
    """Support standard string escaping."""
    # Translate special escapes:
    self.stack[-1] += self.STRING_ESCAPES.get(string, string[1:])

  def Error(self, e):
    """Parse errors are fatal."""
    raise ConfigFormatError("While parsing %s: %s" % (self.parameter, e))

  def StartExpression(self, **_):
    """Start processing a new expression."""
    # Extend the stack for the new expression.
    self.stack.append("")

  def EndLiteralExpression(self, **_):
    if len(self.stack) <= 1:
      raise lexer.ParseError(
          "Unbalanced literal sequence: Can not expand '%s'" %
          self.processed_buffer)

    arg = self.stack.pop(-1)
    self.stack[-1] += arg

  def Filter(self, match=None, **_):
    """Filter the current expression."""
    arg = self.stack.pop(-1)

    # Filters can be specified as a comma separated list.
    for filter_name in match.group(1).split(","):
      filter_object = ConfigFilter.classes_by_name.get(filter_name)
      if filter_object is None:
        raise RuntimeError("Unknown filter function %r" % filter_name)

      arg = filter_object().Filter(arg)

    self.stack[-1] += arg

  def ExpandArg(self, **_):
    """Expand the args as a section.parameter from the config."""
    # This function is called when we see close ) and the stack depth has to
    # exactly match the number of (.
    if len(self.stack) <= 1:
      raise lexer.ParseError(
          "Unbalanced parenthesis: Can not expand '%s'" % self.processed_buffer)

    # This is the full parameter name: e.g. Logging.path
    parameter_name = self.stack.pop(-1)
    if "." not in parameter_name:
      parameter_name = "%s.%s" % (self.default_section, parameter_name)

    final_value = self.config[parameter_name]
    if final_value is None:
      final_value = ""

    type_info_obj = (self.config.FindTypeInfo(parameter_name) or
                     type_info.String())

    # Encode the interpolated string according to its type.
    self.stack[-1] += type_info_obj.ToString(final_value)

  def AppendArg(self, string="", **_):
    self.stack[-1] += string

  def Parse(self):
    self.Close()
    if len(self.stack) != 1:
      raise lexer.ParseError("Nested expression not balanced.")

    return self.stack[0]


class GrrConfigManager(object):
  """Manage configuration system in GRR."""

  # This is the type info set describing all configuration
  # parameters. It is a global shared between all configuration instances,
  type_infos = type_info.TypeDescriptorSet()

  # We store the defaults here. They too are global. Since they are
  # declared by DEFINE_*() calls.
  defaults = {}

  def __init__(self, environment=None):
    """Initialize the configuration manager.

    Args:
      environment: A dictionary containing seed data to use in interpolating the
        configuration file. The dictionary has keys which are section names, and
        values which are dictionaries of key, value pairs.
    """
    self.environment = environment or {}

    self.raw_data = {}
    self.validated = set()

  def Validate(self, parameters):
    """Validate sections or individual parameters.

    The GRR configuration file contains several sections, used by different
    components. Many of these components don't care about other sections. This
    method allows a component to declare in advance what sections and parameters
    it cares about, and have these validated.

    Args:
      parameters: A list of section names or specific parameters (in the format
        section.name) to validate.

    Raises:
      ConfigFormatError: if a parameter fails to validate.
    """
    if isinstance(parameters, basestring):
      parameters = [parameters]

    for parameter in parameters:
      for descriptor in self.type_infos:
        if (("." in parameter and descriptor.name == parameter) or
            (parameter == descriptor.section)):
          value = self.Get(descriptor.name)
          try:
            descriptor.Validate(value)
          except type_info.TypeValueError as e:
            raise ConfigFormatError("Error while parsing %s: %s." % (
                descriptor.name, str(e)))

  def SetEnv(self, key=None, value=None, **env):
    """Update the environment with new data.

    The environment is a temporary configuration layer which takes precedence
    over the configuration files. Components (i.e. main programs) can set
    environment strings in order to fine tune specific important configuration
    parameters relevant to the specific component.

    Practically, this is basically the same as calling Set(), except that Set()
    adds the value to the configuration data - so a subsequent Write() write the
    new data to the configuration file. SetEnv() values do not get written to
    the configuration file.

    Keywords are section names containing dicts of key, value pairs. These will
    completely replace existing sections in the environment.

    Args:
      key: The key to set (e.g. Environment.component).
      value: The value.
      **env: Additional parameters to incorporate into the environment.
    """
    if key is not None:
      self.environment[key] = value
    else:
      self.environment.update(env)

  def SetRaw(self, name, value):
    """Set the raw string without verification or escaping."""
    section, key = self._GetSectionName(name)
    section_data = self.raw_data.setdefault(section, {})

    type_info_obj = (self._FindTypeInfo(section, key) or
                     type_info.String(name=name))

    section_data[key] = type_info_obj.ToString(value)

  def Set(self, name, value, verify=True):
    """Update the configuration option with a new value."""
    section, key = self._GetSectionName(name)

    # Check if the new value conforms with the type_info.
    type_info_obj = self._FindTypeInfo(section, key)
    if type_info_obj is None:
      if verify:
        logging.warn("Setting new value for undefined config parameter %s",
                     name)

      type_info_obj = type_info.String(name=name)

    section_data = self.raw_data.setdefault(section, {})
    if value is None:
      section_data.pop(key, None)

    elif verify:
      type_info_obj.Validate(value)

    value = type_info_obj.ToString(value)
    section_data[key] = self.EscapeString(value)

  def EscapeString(self, string):
    """Escape special characters when encoding to a string."""
    return re.sub(r"([\\%){}])", r"\\\1", string)

  def Write(self):
    """Write out the updated configuration to the fd."""
    self.parser.SaveData(self.raw_data)

  def WriteToFD(self, fd):
    """Write out the updated configuration to the fd."""
    self.parser.SaveDataToFD(self.raw_data, fd)

  def _GetSectionName(self, name):
    """Break the name into section and key."""
    try:
      section, key = name.split(".", 1)
      return section, key
    except ValueError:
      raise RuntimeError("Section not specified")

  def AddOption(self, descriptor):
    """Registers an option with the configuration system.

    Args:
      descriptor: A TypeInfoObject instance describing the option.

    Raises:
      RuntimeError: The descriptor's name must contain a . to denote the section
         name, otherwise we raise.
    """
    descriptor.section, key = self._GetSectionName(descriptor.name)
    self.type_infos.Append(descriptor)

    # Register this option's default value.
    self.defaults.setdefault(
        descriptor.section, {})[key] = descriptor.GetDefault()

  def PrintHelp(self):
    for descriptor in sorted(self.type_infos, key=lambda x: x.name):
      print descriptor.Help()
      print "* Value = %s\n" % self[descriptor.name]

  def MergeData(self, raw_data):
    for section, data in raw_data.items():
      section_dict = self.raw_data.setdefault(
          section, collections.OrderedDict())

      for k, v in data.items():
        section_dict[k] = v

  def _GetParserFromFilename(self, path):
    """Returns the appropriate parser class from the filename url."""
    # Find the configuration parser.
    url = urlparse.urlparse(path, scheme="file")
    for parser_cls in GRRConfigParser.classes.values():
      if parser_cls.name == url.scheme:
        return parser_cls

    # If url is a filename:
    if os.access(path, os.R_OK):
      return ConfigFileParser

  def LoadSecondaryConfig(self, url):
    """Loads an additional configuration file.

    The configuration system has the concept of a single Primary configuration
    file, and multiple secondary files. The primary configuration file is the
    main file that is used by the program. Any writebacks will only be made to
    the primary configuration file. Secondary files contain additional
    configuration data which will be merged into the configuration system.

    This method adds an additional configuration file.

    Args:
      url: The url of the configuration file that will be loaded. For
           example file:///etc/grr.conf
           or reg://HKEY_LOCAL_MACHINE/Software/GRR.

    Returns:
      The parser used to parse this configuration source.
    """
    parser_cls = self._GetParserFromFilename(url)
    parser = parser_cls(filename=url)
    logging.info("Loading configuration from %s", url)

    self.MergeData(parser.RawData())

    return parser

  def Initialize(self, filename=None, data=None, fd=None, reset=True,
                 validate=True, must_exist=False):
    """Initializes the config manager.

    This method is used to add more config options to the manager. The config
    can be given as one of the parameters as described in the Args section.

    Args:
      filename: The name of the configuration file to use.

      data: The configuration given directly as a long string of data.

      fd: A file descriptor of a configuration file.

      reset: If true, the previous configuration will be erased.

      validate: If true, new values are checked for their type. Can be disabled
        to speed up testing.

      must_exist: If true the data source must exist and be a valid
        configuration file, or we raise an exception.

    Raises:
      RuntimeError: No configuration was passed in any of the parameters.

      ConfigFormatError: Raised when the configuration file is invalid or does
        not exist..
    """
    self.validate = validate
    if reset:
      # Clear previous configuration.
      self.raw_data = {}

    if fd is not None:
      self.parser = ConfigFileParser(fd=fd)
      self.MergeData(self.parser.RawData())

    elif filename is not None:
      self.parser = self.LoadSecondaryConfig(filename)
      if must_exist and not self.parser.parsed:
        raise ConfigFormatError(
            "Unable to parse config file %s" % filename)

    elif data is not None:
      self.parser = ConfigFileParser(data=data)
      self.MergeData(self.parser.RawData())

    else:
      raise RuntimeError("Registry path not provided.")

  def __getitem__(self, name):
    """Retrieve a configuration value after suitable interpolations."""
    return self.Get(name)

  def GetRaw(self, name):
    """Get the raw value without interpolations."""
    if name in self.environment:
      return self.environment[name]

    section_name, key = self._GetSectionName(name)
    return self._GetValue(section_name, key)

  def Get(self, name, verify=True, environ=True):
    """Get the value contained  by the named parameter.

    This method applies interpolation/escaping of the named parameter and
    retrieves the interpolated value.

    Args:
      name: The name of the parameter to retrieve. This should be in the format
        of "Section.name"
      verify: The retrieved parameter will also be verified for sanity according
        to its type info descriptor.
      environ: If True we consider the configuration environment in resolving
        this.

    Returns:
      The value of the parameter.
    """
    if environ and name in self.environment:
      return self.environment[name]

    section_name, key = self._GetSectionName(name)
    type_info_obj = self._FindTypeInfo(section_name, key)
    if type_info_obj is None:
      # Only warn for real looking parameters.
      if verify and not key.startswith("__"):
        logging.debug("No config declaration for %s - assuming String",
                      name)

      type_info_obj = type_info.String(name=name, default="")

    value = self.NewlineFixup(self._GetValue(section_name, key))
    try:
      return self.InterpolateValue(
          value, type_info_obj=type_info_obj,
          default_section=section_name)

    except (lexer.ParseError, type_info.TypeValueError) as e:
      raise ConfigFormatError("While parsing %s: %s" % (name, e))

  def _GetValue(self, section_name, key):
    """Search for the value based on section inheritance."""
    # Try to get it from the file data first.
    value = self.raw_data.get(section_name, {}).get(key)

    # Fall back to the environment.
    if value is None:
      value = self.environment.get(section_name, {}).get(key)

    # Or else try the defaults.
    if value is None:
      value = self.defaults.get(section_name, {}).get(key)

    if value is None and not key.startswith("@"):
      # Maybe its inherited?
      inherited_from = self._GetValue(section_name, "@inherit_from_section")
      if inherited_from is not None:
        return self._GetValue(inherited_from, key)

    return value

  def FindTypeInfo(self, parameter_name):
    try:
      section, parameter = parameter_name.split(".", 1)
      return self._FindTypeInfo(section, parameter)
    except ValueError:
      pass

  def _FindTypeInfo(self, section_name, key):
    """Search for a type_info instance which describes this key."""
    if "." in key:
      try:
        section_name, key = self._GetSectionName(key)
        return self._FindTypeInfo(section_name, key)
      except ValueError:
        pass

    section = self.raw_data.get(section_name) or self.defaults.get(section_name)
    if section is None:
      return None

    result = self.type_infos.get("%s.%s" % (section_name, key))
    if result is None:
      # Maybe its inherited?
      inherited_from = section.get("@inherit_from_section")
      if inherited_from:
        return self._FindTypeInfo(inherited_from, key)

    return result

  def InterpolateValue(self, value, type_info_obj=type_info.String(),
                       default_section=None):
    """Interpolate the value and parse it with the appropriate type."""
    # It is only possible to interpolate strings.
    if isinstance(value, basestring):
      value = StringInterpolator(
          value, self, default_section, parameter=type_info_obj.name).Parse()

      # Parse the data from the string.
      value = type_info_obj.FromString(value)

    return value

  def NewlineFixup(self, input_data):
    """Fixup lost newlines in the config.

    Args:
      input_data: Data to fix up.

    Returns:
      The same data but with the lines fixed.

    Fixup function to handle the python 2 issue of losing newlines in the
    config parser options. This is resolved in python 3 and this can be
    deprecated then. Essentially an option containing a newline will be
    returned without the newline.

    This function handles some special cases we need to deal with as a hack
    until it is resolved properly.
    """
    if not isinstance(input_data, basestring):
      return input_data
    result_lines = []
    newline_after = ["DEK-Info:"]
    for line in input_data.splitlines():
      result_lines.append(line)
      for nl in newline_after:
        if line.startswith(nl):
          result_lines.append("")
    return "\n".join(result_lines)

  def ExecuteSection(self, section_name):
    """Uses properties set in section_name to override other properties.

    This is used by main components to override settings in other components,
    based on their own configuration. For example, the following will update the
    client components running inside the demo:

    [Demo]
    Client.rss_max = 4000

    Args:
      section_name: The name of the section to execute.
    """
    logging.info("Executing section %s: %s", section_name,
                 self["%s.__doc__" % section_name])
    section = self.raw_data.get(section_name)
    if section:
      for key in section:
        if "." in key:
          # Keys which are marked with ! will be written as raw to the
          # new section. The means any special escape sequences will
          # remain.
          if key.endswith("!"):
            self.SetRaw(key[:-1], self.GetRaw("%s.%s" % (section_name, key)))
          else:
            self.Set(key, self.Get("%s.%s" % (section_name, key)))

  # pylint: disable=g-bad-name,redefined-builtin
  def DEFINE_bool(self, name, default, help):
    """A helper for defining boolean options."""
    self.AddOption(type_info.Bool(name=name, default=default,
                                  description=help))

  def DEFINE_float(self, name, default, help):
    """A helper for defining float options."""
    self.AddOption(type_info.Float(name=name, default=default,
                                   description=help))

  def DEFINE_integer(self, name, default, help):
    """A helper for defining integer options."""
    self.AddOption(type_info.Integer(name=name, default=default,
                                     description=help))

  def DEFINE_string(self, name, default, help):
    """A helper for defining string options."""
    self.AddOption(type_info.String(name=name, default=default,
                                    description=help))

  def DEFINE_list(self, name, default, help):
    """A helper for defining lists of strings options."""
    self.AddOption(type_info.List(name=name, default=default,
                                  description=help,
                                  validator=type_info.String()))

  # pylint: enable=g-bad-name


# Global for storing the config.
CONFIG = GrrConfigManager()


# pylint: disable=g-bad-name,redefined-builtin
def DEFINE_bool(name, default, help):
  """A helper for defining boolean options."""
  CONFIG.AddOption(type_info.Bool(name=name, default=default,
                                  description=help))


def DEFINE_float(name, default, help):
  """A helper for defining float options."""
  CONFIG.AddOption(type_info.Float(name=name, default=default,
                                   description=help))


def DEFINE_integer(name, default, help):
  """A helper for defining integer options."""
  CONFIG.AddOption(type_info.Integer(name=name, default=default,
                                     description=help))


def DEFINE_boolean(name, default, help):
  """A helper for defining boolean options."""
  CONFIG.AddOption(type_info.Bool(name=name, default=default,
                                  description=help))


def DEFINE_string(name, default, help):
  """A helper for defining string options."""
  CONFIG.AddOption(type_info.String(name=name, default=default,
                                    description=help))


def DEFINE_choice(name, default, choices, help):
  """A helper for defining choice string options."""
  CONFIG.AddOption(type_info.Choice(
      name=name, default=default, choices=choices,
      description=help))


def DEFINE_list(name, default, help):
  """A helper for defining lists of strings options."""
  CONFIG.AddOption(type_info.List(name=name, default=default,
                                  description=help,
                                  validator=type_info.String()))


def DEFINE_option(type_descriptor):
  CONFIG.AddOption(type_descriptor)

# pylint: enable=g-bad-name


DEFINE_string("Environment.component", "GRR",
              "The main component which is running. It is set by the "
              "main program.")

DEFINE_list("Environment.execute_sections", [],
            "These sections will be executed when a config is read. It is set "
            "by the environment of the running component to allow config files "
            "to tune configuration to the correct component.")


def ReloadConfig():
  """Reload the config from the command line flag."""
  # Try to find the correct configuration parser.
  CONFIG.Initialize(filename=flags.FLAGS.config, must_exist=True)

  # Load all secondary files.
  for config_url in flags.FLAGS.secondary_configs:
    CONFIG.LoadSecondaryConfig(config_url)

  # Execute the component section. This allows a component to specify a section
  # to execute for component specific configuration.
  CONFIG.ExecuteSection(CONFIG["Environment.component"])

  # Execute configuration sections specified by the current component.
  for section_name in CONFIG["Environment.execute_sections"]:
    CONFIG.ExecuteSection(section_name)

  # Execute configuration sections specified on the command line.
  for section_name in flags.FLAGS.config_execute:
    CONFIG.ExecuteSection(section_name)


class ConfigLibInit(registry.InitHook):
  """Initializer for the config, reads in the config file."""

  order = 1

  def RunOnce(self):
    ReloadConfig()

    # Does the user want to dump help?
    if flags.FLAGS.config_help:
      print "Configuration overview."
      CONFIG.PrintHelp()
      sys.exit(0)


class PluginLoader(registry.InitHook):
  """Loads additional plugins specified by the user."""

  pre = ["ConfigLibInit"]

  PYTHON_EXTENSIONS = [".py", ".pyo", ".pyc"]

  def RunOnce(self):
    for path in flags.FLAGS.plugins:
      self.LoadPlugin(path)

  @classmethod
  def LoadPlugin(cls, path):
    """Load (import) the plugin at the path."""
    if not os.access(path, os.R_OK):
      logging.error("Unable to find %s", path)
      return

    path = os.path.abspath(path)
    directory, filename = os.path.split(path)
    module_name, ext = os.path.splitext(filename)

    # Its a python file.
    if ext in cls.PYTHON_EXTENSIONS:
      # Make sure python can find the file.
      sys.path.insert(0, directory)

      try:
        logging.info("Loading user plugin %s", path)
        __import__(module_name)
      except Exception, e:  # pylint: disable=broad-except
        logging.error("Error loading user plugin %s: %s", path, e)
      finally:
        sys.path.pop(0)

    elif ext == ".zip":
      zfile = zipfile.ZipFile(path)

      # Make sure python can find the file.
      sys.path.insert(0, path)
      try:
        logging.info("Loading user plugin archive %s", path)
        for name in zfile.namelist():
          # Change from filename to python package name.
          module_name, ext = os.path.splitext(name)
          if ext in cls.PYTHON_EXTENSIONS:
            module_name = module_name.replace("/", ".").replace(
                "\\", ".")

            try:
              __import__(module_name.strip("\\/"))
            except Exception as e:  # pylint: disable=broad-except
              logging.error("Error loading user plugin %s: %s",
                            path, e)

      finally:
        sys.path.pop(0)

    else:
      logging.error("Plugin %s has incorrect extension.", path)
