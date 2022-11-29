#!/usr/bin/env python
"""This is the GRR config management code.

This handles opening and parsing of config files.
"""
import collections
from collections import abc
import copy
import io
import logging
import os
import platform
import re
import sys
import traceback
from typing import Any, BinaryIO, cast, Dict, Optional, Text, Type

from absl import flags

from grr_response_core.lib import config_parser
from grr_response_core.lib import lexer
from grr_response_core.lib import package
from grr_response_core.lib import type_info
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.registry import MetaclassRegistry
from grr_response_core.lib.util import compatibility
from grr_response_core.lib.util import precondition


# Default is set in distro_entry.py to be taken from package resource.
flags.DEFINE_string(
    "config",
    package.ResourcePath("grr-response-core",
                         "install_data/etc/grr-server.yaml"),
    "Primary Configuration file to use. This is normally "
    "taken from the installed package and should rarely "
    "be specified.")

flags.DEFINE_list(
    "secondary_configs", [],
    "Secondary configuration files to load (These override "
    "previous configuration files.).")

flags.DEFINE_bool("config_help", False, "Print help about the configuration.")

flags.DEFINE_list("context", [], "Use these contexts for the config.")

flags.DEFINE_bool(
    "disallow_missing_config_definitions", False,
    "If true, we raise an error on undefined config options. "
    "This flag has an effect only on clients because it is set "
    "as True by default for server components.")

flags.DEFINE_multi_string(
    "parameter",
    default=[],
    help="Global override of config values. "
    "For example -p Database.implementation: MysqlDB",
    short_name="p")


class Error(Exception):
  """Base class for configuration exceptions."""


class ConfigFormatError(Error, type_info.TypeValueError):
  """Raised when configuration file is formatted badly."""


class ConfigWriteError(Error):
  """Raised when we failed to update the config."""


class ConfigFileNotFound(IOError, Error):
  """Raised when a config file was expected but was not found."""


class UnknownOption(Error, KeyError):
  """Raised when an unknown option was requested."""


class InterpolationError(Error):
  """Raised when a config object failed to interpolate."""


class FilterError(InterpolationError):
  """Raised when a filter fails to perform its function."""


class ConstModificationError(Error):
  """Raised when the config tries to change a constant option."""


class AlreadyInitializedError(Error):
  """Raised when an option is defined after initialization."""


class MissingConfigDefinitionError(Error):
  """Raised when a config contains an undefined config option."""


class InvalidContextError(Error):
  """Raised when an invalid context is used."""


def SetPlatformArchContext():
  """Add the running contexts to the config system."""

  # Initialize the running platform context:
  _CONFIG.AddContext("Platform:%s" % platform.system().title())

  machine = platform.uname()[4]
  if machine in ["x86_64", "AMD64", "i686"]:
    # 32 bit binaries running on AMD64 will still have a i386 arch.
    if platform.architecture()[0] == "32bit":
      arch = "i386"
    else:
      arch = "amd64"
  elif machine == "x86":
    arch = "i386"
  elif machine == "arm64":
    arch = "aarch64"
  else:
    arch = machine

  _CONFIG.AddContext("Arch:%s" % arch)


class ConfigFilter(metaclass=MetaclassRegistry):
  """A configuration filter can transform a configuration parameter."""

  name = "identity"

  # If this is set, application of the filter will not be logged - useful
  # for key material.
  sensitive_arg = False

  def Filter(self, data: Text) -> Text:
    precondition.AssertType(data, Text)
    return data


class Literal(ConfigFilter):
  """A filter which does not interpolate."""
  name = "literal"


class Lower(ConfigFilter):
  name = "lower"

  def Filter(self, data: Text) -> Text:
    precondition.AssertType(data, Text)
    return data.lower()


class Upper(ConfigFilter):
  name = "upper"

  def Filter(self, data: Text) -> Text:
    precondition.AssertType(data, Text)
    return data.upper()


class Filename(ConfigFilter):
  name = "file"

  def Filter(self, data: Text) -> Text:
    precondition.AssertType(data, Text)
    try:
      with io.open(data, "r") as fd:
        return fd.read()  # pytype: disable=bad-return-type
    except IOError as e:
      raise FilterError("%s: %s" % (data, e))


class OptionalFile(ConfigFilter):
  name = "optionalfile"

  def Filter(self, data: Text) -> Text:
    precondition.AssertType(data, Text)
    try:
      with io.open(data, "r") as fd:
        return fd.read()  # pytype: disable=bad-return-type
    except IOError:
      return ""


class FixPathSeparator(ConfigFilter):
  """A configuration filter that fixes the path speratator."""

  name = "fixpathsep"

  def Filter(self, data: Text) -> Text:
    precondition.AssertType(data, Text)
    if platform.system() == "Windows":
      # This will fix "X:\", and might add extra slashes to other paths, but
      # this is OK.
      return data.replace("\\", "\\\\")
    else:
      return data.replace("\\", "/")


class Env(ConfigFilter):
  """Interpolate environment variables."""
  name = "env"

  def Filter(self, data: Text) -> Text:
    precondition.AssertType(data, Text)
    return compatibility.Environ(data.upper(), default="")


class Expand(ConfigFilter):
  """Expands the input as a configuration parameter."""
  name = "expand"

  def Filter(self, data: Text) -> Text:
    precondition.AssertType(data, Text)
    interpolated = _CONFIG.InterpolateValue(data)
    # TODO(hanuszczak): This assertion should not be necessary but since the
    # whole configuration system is one gigantic spaghetti, we can never be sure
    # what is being returned.
    precondition.AssertType(data, Text)
    return cast(Text, interpolated)


class Flags(ConfigFilter):
  """Get the parameter from the flags."""
  name = "flags"

  def Filter(self, data: Text):
    precondition.AssertType(data, Text)
    try:
      logging.debug("Overriding config option with flags.FLAGS.%s", data)
      attribute = getattr(flags.FLAGS, data)
      # TODO(hanuszczak): Filters should always return strings and this juggling
      # should not be needed. This is just a quick hack to fix prod.
      if isinstance(attribute, bytes):
        attribute = attribute.decode("utf-8")
      elif not isinstance(attribute, Text):
        attribute = str(attribute)
      # TODO(hanuszczak): See TODO comment in the `Expand` filter.
      precondition.AssertType(attribute, Text)
      return cast(Text, attribute)
    except AttributeError as e:
      raise FilterError(e)


class Resource(ConfigFilter):
  """Locates a GRR resource that is shipped with the GRR package.

  The format of the directive is "path/to/resource@package_name". If
  package_name is not provided we use grr-resource-core by default.
  """
  name = "resource"
  default_package = "grr-response-core"

  def Filter(self, filename_spec: Text) -> Text:
    """Use pkg_resources to find the path to the required resource."""
    if "@" in filename_spec:
      file_path, package_name = filename_spec.split("@")
    else:
      file_path, package_name = filename_spec, Resource.default_package

    resource_path = package.ResourcePath(package_name, file_path)
    if resource_path is not None:
      return resource_path

    # pylint: disable=unreachable
    raise FilterError(
        "Unable to find resource %s while interpolating: " % filename_spec)
    # pylint: enable=unreachable


class ModulePath(ConfigFilter):
  """Locate the path to the specified module.

  Note: A module is either a python file (with a .py extension) or a directory
  with a __init__.py inside it. It is not the same as a resource (See Resource
  above) since a module will be installed somewhere you can import it from.

  Caveat: This will raise if the module is not a physically present on disk
  (e.g. pyinstaller bundle).
  """
  name = "module_path"

  def Filter(self, name: Text) -> Text:
    try:
      return package.ModulePath(name)
    except ImportError:
      message = (
          "Config parameter module_path expansion %r can not be imported." %
          name)

      # This exception will typically be caught by the expansion engine and
      # be silently swallowed.
      traceback.print_exc()
      logging.error(message)
      raise FilterError(message)


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

  - The following characters must be escaped by preceding them with a single \:
     - ()|
  """

  tokens = [
      # When in literal mode, only allow to escape }
      lexer.Token("Literal", r"\\[^{}]", "AppendArg", None),

      # Allow escaping of special characters
      lexer.Token(None, r"\\(.)", "Escape", None),

      # Literal sequence is %{....}. Literal states can not be nested further,
      # i.e. we include anything until the next }. It is still possible to
      # escape } if this character needs to be inserted literally.
      lexer.Token("Literal", r"\}", "EndLiteralExpression,PopState", None),
      lexer.Token("Literal", r"[^}\\]+", "AppendArg", None),
      lexer.Token(None, r"\%\{", "StartExpression,PushState", "Literal"),

      # Expansion sequence is %(....)
      lexer.Token(None, r"\%\(", "StartExpression", None),
      lexer.Token(None, r"\|([a-zA-Z_-]+)\)", "Filter", None),
      lexer.Token(None, r"\)", "ExpandArg", None),

      # Glob up as much data as possible to increase efficiency here.
      lexer.Token(None, r"[^()%{}|\\]+", "AppendArg", None),
      lexer.Token(None, r".", "AppendArg", None),
  ]

  STRING_ESCAPES = {
      "\\\\": "\\",
      "\\(": "(",
      "\\)": ")",
      "\\{": "{",
      "\\}": "}",
      "\\%": "%"
  }

  def __init__(self,
               data,
               config,
               default_section="",
               parameter=None,
               context=None):
    self.stack = [""]
    self.default_section = default_section
    self.parameter = parameter
    self.config = config
    self.context = context
    super().__init__(data)

  def Escape(self, string="", **_):
    """Support standard string escaping."""
    # Translate special escapes:
    self.stack[-1] += self.STRING_ESCAPES.get(string, string)

  def Error(self, message=None, weight=1):
    """Parse errors are fatal."""
    raise ConfigFormatError("While parsing %s: %s" % (self.parameter, message))

  def StartExpression(self, **_):
    """Start processing a new expression."""
    # Extend the stack for the new expression.
    self.stack.append("")

  def EndLiteralExpression(self, **_):
    if len(self.stack) <= 1:
      raise lexer.ParseError("Unbalanced literal sequence: Can not expand '%s'"
                             % self.processed_buffer)

    arg = self.stack.pop(-1)
    self.stack[-1] += arg

  def Filter(self, match=None, **_):
    """Filter the current expression."""
    arg = self.stack.pop(-1)

    # Filters can be specified as a comma separated list.
    for filter_name in match.group(1).split(","):
      filter_object = ConfigFilter.classes_by_name.get(filter_name)
      if filter_object is None:
        raise FilterError("Unknown filter function %r" % filter_name)

      if not filter_object.sensitive_arg:
        logging.debug("Applying filter %s for %s.", filter_name, arg)
      arg = filter_object().Filter(arg)
      precondition.AssertType(arg, Text)

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

    final_value = self.config.Get(parameter_name, context=self.context)
    if final_value is None:
      final_value = ""

    type_info_obj = (
        self.config.FindTypeInfo(parameter_name) or type_info.String())

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

  def __init__(self):
    """Initialize the configuration manager."""
    # The context is used to provide different configuration directives in
    # different situations. The context can contain any string describing a
    # different aspect of the running instance.
    self.context = []
    self.raw_data = collections.OrderedDict()
    self.files = []
    self.secondary_config_parsers = []
    self.writeback = None
    self.writeback_data = collections.OrderedDict()
    self.global_override = dict()
    self.context_descriptions = {}
    self.constants = set()
    self.valid_contexts = set()

    # This is the type info set describing all configuration
    # parameters.
    self.type_infos = type_info.TypeDescriptorSet()

    # We store the defaults here.
    self.defaults = {}

    # A cache of validated and interpolated results.
    self.FlushCache()

    self.initialized = False
    self.DeclareBuiltIns()

  def DeclareBuiltIns(self):
    """Declare built in options internal to the config system."""
    self.DEFINE_list(
        "Config.includes", [],
        "List of additional config files to include. Files are "
        "processed recursively depth-first, later values "
        "override earlier ones.")

  def __str__(self):
    # List all the files we read from.
    message = ""
    for filename in self.files:
      message += " file=\"%s\" " % filename

    return "<%s %s>" % (self.__class__.__name__, message)

  def FlushCache(self):
    self.cache = {}

  def MakeNewConfig(self):
    """Creates a new configuration option based on this one.

    Note that it is not normally possible to just instantiate the
    config object because it will have an empty set of type
    descriptors (i.e. no config options will be defined). Config
    options are normally defined at import time, and then they get
    added to the _CONFIG global in this module.

    To obtain a new configuration object, inheriting the regular
    config options, this method must be called from the global _CONFIG
    object, to make a copy.

    Returns:
      A new empty config object. which has the same parameter definitions as
      this one.
    """
    result = self.__class__()

    # We do not need to copy here since these never change.
    result.type_infos = self.type_infos
    result.defaults = self.defaults
    result.context = self.context
    result.valid_contexts = self.valid_contexts

    return result

  def CopyConfig(self):
    """Make a complete new copy of the current config.

    This includes all options as they currently are. If you want a base config
    with defaults use MakeNewConfig.

    Returns:
      A new config object with the same data as self.
    """
    newconf = self.MakeNewConfig()
    newconf.raw_data = copy.deepcopy(self.raw_data)
    newconf.files = copy.deepcopy(self.files)
    newconf.secondary_config_parsers = [
        p.Copy() for p in self.secondary_config_parsers
    ]
    newconf.writeback = copy.deepcopy(self.writeback)
    newconf.writeback_data = copy.deepcopy(self.writeback_data)
    newconf.global_override = copy.deepcopy(self.global_override)
    newconf.context_descriptions = copy.deepcopy(self.context_descriptions)
    newconf.constants = copy.deepcopy(self.constants)
    newconf.initialized = copy.deepcopy(self.initialized)
    return newconf

  def SetWriteBack(self, filename, rename_invalid_writeback=True):
    """Sets the config file which will receive any modifications.

    The main config file can be made writable, but directing all Set()
    operations into a secondary location. This secondary location will
    receive any updates and will override the options for this file.

    Args:
      filename: A filename which will receive updates. The file is parsed first
        and merged into the raw data from this object.
      rename_invalid_writeback: Whether to rename the writeback file if
        it cannot be parsed.
    """
    try:
      self.writeback = self.LoadSecondaryConfig(filename)
      self.MergeData(self.writeback.ReadData(), self.writeback_data)
    except config_parser.ReadDataError as e:
      # This means that we probably aren't installed correctly.
      logging.error("Unable to read writeback file: %s", e)
      return
    except Exception as we:  # pylint: disable=broad-except
      # Could be yaml parse error, could be some malformed parameter. Move the
      # writeback file so that we start in a clean state next run
      if rename_invalid_writeback and os.path.exists(filename):
        try:
          b = filename + ".bak"
          os.rename(filename, b)
          logging.warning("Broken writeback (%s) renamed to: %s", we, b)
        except Exception as e:  # pylint: disable=broad-except
          logging.error("Unable to rename broken writeback: %s", e)
      raise we
    logging.debug("Configuration writeback is set to %s", filename)

  def Validate(self, sections=None, parameters=None):
    """Validate sections or individual parameters.

    The GRR configuration file contains several sections, used by different
    components. Many of these components don't care about other sections. This
    method allows a component to declare in advance what sections and parameters
    it cares about, and have these validated.

    Args:
      sections: A list of sections to validate. All parameters within the
        section are validated.
      parameters: A list of specific parameters (in the format section.name) to
        validate.

    Returns:
      dict of {parameter: Exception}, where parameter is a section.name string.
    """
    if isinstance(sections, str):
      sections = [sections]

    if sections is None:
      sections = []

    if parameters is None:
      parameters = []

    validation_errors = {}
    for section in sections:
      for descriptor in self.type_infos:
        if descriptor.name.startswith(section + "."):
          try:
            self.Get(descriptor.name)
          except (Error, ValueError) as e:
            validation_errors[descriptor.name] = e

    for parameter in parameters:
      for descriptor in self.type_infos:
        if parameter == descriptor.name:
          try:
            self.Get(descriptor.name)
          except (Error, ValueError) as e:
            validation_errors[descriptor.name] = e

    return validation_errors

  def AddContext(self, context_string, description=None):
    """Adds a context string to the global configuration.

    The context conveys information about the caller of the config system and
    allows the configuration to have specialized results for different callers.

    Note that the configuration file may specify conflicting options for
    different contexts. In this case, later specified contexts (i.e. the later
    AddContext() calls) will trump the earlier specified contexts. This allows
    specialized contexts to be specified on the command line which override
    normal operating options.

    Args:
      context_string: A string which describes the global program.
      description: A description as to when this context applies.

    Raises:
      InvalidContextError: An undefined context was specified.
    """
    if context_string not in self.context:
      if context_string not in self.valid_contexts:
        raise InvalidContextError(
            "Invalid context specified: %s" % context_string)

      self.context.append(context_string)
      self.context_descriptions[context_string] = description

    self.FlushCache()

  def ContextApplied(self, context_string):
    """Return true if the context is applied."""
    return context_string in self.context

  def RemoveContext(self, context_string):
    if context_string in self.context:
      self.context.remove(context_string)
      self.context_descriptions.pop(context_string)

    self.FlushCache()

  def SetRaw(self, name, value):
    """Set the raw string without verification or escaping."""
    if self.writeback is None:
      logging.warning("Attempting to modify a read only config object.")
    if name in self.constants:
      raise ConstModificationError(
          "Attempting to modify constant value %s" % name)

    self.writeback_data[name] = value
    self.FlushCache()

  def Set(self, name, value):
    """Update the configuration option with a new value.

    Note that this forces the value to be set for all contexts. The value is
    written to the writeback location if Save() is later called.

    Args:
      name: The name of the parameter to set.
      value: The value to set it to. The value will be validated against the
        option's type descriptor.

    Raises:
      ConstModificationError: When attempting to change a constant option.
    """
    # If the configuration system has a write back location we use it,
    # otherwise we use the primary configuration object.
    if self.writeback is None:
      logging.warning("Attempting to modify a read only config object for %s.",
                      name)
    if name in self.constants:
      raise ConstModificationError(
          "Attempting to modify constant value %s" % name)

    writeback_data = self.writeback_data

    # Check if the new value conforms with the type_info.
    if value is not None:
      if isinstance(value, Text):
        value = self.EscapeString(value)

      if not compatibility.PY2 and isinstance(value, bytes):
        raise ValueError("Setting config option %s to bytes is not allowed" %
                         name)

    writeback_data[name] = value
    self.FlushCache()

  def EscapeString(self, string):
    """Escape special characters when encoding to a string."""
    return re.sub(r"([\\%){}])", r"\\\1", string)

  def Write(self):
    """Write out the updated configuration to the fd."""
    if self.writeback:
      self.writeback.SaveData(self.writeback_data)
    else:
      raise RuntimeError("Attempting to write a configuration without a "
                         "writeback location.")

  def Persist(self, config_option):
    """Stores <config_option> in the writeback."""
    if not self.writeback:
      raise RuntimeError("Attempting to write a configuration without a "
                         "writeback location.")

    writeback_raw_value = dict(self.writeback.ReadData()).get(config_option)
    raw_value = None

    for parser in [self.parser] + self.secondary_config_parsers:
      if parser == self.writeback:
        continue

      config_raw_data = dict(parser.ReadData())
      raw_value = config_raw_data.get(config_option)
      if raw_value is None:
        continue
      break

    if writeback_raw_value == raw_value:
      return

    if raw_value is None:
      return

    self.SetRaw(config_option, raw_value)
    self.Write()

  def AddOption(self, descriptor, constant=False):
    """Registers an option with the configuration system.

    Args:
      descriptor: A TypeInfoObject instance describing the option.
      constant: If this is set, the option is treated as a constant - it can be
        read at any time (before parsing the configuration) and it's an error to
        try to override it in a config file.

    Raises:
      RuntimeError: The descriptor's name must contain a . to denote the section
         name, otherwise we raise.
      AlreadyInitializedError: If the config has already been read it's too late
         to define new options.
    """
    if self.initialized:
      raise AlreadyInitializedError(
          "Config was already initialized when defining %s" % descriptor.name)

    descriptor.section = descriptor.name.split(".")[0]
    if descriptor.name in self.type_infos:
      logging.warning("Config Option %s multiply defined!", descriptor.name)

    self.type_infos.Append(descriptor)
    if constant:
      self.constants.add(descriptor.name)

    # Register this option's default value.
    self.defaults[descriptor.name] = descriptor.GetDefault()
    self.FlushCache()

  def DefineContext(self, context_name):
    self.valid_contexts.add(context_name)
    return context_name

  def FormatHelp(self):
    result = "Context: %s\n\n" % ",".join(self.context)
    for descriptor in sorted(self.type_infos, key=lambda x: x.name):
      result += descriptor.Help() + "\n"
      try:
        result += "   Current Value: %s\n" % self.Get(descriptor.name)
      except Exception as e:  # pylint:disable=broad-except
        result += "   Current Value: %s (Error: %s)\n" % (self.GetRaw(
            descriptor.name), e)
    return result

  def PrintHelp(self):
    print(self.FormatHelp())

  def MergeData(self, merge_data: Dict[Any, Any], raw_data=None):
    """Merges data read from a config file into the current config."""
    self.FlushCache()
    if raw_data is None:
      raw_data = self.raw_data

    for k, v in merge_data.items():
      # A context clause.
      if isinstance(v, dict) and k not in self.type_infos:
        if k not in self.valid_contexts:
          raise InvalidContextError("Invalid context specified: %s" % k)
        context_data = raw_data.setdefault(k, collections.OrderedDict())
        self.MergeData(v, context_data)

      else:
        # Find the descriptor for this field.
        descriptor = self.type_infos.get(k)
        if descriptor is None:
          msg = ("Missing config definition for %s. This option is likely "
                 "deprecated or renamed. Check the release notes." % k)
          if flags.FLAGS.disallow_missing_config_definitions:
            raise MissingConfigDefinitionError(msg)

        if isinstance(v, str):
          v = v.strip()

        # If we are already initialized and someone tries to modify a constant
        # value (e.g. via Set()), break loudly.
        if self.initialized and k in self.constants:
          raise ConstModificationError(
              "Attempting to modify constant value %s" % k)

        raw_data[k] = v

  def LoadSecondaryConfig(
      self,
      filename=None,
      parser=None,
      process_includes=True) -> config_parser.GRRConfigParser:
    """Loads an additional configuration file.

    The configuration system has the concept of a single Primary configuration
    file, and multiple secondary files. The primary configuration file is the
    main file that is used by the program. Any writebacks will only be made to
    the primary configuration file. Secondary files contain additional
    configuration data which will be merged into the configuration system.

    This method adds an additional configuration file.

    Args:
      filename: The configuration file that will be loaded. For example
           file:///etc/grr.conf or reg://HKEY_LOCAL_MACHINE/Software/GRR.
      parser: An optional parser can be given. In this case, the parser's data
        will be loaded directly.
      process_includes: If false, do not process any files listed in
        Config.includes configuration option.

    Returns:
      The parser used to parse this configuration source.

    Raises:
      ValueError: if both filename and parser arguments are None.
      ConfigFileNotFound: If a specified included file was not found.

    """
    if filename:
      # Maintain a stack of config file locations in loaded order.
      self.files.append(filename)

      parser = config_parser.GetParserFromPath(filename)
      logging.debug("Loading configuration from %s", filename)
      self.secondary_config_parsers.append(parser)
    elif parser is None:
      raise ValueError("Must provide either a filename or a parser.")

    clone = self.MakeNewConfig()
    clone.MergeData(parser.ReadData())
    clone.initialized = True

    if process_includes:
      for file_to_load in clone["Config.includes"]:
        # We can not include a relative file from a config which does not have
        # path.
        if not os.path.isabs(file_to_load):
          if not filename:
            raise ConfigFileNotFound(
                "While loading %s: Unable to include a relative path (%s) "
                "from a config without a filename" % (filename, file_to_load))

          # If the included path is relative, we take it as relative to the
          # current path of the config.
          file_to_load = os.path.join(os.path.dirname(filename), file_to_load)

        clone_parser = clone.LoadSecondaryConfig(file_to_load)
        # If an include file is specified but it was not found, raise an error.
        try:
          clone_parser.ReadData()
        except config_parser.ReadDataError as e:
          raise ConfigFileNotFound("Unable to load include file %s" %
                                   file_to_load) from e

    self.MergeData(clone.raw_data)
    self.files.extend(clone.files)

    return parser

  # TODO(hanuszczak): Magic method with a lot of mutually exclusive switches. It
  # should be split into multiple methods instead.
  def Initialize(
      self,
      filename: Optional[str] = None,
      data: Optional[str] = None,
      fd: Optional[BinaryIO] = None,
      reset: bool = True,
      must_exist: bool = False,
      process_includes: bool = True,
      parser: Type[
          config_parser.GRRConfigParser] = config_parser.IniConfigFileParser):
    """Initializes the config manager.

    This method is used to add more config options to the manager. The config
    can be given as one of the parameters as described in the Args section.

    Args:
      filename: The name of the configuration file to use.
      data: The configuration given directly as a long string of data.
      fd: A file descriptor of a configuration file.
      reset: If true, the previous configuration will be erased.
      must_exist: If true the data source must exist and be a valid
        configuration file, or we raise an exception.
      process_includes: If false, do not process any files listed in
        Config.includes configuration option.
      parser: The parser class to use (i.e. the format of the file). If not
        specified guess from the filename.

    Raises:
      RuntimeError: No configuration was passed in any of the parameters.

      ConfigFormatError: Raised when the configuration file is invalid or does
        not exist..
    """
    self.FlushCache()
    if reset:
      # Clear previous configuration.
      self.raw_data = collections.OrderedDict()
      self.writeback_data = collections.OrderedDict()
      self.writeback = None
      self.initialized = False

    if fd is not None:
      if issubclass(parser, config_parser.GRRConfigFileParser):
        self.parser = self.LoadSecondaryConfig(
            parser=config_parser.FileParserDataWrapper(fd.read(), parser("")),
            process_includes=process_includes)
      else:
        raise TypeError("Trying to read from FD with a non-file parser.")

    elif filename is not None:
      self.parser = self.LoadSecondaryConfig(
          filename, process_includes=process_includes)
      try:
        self.parser.ReadData()
      except config_parser.ReadDataError as e:
        if must_exist:
          raise ConfigFormatError("Unable to parse config file %s" %
                                  filename) from e

    elif data is not None:
      if issubclass(parser, config_parser.GRRConfigFileParser):
        self.parser = self.LoadSecondaryConfig(
            parser=config_parser.FileParserDataWrapper(
                data.encode("utf-8"), parser("")),
            process_includes=process_includes)
      else:
        raise TypeError("Trying to parse bytes with a non-file parser.")

    elif must_exist:
      raise RuntimeError("Registry path not provided.")

    self.initialized = True

  def __getitem__(self, name):
    """Retrieve a configuration value after suitable interpolations."""
    if name not in self.type_infos:
      raise UnknownOption("Config parameter %s not known." % name)

    return self.Get(name)

  def GetRaw(self, name, context=None, default=utils.NotAValue):
    """Get the raw value without interpolations."""
    if context is None:
      context = self.context

    # Getting a raw value is pretty cheap so we won't bother with the cache
    # here.
    _, value = self._GetValue(name, context, default=default)
    return value

  def Get(self, name, default=utils.NotAValue, context=None):
    """Get the value contained  by the named parameter.

    This method applies interpolation/escaping of the named parameter and
    retrieves the interpolated value.

    Args:
      name: The name of the parameter to retrieve. This should be in the format
        of "Section.name"
      default: If retrieving the value results in an error, return this default.
      context: A list of context strings to resolve the configuration. This is a
        set of roles the caller is current executing with. For example (client,
        windows). If not specified we take the context from the current thread's
        TLS stack.

    Returns:
      The value of the parameter.
    Raises:
      ConfigFormatError: if verify=True and the config doesn't validate.
      RuntimeError: if a value is retrieved before the config is initialized.
      ValueError: if a bad context is passed.
    """
    if not self.initialized:
      if name not in self.constants:
        raise RuntimeError("Error while retrieving %s: "
                           "Configuration hasn't been initialized yet." % name)
    if context:
      # Make sure it's not just a string and is iterable.
      if (isinstance(context, str) or not isinstance(context, abc.Iterable)):
        raise ValueError("context should be a list, got %r" % context)

    calc_context = context

    # Only use the cache if possible.
    cache_key = (name, tuple(context or ()))
    if default is utils.NotAValue and cache_key in self.cache:
      return self.cache[cache_key]

    # Use a default global context if context is not provided.
    if context is None:
      calc_context = self.context

    type_info_obj = self.FindTypeInfo(name)
    _, return_value = self._GetValue(
        name, context=calc_context, default=default)

    # If we returned the specified default, we just return it here.
    if return_value is default:
      return default

    try:
      return_value = self.InterpolateValue(
          return_value,
          default_section=name.split(".")[0],
          type_info_obj=type_info_obj,
          context=calc_context)
    except (lexer.ParseError, ValueError) as e:
      # We failed to parse the value, but a default was specified, so we just
      # return that.
      if default is not utils.NotAValue:
        return default

      raise ConfigFormatError("While parsing %s: %s" % (name, e))

    try:
      new_value = type_info_obj.Validate(return_value)
      if new_value is not None:
        # Update the stored value with the valid data.
        return_value = new_value
    except ValueError:
      if default is not utils.NotAValue:
        return default

      raise

    # Cache the value for next time.
    if default is utils.NotAValue:
      self.cache[cache_key] = return_value

    return return_value

  def _ResolveContext(self, context, name, raw_data, path=None):
    """Returns the config options active under this context."""
    if path is None:
      path = []

    for element in context:
      if element not in self.valid_contexts:
        raise InvalidContextError("Invalid context specified: %s" % element)

      if element in raw_data:
        context_raw_data = raw_data[element]

        # TODO(hanuszczak): Investigate why pytype complains here (probably for
        # valid reasons, because this code does not looks like something well-
        # typed).
        value = context_raw_data.get(name)  # pytype: disable=attribute-error
        if value is not None:
          if isinstance(value, str):
            value = value.strip()

          yield context_raw_data, value, path + [element]

        # Recurse into the new context configuration.
        for context_raw_data, value, new_path in self._ResolveContext(
            context, name, context_raw_data, path=path + [element]):
          yield context_raw_data, value, new_path

  def _GetValue(self, name, context, default=utils.NotAValue):
    """Search for the value based on the context."""
    container = self.defaults

    # The caller provided a default value.
    if default is not utils.NotAValue:
      value = default

    # Take the default from the definition.
    elif name in self.defaults:
      value = self.defaults[name]

    else:
      raise UnknownOption("Option %s not defined." % name)

    # We resolve the required key with the default raw data, and then iterate
    # over all elements in the context to see if there are overriding context
    # configurations.
    new_value = self.raw_data.get(name)
    if new_value is not None:
      value = new_value
      container = self.raw_data

    # Now check for any contexts. We enumerate all the possible resolutions and
    # sort by their path length. The last one will be the match with the deepest
    # path (i.e .the most specific match).
    matches = list(self._ResolveContext(context, name, self.raw_data))

    if matches:
      # Sort by the length of the path - longest match path will be at the end.
      matches.sort(key=lambda x: len(x[2]))
      value = matches[-1][1]
      container = matches[-1][0]

      if (len(matches) >= 2 and len(matches[-1][2]) == len(matches[-2][2]) and
          matches[-1][2] != matches[-2][2] and
          matches[-1][1] != matches[-2][1]):
        # This warning specifies that there is an ambiguous match, the config
        # attempts to find the most specific value e.g. if you have a value
        # for X.y in context A,B,C, and a value for X.y in D,B it should choose
        # the one in A,B,C. This warning is for if you have a value in context
        # A,B and one in A,C. The config doesn't know which one to pick so picks
        # one and displays this warning.
        logging.warning(
            "Ambiguous configuration for key %s: "
            "Contexts of equal length: %s (%s) and %s (%s)", name,
            matches[-1][2], matches[-1][1], matches[-2][2], matches[-2][1])

    # If there is a writeback location this overrides any previous
    # values.
    if self.writeback_data:
      new_value = self.writeback_data.get(name)
      if new_value is not None:
        value = new_value
        container = self.writeback_data

    # Allow the global override to force an option value.
    if name in self.global_override:
      return self.global_override, self.global_override[name]

    return container, value

  def FindTypeInfo(self, name):
    """Search for a type_info instance which describes this key."""
    result = self.type_infos.get(name)
    if result is None:
      # Not found, assume string.
      result = type_info.String(name=name, default="")

    return result

  def InterpolateValue(self,
                       value,
                       type_info_obj=type_info.String(),
                       default_section=None,
                       context=None):
    """Interpolate the value and parse it with the appropriate type."""
    # It is only possible to interpolate strings...
    if isinstance(value, Text):
      try:
        value = StringInterpolator(
            value,
            self,
            default_section=default_section,
            parameter=type_info_obj.name,
            context=context).Parse()
      except InterpolationError as e:
        # TODO(hanuszczak): This is a quick hack to not refactor too much while
        # working on Python 3 compatibility. But this is bad and exceptions
        # should not be used like this.
        message = "{cause}: {detail}".format(cause=e, detail=value)
        raise type(e)(message)

      # Parse the data from the string.
      value = type_info_obj.FromString(value)

    # ... and lists of strings.
    if isinstance(value, list):
      value = [
          self.InterpolateValue(
              v, default_section=default_section, context=context)
          for v in value
      ]

    return value

  def GetSections(self):
    result = set()
    for descriptor in self.type_infos:
      result.add(descriptor.section)

    return result

  def MatchBuildContext(self,
                        target_os,
                        target_arch,
                        target_package,
                        context=None):
    """Return true if target_platforms matches the supplied parameters.

    Used by buildanddeploy to determine what clients need to be built.

    Args:
      target_os: which os we are building for in this run (linux, windows,
        darwin)
      target_arch: which arch we are building for in this run (i386, amd64)
      target_package: which package type we are building (exe, dmg, deb, rpm)
      context: config_lib context

    Returns:
      bool: True if target_platforms spec matches parameters.
    """
    for spec in self.Get("ClientBuilder.target_platforms", context=context):
      spec_os, arch, package_name = spec.split("_")
      if (spec_os == target_os and arch == target_arch and
          package_name == target_package):
        return True
    return False

  # pylint: disable=g-bad-name,redefined-builtin
  def DEFINE_bool(self, name, default, help, constant=False):
    """A helper for defining boolean options."""
    self.AddOption(
        type_info.Bool(name=name, default=default, description=help),
        constant=constant)

  def DEFINE_float(self, name, default, help, constant=False):
    """A helper for defining float options."""
    self.AddOption(
        type_info.Float(name=name, default=default, description=help),
        constant=constant)

  def DEFINE_integer(self, name, default, help, constant=False):
    """A helper for defining integer options."""
    self.AddOption(
        type_info.Integer(name=name, default=default, description=help),
        constant=constant)

  def DEFINE_string(self, name, default, help, constant=False):
    """A helper for defining string options."""
    self.AddOption(
        type_info.String(name=name, default=default or "", description=help),
        constant=constant)

  def DEFINE_choice(self, name, default, choices, help, constant=False):
    """A helper for defining choice string options."""
    self.AddOption(
        type_info.Choice(
            name=name, default=default, choices=choices, description=help),
        constant=constant)

  def DEFINE_multichoice(self, name, default, choices, help, constant=False):
    """Choose multiple options from a list."""
    self.AddOption(
        type_info.MultiChoice(
            name=name, default=default, choices=choices, description=help),
        constant=constant)

  def DEFINE_integer_list(self, name, default, help, constant=False):
    """A helper for defining lists of integer options."""
    self.AddOption(
        type_info.List(
            name=name,
            default=default,
            description=help,
            validator=type_info.Integer()),
        constant=constant)

  def DEFINE_list(self, name, default, help, constant=False):
    """A helper for defining lists of strings options."""
    self.AddOption(
        type_info.List(
            name=name,
            default=default,
            description=help,
            validator=type_info.String()),
        constant=constant)

  def DEFINE_constant_string(self, name, default, help):
    """A helper for defining constant strings."""
    self.AddOption(
        type_info.String(name=name, default=default or "", description=help),
        constant=True)

  def DEFINE_semantic_value(self, semantic_type, name, default=None, help=""):
    if issubclass(semantic_type, rdf_structs.RDFStruct):
      raise ValueError("DEFINE_semantic_value should be used for types based "
                       "on primitives.")

    self.AddOption(
        type_info.RDFValueType(
            rdfclass=semantic_type,
            name=name,
            default=default,
            description=help))

  def DEFINE_semantic_enum(self,
                           enum_container: rdf_structs.EnumContainer,
                           name: str,
                           default: Optional[rdf_structs.EnumNamedValue] = None,
                           help: str = "") -> None:
    if not isinstance(enum_container, rdf_structs.EnumContainer):
      raise ValueError("enum_container must be an EnumContainer.")

    self.AddOption(
        type_info.RDFEnumType(
            enum_container=enum_container,
            name=name,
            default=default,
            description=help))

  def DEFINE_semantic_struct(self, semantic_type, name, default=None, help=""):
    if not issubclass(semantic_type, rdf_structs.RDFStruct):
      raise ValueError("DEFINE_semantic_struct should be used for types based "
                       "on structs.")

    self.AddOption(
        type_info.RDFStructDictType(
            rdfclass=semantic_type,
            name=name,
            default=default,
            description=help))

  def DEFINE_context(self, name):
    return self.DefineContext(name)


# pylint: enable=g-bad-name

# Global config object. This object is not supposed to be used directly,
# since when used from config_lib, it's not going to have all the GRR
# config options registered.
#
# grr.config.CONFIG should be used instead - using grr.config.CONFIG
# guarantees that all configuration options and filters are properly
# imported.
_CONFIG = GrrConfigManager()


# pylint: disable=g-bad-name,redefined-builtin
def DEFINE_bool(name, default, help):
  """A helper for defining boolean options."""
  _CONFIG.DEFINE_bool(name, default, help)


def DEFINE_float(name, default, help):
  """A helper for defining float options."""
  _CONFIG.DEFINE_float(name, default, help)


def DEFINE_integer(name, default, help):
  """A helper for defining integer options."""
  _CONFIG.DEFINE_integer(name, default, help)


def DEFINE_boolean(name, default, help):
  """A helper for defining boolean options."""
  _CONFIG.DEFINE_bool(name, default, help)


def DEFINE_string(name, default, help):
  """A helper for defining string options."""
  _CONFIG.DEFINE_string(name, default, help)


def DEFINE_choice(name, default, choices, help):
  """A helper for defining choice string options."""
  _CONFIG.DEFINE_choice(name, default, choices, help)


def DEFINE_multichoice(name, default, choices, help):
  """Choose multiple options from a list."""
  _CONFIG.DEFINE_multichoice(name, default, choices, help)


def DEFINE_integer_list(name, default, help):
  """A helper for defining lists of integer options."""
  _CONFIG.DEFINE_integer_list(name, default, help)


def DEFINE_list(name, default, help):
  """A helper for defining lists of strings options."""
  _CONFIG.DEFINE_list(name, default, help)


def DEFINE_semantic_value(semantic_type, name, default=None, help=""):
  _CONFIG.DEFINE_semantic_value(semantic_type, name, default=default, help=help)


def DEFINE_semantic_enum(semantic_enum: rdf_structs.EnumContainer,
                         name: str,
                         default: Optional[rdf_structs.EnumNamedValue] = None,
                         help: str = "") -> None:
  _CONFIG.DEFINE_semantic_enum(semantic_enum, name, default=default, help=help)


def DEFINE_semantic_struct(semantic_type, name, default=None, help=""):
  _CONFIG.DEFINE_semantic_struct(
      semantic_type, name, default=default, help=help)


def DEFINE_option(type_descriptor):
  _CONFIG.AddOption(type_descriptor)


def DEFINE_constant_string(name, default, help):
  """A helper for defining constant strings."""
  _CONFIG.DEFINE_constant_string(name, default, help)


def DEFINE_context(name):
  return _CONFIG.DefineContext(name)


# pylint: enable=g-bad-name


def LoadConfig(config_obj,
               config_file=None,
               config_fd=None,
               secondary_configs=None,
               contexts=None,
               reset=False,
               parser=config_parser.IniConfigFileParser):
  """Initialize a ConfigManager with the specified options.

  Args:
    config_obj: The ConfigManager object to use and update. If None, one will be
      created.
    config_file: Filename to read the config from.
    config_fd: A file-like object to read config data from.
    secondary_configs: A list of secondary config URLs to load.
    contexts: Add these contexts to the config object.
    reset: Completely wipe previous config before doing the load.
    parser: Specify which parser to use.

  Returns:
    The resulting config object. The one passed in, unless None was specified.
  """
  if config_obj is None or reset:
    # Create a new config object.
    config_obj = _CONFIG.MakeNewConfig()

  # Initialize the config with a filename or file like object.
  if config_file is not None:
    config_obj.Initialize(filename=config_file, must_exist=True, parser=parser)
  elif config_fd is not None:
    config_obj.Initialize(fd=config_fd, parser=parser)

  # Load all secondary files.
  if secondary_configs:
    for config_file in secondary_configs:
      config_obj.LoadSecondaryConfig(config_file)

  if contexts:
    for context in contexts:
      config_obj.AddContext(context)

  return config_obj


def ParseConfigCommandLine(rename_invalid_writeback=True):
  """Parse all the command line options which control the config system."""
  # The user may specify the primary config file on the command line.
  if flags.FLAGS.config:
    _CONFIG.Initialize(filename=flags.FLAGS.config, must_exist=True)
  else:
    raise RuntimeError("A config file is not specified.")

  # Allow secondary configuration files to be specified.
  if flags.FLAGS.secondary_configs:
    for config_file in flags.FLAGS.secondary_configs:
      _CONFIG.LoadSecondaryConfig(config_file)

  # Allow individual options to be specified as global overrides.
  for statement in flags.FLAGS.parameter:
    if "=" not in statement:
      raise RuntimeError("statement %s on command line not valid." % statement)

    name, value = statement.split("=", 1)
    _CONFIG.global_override[name] = value

  # Load additional contexts from the command line.
  for context in flags.FLAGS.context:
    if context:
      _CONFIG.AddContext(context)

  if _CONFIG["Config.writeback"]:
    _CONFIG.SetWriteBack(
        _CONFIG["Config.writeback"],
        rename_invalid_writeback=rename_invalid_writeback)

  # Does the user want to dump help? We do this after the config system is
  # initialized so the user can examine what we think the value of all the
  # parameters are.
  if flags.FLAGS.config_help:
    print("Configuration overview.")

    _CONFIG.PrintHelp()
    sys.exit(0)
