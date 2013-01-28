#!/usr/bin/env python
"""This is the GRR config management code.

This handles opening and parsing of config files.
"""

import ConfigParser
import re
import stat

from grr.client import conf as flags
import logging
from grr.lib import registry

FLAGS = flags.FLAGS

flags.DEFINE_string("config", "/etc/grr/grr-server.conf",
                    "Configuration file to use.")


class ConfigFormatError(Exception):
  """Raised when configuration file is formatted badly."""


class ConfigManager(ConfigParser.SafeConfigParser):
  """A ConfigParser implementation with GRR specific features.

  Key Additional Features over SafeConfigParser:
    - Allows getters and setters using dot notation
      e.g. conf["ServerFlags.server_key"]
    - Basic validation of formatting
    - Section inheritance via @inherit_from_section option
  """

  REQUIRED_SECTIONS = ["ServerFlags"]

  def __init__(self):
    """Initialize the GRR configuation manager."""
    # Cannot use super() here
    ConfigParser.SafeConfigParser.__init__(self)
    for section in self.REQUIRED_SECTIONS:
      self.add_section(section)

    # List of sections that should be used as FLAGS.
    # TODO(user): Remove once new CONFIG type info is in place.
    self.flag_sections = []

  def Initialize(self, filename, skip_validation=False):
    """Initialize the config manager with the configuration file."""
    self.config_filename = filename
    result = self.read(filename)
    if not skip_validation:
      self.Validate()   # This will raise if the file doesn't validate.
    return result

  def InitializeFromFileObject(self, fileobj, skip_validation=False):
    """Initialize the config manager from a file like object."""
    if hasattr(fileobj, "name"):
      self.config_filename = fileobj.name
    result = self.readfp(fileobj)
    if not skip_validation:
      self.Validate()   # This will raise if the file doesn't validate.
    return result

  def Validate(self):
    """Check formatting to give early warning early of bad formatting issues."""
    for section in self.sections():
      if not IsCamel(section):
        raise ConfigFormatError("Section %s is not AlphaNum with TitleCase"
                                % section)

  # pylint: disable=redefined-builtin
  def _interpolate(self, section, option, rawval, vars):
    """Override interpolate to handle @inherit_from_section."""
    if "@inherit_from_section" in vars:
      inherited_vars = dict(self.items(vars["@inherit_from_section"]))
      # pylint: disable=protected-access
      vars = ConfigParser._Chainmap(vars, inherited_vars)
    # Cannot use super() here.
    return ConfigParser.SafeConfigParser._interpolate(self, section, option,
                                                      rawval, vars)

  def __getitem__(self, item):
    """Get attribute with section and modifier support.

    Args:
      item: a string containing the item specification. E.g.
            "option" or ".option" global configuration item,
            "section.option" configuration item in a specific section.
            "section.option|escape" configuration item in a specific section
             with modifier. The modifier must exists as a modifier function
             as part of this class, e.g. escape, join, lower and upper.

    Returns:
      The value of the item.
    """
    if "." in item:
      section, option = item.split(".", 1)
    else:
      section, option = "", item

    try:
      option, modifier = option.split("|", 1)

      return getattr(self, modifier)(self.get(section, option))
    except ValueError:
      return self.get(section, option)

  def __setitem__(self, item, value):
    """Set attribute with section and modifier support.

    Args:
      item: a string containing the item specification. E.g.
            "option" or ".option" global configuration item,
            "section.option" configuration item in a specific section.
      value: the value to set.
    """
    if "." in item:
      section, option = item.split(".", 1)
    else:
      section, option = "", item

    self.set(section, option, value)

  # pylint: disable=redefined-builtin
  def get(self, section, option, raw=False, vars=None):
    """Override get to support OS specific sections.

    Args:
      section: Section to look in.
      option: Option to retrieve.
      raw: Ignore interpolation.
      vars: raw variables to override with.

    Returns:
      The option requested.

    Some sections can have OS specific config sections.
    Values in the OS Specific section will override the options in
    the OS generic section. E.g. Name = foo in [ClientBuildWindows]
    will override Name = bar in [ClientBuild]. Callers should request
    options in the more specific section.
    """
    inherit = "@inherit_from_section"
    try:
      # Cannot use super() here
      result = ConfigParser.SafeConfigParser.get(self, section, option, raw,
                                                 vars)
    except ConfigParser.NoOptionError:
      if ConfigParser.SafeConfigParser.has_option(self, section, inherit):
        # Attempt to retrieve it from the inherited section instead.
        inherited_section = ConfigParser.SafeConfigParser.get(
            self, section, inherit)
        result = self.get(inherited_section, option, raw=raw)
      else:
        # If it isn't an inherited section, re-raise the error.
        raise

    return self.NewlineFixup(result)

  def NewlineFixup(self, result):
    """Fixup lost newlines in the config.

    Args:
      result: Data to fix up.

    Returns:
      The same data but with the lines fixed.

    Fixup function to handle the python 2 issue of losing newlines in the
    config parser options. This is resolved in python 3 and this can be
    deprecated then. Essentially an option containing a newline will be
    returned without the newline.

    This function handles some special cases we need to deal with as a hack
    until it is resolved properly.
    """
    result_lines = []
    newline_after = ["DEK-Info:"]
    for line in result.splitlines():
      result_lines.append(line)
      for nl in newline_after:
        if line.startswith(nl):
          result_lines.append("")
    return "\n".join(result_lines)

  def escape(self, data):  # pylint: disable=g-bad-name
    """Escape modifier function used for interpolation.

       E.g. %(ConfigItem|escape)s will escape certain characters in
       the ConfigItem value. Escaped characters are: backslash

    Args:
      data: a string containing the data.

    Returns:
      An escaped version of the data.
    """
    # Cannot use re.escape() here since it also escapes underscores
    return re.sub(r"\\", r"\\\\", data)

  def join(self, data):  # pylint: disable=g-bad-name
    """Join modifier function used for interpolation.

       E.g. %(ConfigItem|join)s will join a multi line ConfigItem value
       into a single line.

    Args:
      data: a string containing the data.

    Returns:
      A joined version of the data.
    """
    return "".join(data.splitlines())

  def lower(self, data):  # pylint: disable=g-bad-name
    """Lower modifier function used for interpolation.

       E.g. %(ConfigItem|lower)s will lower case the ConfigItem value.

    Args:
      data: a string containing the data.

    Returns:
      A lower case version of the data.
    """
    return data.lower()

  def upper(self, data):  # pylint: disable=g-bad-name
    """Upper modifier function used for interpolation.

       E.g. %(ConfigItem|upper)s will upper case the ConfigItem value.

    Args:
      data: a string containing the data.

    Returns:
      An upper case version of the data.
    """
    return data.upper()

  # TODO(user): This code is not ready for use yet.
  def WriteClientConfigCopy(self, out_path):
    """Write a copy of the config containing only the client sections.

       This funcion is used to convert a full server configuration file
       into a client configuraion file.

    Args:
      out_path: the path of the output file.
    """
    new_config = ConfigParser.SafeConfigParser()

    for section in ["ClientSigningKeys", "ServerKeys"]:
      if self.has_section(section):
        new_config.add_section(section)
        try:
          for k, v in self.items(section, raw=True):
            # Safety check, we don't want private keys in client configs.
            if "private" in v.lower():
              raise RuntimeError("Attempt to write private key thwarted.")
            # Skip anything in the default section.
            if self.has_option("DEFAULT", k):
              continue
            new_config.set(section, k, v)
        except ConfigParser.NoOptionError:
          pass

    new_config.write(open(out_path, "wb"))

  def WriteConfig(self):
    """Write the filename back to the config file it was loaded from."""
    with open(self.config_filename, "wb") as conf_fd:
      self.write(conf_fd)

  def InitFlagSections(self, additional_sections=None):
    """Go through a section and set the options in the FLAGS object."""
    # TODO(user): Deprecate this, it should not be needed after the CONFIG
    # changes to deprecate most FLAGS usage.
    if additional_sections is None:
      additional_sections = []
    for section in set(self.flag_sections).union(set(additional_sections)):
      if self.has_section(section):
        for option, value in self.items(section):
          if hasattr(FLAGS, option):
            setattr(FLAGS, option, value)
          else:
            logging.warn("Attempt to set flag %s from %s where it doesn't"
                         " exist", option, section)

  def FormattedAsString(self, sections=None, truncate_len=None):
    """Return the config as a string but with extra formatting for easy display.

    Args:
      sections: List of sections to include. If None all will be included.
      truncate_len: Truncate values to this lenght. If None don't truncate.

    Returns:
      A string with the formatted config.

    Key reasons to use this:
      - Truncate long options values such as certs.
      - Only show particular sections.
    """
    if sections is None:
      sections = self.sections()
    output = []
    for section in sections:
      output.append("[%s]" % section)
      for item, val in self.items(section):
        if truncate_len:
          # Truncate to first line end or length.
          if "\n" in val:
            val = val.split("\n", 1)[0] + " [truncated]"
          if len(val) > truncate_len:
            val = val[:truncate_len] + " [truncated]"
        output.append("%s: %s" % (item, val))
      output.append("")
    return "\n".join(output)


def IsCamel(s):
  """Attempt to validate strings as camel case."""
  if s[0].isupper() and s != s.lower() and s != s.upper() and s.isalnum():
    return True
  return False


# Global for storing the config.
CONFIG = ConfigManager()


class ConfigLibInit(registry.InitHook):
  """Initializer for the config, reads in the config file."""

  def RunOnce(self):
    CONFIG.Initialize(FLAGS.config)

    # Now go through the ServerFlags config and set flag values.
    CONFIG.InitFlagSections()

