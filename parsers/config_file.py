#!/usr/bin/env python
"""Simple parsers for configuration files."""
import re
from grr.lib import parsers
from grr.lib import rdfvalue


class SshdConfigParser(parsers.FileParser):
  """Parser for sshd_config files."""

  output_types = ["SshdConfig"]
  supported_artifacts = ["SshdConfigFile", "SshdConfigCmd"]
  # Specify the values that are boolean or integer. Anything else is a string.
  _integers = ["clientalivecountmax",
               "magicudsport",
               "maxauthtries",
               "maxsessions",
               "port",
               "protocol",
               "serverkeybits",
               "x11displayoffset"]
  _booleans = ["allowagentforwarding",
               "challengeresponseauthentication",
               "gssapiauthentication",
               "gssapicleanupcredentials",
               "gssapikeyexchange",
               "gssapistorecredentialsonrekey",
               "gssapistrictacceptorcheck",
               "hostbasedauthentication",
               "ignorerhosts",
               "ignoreuserknownhosts",
               "kbdinteractiveauthentication",
               "kerberosauthentication",
               "passwordauthentication",
               "permitemptypasswords",
               "permitrootlogin",
               "permittunnel",
               "permituserenvironment",
               "pubkeyauthentication",
               "rhostsrsaauthentication",
               "rsaauthentication",
               "strictmodes",
               "uselogin",
               "usepam",
               "x11forwarding",
               "x11uselocalhost"]
  # Valid ways that parameters can repeat
  _repeated = {"acceptenv": r"[\n\s]+",
               "allowgroups": r"[\s]+",
               "allowusers": r"[\s]+",
               "authenticationmethods": r"[\s]+",
               "authorizedkeysfile": r"[\s]+",
               "ciphers": r"[,]+",
               "denygroups": r"[\s]+",
               "denyusers": r"[\s]+",
               "forcecommand": r"[\n]+",
               "hostkey": r"[\n]+",
               "kexalgorithms": r"[,]+",
               "listenaddress": r"[\n]+",
               "macs": r"[,]+",
               "permitopen": r"[\s]+",
               "port": r"[,\n]+",
               "protocol": r"[,]+",
               "subsystem": r"[\n]+"}
  _true = ["yes", "true", "1"]
  _match_keywords = [
      "acceptenv", "allowagentforwarding", "allowgroups", "allowtcpforwarding",
      "allowusers", "authenticationmethods", "authorizedkeyscommand",
      "authorizedkeyscommanduser", "authorizedkeysfile",
      "authorizedprincipalsfile", "banner", "chrootdirectory", "denygroups",
      "denyusers", "forcecommand", "gatewayports", "gssapiauthentication",
      "hostbasedauthentication", "hostbasedusesnamefrompacketonly",
      "kbdinteractiveauthentication", "kerberosauthentication", "magicudspath",
      "magicudsport", "maxauthtries", "maxsessions", "passwordauthentication",
      "permitemptypasswords", "permitopen", "permitrootlogin",
      "permittemphomedir", "permittty", "permittunnel", "pubkeyauthentication",
      "rekeylimit", "rhostsrsaauthentication", "rsaauthentication",
      "temphomedirpath", "x11displayoffset", "x11forwarding", "x11uselocalhost"]

  def __init__(self):
    super(SshdConfigParser, self).__init__()
    self.Flush()

  def Flush(self):
    self.config = {}
    self.matches = []
    self.section = self.config
    self.processor = self._ParseEntry

  def ParseLine(self, line):
    """Extracts keyword/value settings from the sshd config.

    The keyword is always the first string item.
    Values are the remainder of the string. In cases where an sshd config
    allows multiple values, these are split according to whatever separator(s)
    sshd_config permits for that value.

    Keywords and values are normalized. Keywords are converted to lowercase.
    Values are converted into integers, booleans or strings. Strings are always
    lowercased.

    Args:
      line: A line of the configuration file.
    """
    kv = line.split(None, 1)
    keyword = kv[0].lower()
    # Safely set the argument string if it wasn't found.
    values = kv[1:] or [""]
    # Then split any parameters that are actually repeated items.
    separators = self._repeated.get(keyword)
    if separators:
      repeated = []
      for v in values:
        repeated.extend(re.split(separators, v))
      # Remove empty matches.
      values = [v for v in repeated if v]

    # Now convert the values to the right types.
    if keyword in self._integers:
      values = [int(v) for v in values]
    elif keyword in self._booleans:
      values = [v.lower() in self._true for v in values]
    else:
      values = [v.lower() for v in values]
    # Only repeated arguments should be treated as a list.
    if keyword not in self._repeated:
      values = values[0]
    # Switch sections for new match blocks.
    if keyword == "match":
      self._NewMatchSection(values)
    # Add the keyword/values to the section.
    self.processor(keyword, values)

  def _ParseEntry(self, key, val):
    """Adds an entry for a configuration setting.

    Args:
      key: The name of the setting.
      val: The value of the setting.
    """
    if key in self._repeated:
      setting = self.section.setdefault(key, [])
      setting.extend(val)
    else:
      self.section.setdefault(key, val)

  def _ParseMatchGrp(self, key, val):
    """Adds valid match group parameters to the configuration."""
    if key in self._match_keywords:
      self._ParseEntry(key, val)

  def _NewMatchSection(self, val):
    """Create a new configuration section for each match clause.

    Each match clause is added to the main config, and the criterion that will
    trigger the match is recorded, as is the configuration.

    Args:
      val: The value following the 'match' keyword.
    """
    section = {"criterion": val, "config": {}}
    self.matches.append(section)
    # Now add configuration items to config section of the match block.
    self.section = section["config"]
    # Switch to a match-specific processor on a new match_block.
    self.processor = self._ParseMatchGrp

  def Parse(self, stat, file_object, knowledge_base):
    """Parse the sshd configuration.

    Process each of the lines in the configuration file.

    Assembes an sshd_config file into a dictionary with the configuration
    keyword as the key, and the configuration settings as value(s).

    Args:
      stat: unused
      file_object: An open configuration file object.
      knowledge_base: unused

    Yields:
      The configuration as an rdfvalue.
    """
    _, _ = stat, knowledge_base
    # Clean out any residual state.
    self.Flush()
    # for line in file_object:
    lines = [l.strip() for l in file_object.read(100000).splitlines()]
    for line in lines:
      # Remove comments (will break if it includes a quoted/escaped #)
      line = line.split("#")[0].strip()
      if line:
        self.ParseLine(line)
    matches = []
    for match in self.matches:
      criterion, config = match["criterion"], match["config"]
      block = rdfvalue.SshdMatchBlock(criterion=criterion, config=config)
      matches.append(block)
    yield rdfvalue.SshdConfig(config=self.config, matches=matches)
