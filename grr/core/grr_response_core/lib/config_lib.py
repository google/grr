#!/usr/bin/env python
"""This is the GRR config management code.

This handles opening and parsing of config files.
"""
from __future__ import absolute_import
from __future__ import division

from __future__ import print_function
from __future__ import unicode_literals

import collections
import copy
import errno
import io
import logging
import os
import platform
import re
import sys
import traceback


import configparser
from future.utils import iteritems
from future.utils import itervalues
from future.utils import string_types
from future.utils import with_metaclass
import yaml

from grr_response_core.lib import flags
from grr_response_core.lib import lexer
from grr_response_core.lib import package
from grr_response_core.lib import registry
from grr_response_core.lib import type_info
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import structs as rdf_structs
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

flags.DEFINE_bool("disallow_missing_config_definitions", False,
                  "If true, we raise an error on undefined config options.")

flags.DEFINE_multi_string(
    "p",
    "parameter",
    help="Global override of config values. "
    "For example -p DataStore.implementation=MySQLDataStore")


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

  def AddContext(self, message):
    self.message = "%s %s" % (self.message, message)
    self.args = (self.message,)


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
  else:
    arch = machine

  _CONFIG.AddContext("Arch:%s" % arch)


class ConfigFilter(with_metaclass(registry.MetaclassRegistry, object)):
  """A configuration filter can transform a configuration parameter."""

  name = "identity"

  # If this is set, application of the filter will not be logged - useful
  # for key material.
  sensitive_arg = False

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
    try:
      return open(data, "rb").read(1024000)
    except IOError as e:
      raise FilterError("%s: %s" % (data, e))


class FixPathSeparator(ConfigFilter):
  name = "fixpathsep"

  def Filter(self, data):
    if platform.system() == "Windows":
      # This will fix "X:\", and might add extra slashes to other paths, but
      # this is OK.
      return data.replace("\\", "\\\\")
    else:
      return data.replace("\\", "/")


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
    return _CONFIG.InterpolateValue(data)


class Flags(ConfigFilter):
  """Get the parameter from the flags."""
  name = "flags"

  def Filter(self, data):
    try:
      logging.debug("Overriding config option with flags.FLAGS.%s", data)
      return getattr(flags.FLAGS, data)
    except AttributeError as e:
      raise FilterError(e)


class Resource(ConfigFilter):
  """Locates a GRR resource that is shipped with the GRR package.

  The format of the directive is "path/to/resource@package_name". If
  package_name is not provided we use grr-resource-core by default.
  """
  name = "resource"
  default_package = "grr-response-core"

  def Filter(self, filename_spec):
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

  def Filter(self, name):
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


class GRRConfigParser(with_metaclass(registry.MetaclassRegistry, object)):
  """The base class for all GRR configuration parsers."""

  # Configuration parsers are named. This name is used to select the correct
  # parser from the --config parameter which is interpreted as a filename,
  # except for files of the form reg://XXXX where XXXX is the key name.
  name = None

  # Set to True by the parsers if the file exists.
  parsed = None

  def RawData(self):
    """Convert the file to a more suitable data structure.

    Returns:
    The standard data format from this method is for example:

    {
     name: default_value;
     name2: default_value2;

     "Context1": {
         name: value,
         name2: value,

         "Nested Context" : {
           name: value;
         };
      },
     "Context2": {
         name: value,
      }
    }

    i.e. raw_data is an OrderedYamlDict() with keys representing parameter names
    and values representing values. Contexts are represented by nested
    OrderedYamlDict() structures with similar format.

    Note that support for contexts is optional and depends on the config file
    format. If contexts are not supported, a flat OrderedYamlDict() is returned.
    """


class ConfigFileParser(configparser.RawConfigParser, GRRConfigParser):
  """A parser for ini style config files."""

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
      fd = io.StringIO(data)
      # TODO(hanuszczak): Incorrect typings (`StringIO` is `IO`).
      self.parsed = self.readfp(fd)  # pytype: disable=wrong-arg-types
      self.filename = filename
    else:
      raise Error("Filename not specified.")

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
      fd = os.open(self.filename, mode, 0o600)
      with os.fdopen(fd, "wb") as config_file:
        self.SaveDataToFD(raw_data, config_file)

    except OSError as e:
      logging.warn("Unable to write config file %s: %s.", self.filename, e)

  def SaveDataToFD(self, raw_data, fd):
    """Merge the raw data with the config file and store it."""
    for key, value in iteritems(raw_data):
      # TODO(hanuszczak): Incorrect type specification for `set`.
      # pytype: disable=wrong-arg-types
      self.set("", key, value=value)
      # pytype: enable=wrong-arg-types

    self.write(fd)

  def RawData(self):
    raw_data = OrderedYamlDict()
    for section in self.sections():
      for key, value in self.items(section):
        raw_data[".".join([section, key])] = value

    return raw_data


# TODO(user): Move this class to utils.py
class OrderedYamlDict(yaml.YAMLObject, collections.OrderedDict):
  """A class which produces an ordered dict."""
  yaml_tag = "tag:yaml.org,2002:map"

  # pylint:disable=g-bad-name
  @classmethod
  def to_yaml(cls, dumper, data):
    value = []
    node = yaml.nodes.MappingNode(cls.yaml_tag, value)
    for key, item in iteritems(data):
      # Keys are forced to be strings and not unicode.
      node_key = dumper.represent_data(utils.SmartStr(key))
      node_value = dumper.represent_data(item)
      value.append((node_key, node_value))

    return node

  @classmethod
  def construct_mapping(cls, loader, node, deep=False):
    """Based on yaml.loader.BaseConstructor.construct_mapping."""

    if not isinstance(node, yaml.MappingNode):
      raise yaml.loader.ConstructorError(
          None, None, "expected a mapping node, but found %s" % node.id,
          node.start_mark)

    mapping = OrderedYamlDict()
    for key_node, value_node in node.value:
      key = loader.construct_object(key_node, deep=deep)
      try:
        hash(key)
      except TypeError as exc:
        raise yaml.loader.ConstructorError(
            "while constructing a mapping", node.start_mark,
            "found unacceptable key (%s)" % exc, key_node.start_mark)
      value = loader.construct_object(value_node, deep=deep)
      mapping[key] = value

    return mapping

  @classmethod
  def from_yaml(cls, loader, node):
    """Parse the yaml file into an OrderedDict so we can preserve order."""
    fields = cls.construct_mapping(loader, node, deep=True)
    result = cls()
    for k, v in iteritems(fields):
      result[k] = v

    return result

  # pylint:enable=g-bad-name


  # Ensure Yaml does not emit tags for unicode objects.
  # http://pyyaml.org/ticket/11
def UnicodeRepresenter(dumper, value):
  return dumper.represent_scalar(u"tag:yaml.org,2002:str", value)


yaml.add_representer(unicode, UnicodeRepresenter)


class YamlParser(GRRConfigParser):
  """A parser for yaml style config files."""

  name = "yaml"

  # TODO(hanuszczak): This constructor has unnecessary complicated logic and too
  # much branching. It should be simplified.
  def __init__(self, filename=None, data=None, fd=None):
    super(YamlParser, self).__init__()

    if fd:
      self.fd = fd
      try:
        self.filename = fd.name
      except AttributeError:
        self.filename = None
      self.parsed = _ParseYamlFromFile(fd)

    elif filename:
      self.filename = filename

      try:
        self.parsed = _ParseYamlFromFilepath(filename)
      except IOError as e:
        if e.errno == errno.EACCES:
          # Specifically catch access denied errors, this usually indicates the
          # user wanted to read the file, and it existed, but they lacked the
          # permissions.
          raise IOError(e)
        else:
          self.parsed = OrderedYamlDict()
      except OSError:
        self.parsed = OrderedYamlDict()

    elif data is not None:
      self.filename = filename
      fd = io.StringIO(data)
      self.parsed = _ParseYamlFromFile(fd)
    else:
      raise Error("Filename not specified.")

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
      fd = os.open(self.filename, mode, 0o600)
      with os.fdopen(fd, "wb") as config_file:
        self.SaveDataToFD(raw_data, config_file)

    except OSError as e:
      logging.warn("Unable to write config file %s: %s.", self.filename, e)

  def SaveDataToFD(self, raw_data, fd):
    """Merge the raw data with the config file and store it."""
    yaml.dump(raw_data, fd, default_flow_style=False)

  def _RawData(self, data):
    """Convert data to common format.

    Configuration options are normally grouped by the functional component which
    define it (e.g. Logging.path is the path parameter for the logging
    subsystem). However, sometimes it is more intuitive to write the config as a
    flat string (e.g. Logging.path). In this case we group all the flat strings
    in their respective sections and create the sections automatically.

    Args:
      data: A dict of raw data.

    Returns:
      a dict in common format. Any keys in the raw data which have a "." in them
      are separated into their own sections. This allows the config to be
      written explicitly in dot notation instead of using a section.
    """
    if not isinstance(data, dict):
      return data

    result = OrderedYamlDict()
    for k, v in iteritems(data):
      result[k] = self._RawData(v)

    return result

  def RawData(self):
    return self._RawData(self.parsed)


def _ParseYamlFromFilepath(filepath):
  """Parses a YAML file at specified path."""
  with io.open(filepath, "r") as filedesc:
    return _ParseYamlFromFile(filedesc)


def _ParseYamlFromFile(filedesc):
  """Parses given YAML file."""

  def StrConstructor(loader, node):
    precondition.AssertType(node.value, unicode)
    return loader.construct_scalar(node)

  # This makes sure that all string literals in the YAML file are parsed as an
  # `unicode` object rather than `bytes` instances.
  yaml.add_constructor("tag:yaml.org,2002:str", StrConstructor)

  # Note that we do not use safe_load because we trust the config file (if an
  # attacker can write on the config file they can already get code
  # execution). Using safe_load will break when loading a yaml file written
  # with dump().
  return yaml.load(filedesc) or OrderedYamlDict()


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
    super(StringInterpolator, self).__init__(data)

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
    self.raw_data = OrderedYamlDict()
    self.files = []
    self.secondary_config_parsers = []
    self.writeback = None
    self.writeback_data = OrderedYamlDict()
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
    newconf.secondary_config_parsers = copy.deepcopy(
        self.secondary_config_parsers)
    newconf.writeback = copy.deepcopy(self.writeback)
    newconf.writeback_data = copy.deepcopy(self.writeback_data)
    newconf.global_override = copy.deepcopy(self.global_override)
    newconf.context_descriptions = copy.deepcopy(self.context_descriptions)
    newconf.constants = copy.deepcopy(self.constants)
    newconf.initialized = copy.deepcopy(self.initialized)
    return newconf

  def SetWriteBack(self, filename):
    """Sets the config file which will receive any modifications.

    The main config file can be made writable, but directing all Set()
    operations into a secondary location. This secondary location will
    receive any updates and will override the options for this file.

    Args:
      filename: A filename which will receive updates. The file is parsed first
        and merged into the raw data from this object.
    """
    try:
      self.writeback = self.LoadSecondaryConfig(filename)
      self.MergeData(self.writeback.RawData(), self.writeback_data)
    except IOError as e:
      # This means that we probably aren't installed correctly.
      logging.error("Unable to read writeback file: %s", e)
      return
    except Exception as we:  # pylint: disable=broad-except
      # Could be yaml parse error, could be some malformed parameter. Move the
      # writeback file so that we start in a clean state next run
      if os.path.exists(filename):
        try:
          b = filename + ".bak"
          os.rename(filename, b)
          logging.warn("Broken writeback (%s) renamed to: %s", we, b)
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
    if isinstance(sections, string_types):
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
      logging.warn("Attempting to modify a read only config object.")
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
      logging.warn("Attempting to modify a read only config object for %s.",
                   name)
    if name in self.constants:
      raise ConstModificationError(
          "Attempting to modify constant value %s" % name)

    writeback_data = self.writeback_data

    # Check if the new value conforms with the type_info.
    if value is not None:
      if isinstance(value, unicode):
        value = self.EscapeString(value)

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

  def WriteToFD(self, fd):
    """Write out the updated configuration to the fd."""
    if self.writeback:
      self.writeback.SaveDataToFD(self.writeback_data, fd)
    else:
      raise RuntimeError("Attempting to write a configuration without a "
                         "writeback location.")

  def Persist(self, config_option):
    """Stores <config_option> in the writeback."""
    if not self.writeback:
      raise RuntimeError("Attempting to write a configuration without a "
                         "writeback location.")

    writeback_raw_value = dict(self.writeback.RawData()).get(config_option)
    for parser in [self.parser] + self.secondary_config_parsers:
      if parser == self.writeback:
        continue

      config_raw_data = dict(parser.RawData())
      raw_value = config_raw_data.get(config_option)
      if raw_value is None:
        continue
      break

    if writeback_raw_value == raw_value:
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

  default_descriptors = {
      str: type_info.String,
      unicode: type_info.String,
      int: type_info.Integer,
      list: type_info.List,
  }

  def MergeData(self, merge_data, raw_data=None):
    """Merges data read from a config file into the current config."""
    self.FlushCache()
    if raw_data is None:
      raw_data = self.raw_data

    for k, v in iteritems(merge_data):
      # A context clause.
      if isinstance(v, OrderedYamlDict) and k not in self.type_infos:
        if k not in self.valid_contexts:
          raise InvalidContextError("Invalid context specified: %s" % k)
        context_data = raw_data.setdefault(k, OrderedYamlDict())
        self.MergeData(v, context_data)

      else:
        # Find the descriptor for this field.
        descriptor = self.type_infos.get(k)
        if descriptor is None:
          msg = ("Missing config definition for %s. This option is likely "
                 "deprecated or renamed. Check the release notes." % k)
          if flags.FLAGS.disallow_missing_config_definitions:
            raise MissingConfigDefinitionError(msg)

        if isinstance(v, string_types):
          v = v.strip()

        # If we are already initialized and someone tries to modify a constant
        # value (e.g. via Set()), break loudly.
        if self.initialized and k in self.constants:
          raise ConstModificationError(
              "Attempting to modify constant value %s" % k)

        raw_data[k] = v

  def GetParserFromFilename(self, path):
    """Returns the appropriate parser class from the filename."""
    # Find the configuration parser.
    handler_name = path.split("://")[0]
    for parser_cls in itervalues(GRRConfigParser.classes):
      if parser_cls.name == handler_name:
        return parser_cls

    # Handle the filename.
    extension = os.path.splitext(path)[1]
    if extension in [".yaml", ".yml"]:
      return YamlParser

    return ConfigFileParser

  def LoadSecondaryConfig(self, filename=None, parser=None):
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

    Returns:
      The parser used to parse this configuration source.

    Raises:
      ValueError: if both filename and parser arguments are None.
      ConfigFileNotFound: If a specified included file was not found.

    """
    if filename:
      # Maintain a stack of config file locations in loaded order.
      self.files.append(filename)

      parser_cls = self.GetParserFromFilename(filename)
      parser = parser_cls(filename=filename)
      logging.debug("Loading configuration from %s", filename)
      self.secondary_config_parsers.append(parser)
    elif parser is None:
      raise ValueError("Must provide either a filename or a parser.")

    clone = self.MakeNewConfig()
    clone.MergeData(parser.RawData())
    clone.initialized = True

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
      if not clone_parser.parsed:
        raise ConfigFileNotFound(
            "Unable to load include file %s" % file_to_load)

    self.MergeData(clone.raw_data)
    self.files.extend(clone.files)

    return parser

  # TODO(hanuszczak): Magic method with a lot of mutually exclusive switches. It
  # should be split into multiple methods instead.
  def Initialize(self,
                 filename=None,
                 data=None,
                 fd=None,
                 reset=True,
                 must_exist=False,
                 parser=ConfigFileParser):
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
      self.raw_data = OrderedYamlDict()
      self.writeback_data = OrderedYamlDict()
      self.writeback = None
      self.initialized = False

    if fd is not None:
      self.parser = self.LoadSecondaryConfig(parser=parser(fd=fd))

    elif filename is not None:
      self.parser = self.LoadSecondaryConfig(filename)
      if must_exist and not self.parser.parsed:
        raise ConfigFormatError("Unable to parse config file %s" % filename)

    elif data is not None:
      self.parser = self.LoadSecondaryConfig(parser=parser(data=data))

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

    # Getting a raw value is pretty cheap so we wont bother with the cache here.
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
      if (isinstance(context, string_types) or
          not isinstance(context, collections.Iterable)):
        raise ValueError("context should be a list, got %s" % str(context))

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

        value = context_raw_data.get(name)
        if value is not None:
          if isinstance(value, string_types):
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
        logging.warn(
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
    if isinstance(value, unicode):
      try:
        value = StringInterpolator(
            value,
            self,
            default_section=default_section,
            parameter=type_info_obj.name,
            context=context).Parse()
      except InterpolationError as e:
        e.AddContext(value)
        raise

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
               parser=ConfigFileParser):
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


def ParseConfigCommandLine():
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
    _CONFIG.SetWriteBack(_CONFIG["Config.writeback"])

  # Does the user want to dump help? We do this after the config system is
  # initialized so the user can examine what we think the value of all the
  # parameters are.
  if flags.FLAGS.config_help:
    print("Configuration overview.")

    _CONFIG.PrintHelp()
    sys.exit(0)
