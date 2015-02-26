#!/usr/bin/env python
"""Simple parsers for configuration files."""
import collections
import re

import logging

from grr.lib import lexer
from grr.lib import parsers
from grr.lib import rdfvalue
from grr.lib import utils


def AsIter(arg):
  """Encapsulates an argument in a tuple, if it's not already iterable."""
  if isinstance(arg, basestring):
    rslt = [arg]
  elif isinstance(arg, collections.Iterable):
    rslt = arg
  elif not arg:
    rslt = []
  else:
    rslt = [arg]
  return tuple(rslt)


# Grr lexer implementation of ssv parser. Considered using
# https://github.com/Eugeny/reconfigure/blob/master/reconfigure/parsers/ssv.py
# but it doesn't seem to actually forward lookup.
class FieldParser(lexer.Lexer):
  r"""A generalized field based parser that splits entries into fields.

  Entries refer to distinct records within the text content, for example each
  line of /etc/passwd or a ssh configuration attribute.
  Fields are elements that make up the entry, for example the individual
  parameters in /etc/passwd.

  The parser supports:
  - Flexible field based separators (e.g. spaces, commas, colons).
  - Identification and removal of line comments. Inline comments (e.g. /*...*/)
    are not supported.
  - Line continuation detection.
  - Multiline quotes.

  The parser uses the following attributes as defaults:
  - comments: #
  - cont: \ (followed by any amount of whitespace)
  - ml_quote: False (by default, quotes must close before newlines).
  - quot: Both " and ' characters.
  - sep: Whitespace
  - term: Newlines.

  To override default values, pass in appropriate keywords with a python
  compatible regex string.
  """

  def __init__(self, comments=r"#", cont=r"\\\s*\n", ml_quote=False,
               quot=(r"\"", r"'"), sep=r"\s+", term=r"\n", verbose=0):
    """A generalized field-based parser. Handles whitespace, csv etc.

    Args:
      comments: Line comment patterns (e.g. "#").
      cont: Continuation patterns (e.g. "\\").
      ml_quote: Boolean flag to allow quoted strings to span lines.
      quot: Quotation patterns (e.g. "\\"" or "'").
      sep: Field separator patterns (e.g. "[\\s,]").
      term: Entry termination patterns (e.g. "\\n").
      verbose: Enable verbose mode for the lexer. Useful for debugging.
    """
    super(FieldParser, self).__init__()
    self.entries = []
    self.fields = []
    self.field = ""
    self.comments = AsIter(comments)
    self.cont = AsIter(cont)
    self.ml_quote = AsIter(ml_quote)
    self.quot = AsIter(quot)
    self.sep = AsIter(sep)
    self.term = AsIter(term)
    self.verbose = verbose
    self._GenStates()

  def _GenStates(self):
    """Generate the lexer states."""
    self.GenCommentState()
    self.GenFwdState()
    self.GenQuotedState()
    self.GenCatchallState()

  def _AddToken(self, state_regex, regex, actions, next_state):
    self._tokens.append(lexer.Token(state_regex, regex, actions, next_state))

  def GenCommentState(self):
    if self.comments:
      self._AddToken("COMMENT", r"\n", "PushBack,PopState", None)
      self._AddToken("COMMENT", ".", None, None)

  def GenFwdState(self):
    """Generates forwarding state rules.

    The lexer will fast forward until there is string content. The
    string content will be returned to the string processor.
    """
    for c in self.cont:
      self._AddToken("FWD", c, None, None)
    for s in self.sep:
      self._AddToken("FWD", s, None, None)
    self._AddToken("FWD", ".", "PushBack,PopState", None)

  def GenQuotedState(self):
    """Generate string matching state rules."""
    for i, q in enumerate(self.quot):
      label = "%s_STRING" % i
      escaped = q.encode("string_escape")
      self._AddToken(label, escaped, "PopState", None)
      self._AddToken(label, q, "PopState", None)
      if self.ml_quote:
        self._AddToken(label, r"\n", None, None)
      else:
        self._AddToken(label, r"\n", "BadLine", None)
      self._AddToken(label, ".", "AddToField", None)

  def GenCatchallState(self):
    """Generate string matching state rules.

    This sets up initial state handlers that cover both the 'INITIAL' state
    and the intermediate content between fields.

    The lexer acts on items with precedence:
      - continuation characters: use the fast forward state rules.
      - field separators: finalize processing the field.
      - quotation characters: use the quotation state rules.
    """
    for c in self.comments:
      self._AddToken(".", c, "PushState,EndField", "COMMENT")
    for c in self.cont:
      self._AddToken(".", c, "PushState", "FWD")
    for t in self.term:
      self._AddToken(".", t, "EndEntry", None)
    for s in self.sep:
      self._AddToken(".", s, "EndField", None)
    for i, q in enumerate(self.quot):
      self._AddToken(".", q, "PushState", "%s_STRING" % i)
    self._AddToken(".", ".", "AddToField", None)

  def EndEntry(self, **_):
    self.EndField()
    if self.fields:
      # Copy the fields into the processed entries.
      self.entries.append(self.fields[:])
    self.fields = []

  def AddToField(self, string="", **_):
    if string:
      self.field += string

  def EndField(self, **_):
    if self.field:
      self.fields.append(self.field[:])
      self.field = ""

  def BadLine(self, **_):
    logging.debug("Skipped bad line in file at %s" % self.processed)
    self.field = ""

  def ParseEntries(self, data):
    # Flush any old results.
    self.Reset()
    self.Feed(utils.SmartStr(data))
    self.Close()
    return self.entries


class KeyValueParser(FieldParser):
  """A generalized KeyValue parser that splits entries into key/value pairs.

  Capabilities and parameters are identical to FieldParser, with one difference.
  The parser also accepts the parameter "kv_sep"
  Patterns specified in kv_sep are used to demarcate key/value processing.

  kv_sep defaults to "="
  """

  def __init__(self, comments=r"#", cont=r"\\\s*\n", kv_sep="=", ml_quote=False,
               quot=(r"\"", r"'"), sep=r"\s+", term=r"\n", verbose=0):
    """A generalized key-value parser. Handles whitespace, csv etc.

    Args:
      comments: Line comment patterns (e.g. "#").
      cont: Continuation patterns (e.g. "\\").
      kv_sep: Key/Value separators (e.g. "=" or ":").
      ml_quote: Boolean flag to allow quoted strings to span lines.
      quot: Quotation patterns (e.g. "\\"" or "'").
      sep: Field separator patterns (e.g. "[\\s,]").
      term: Entry termination patterns (e.g. "\\n").
      verbose: Enable verbose mode for the lexer. Useful for debugging.
    """
    self.kv_sep = AsIter(kv_sep)
    super(KeyValueParser, self).__init__(comments=comments, cont=cont,
                                         ml_quote=ml_quote, quot=quot, sep=sep,
                                         term=term, verbose=verbose)
    self.key_field = ""

  def _GenStates(self):
    self.GenCommentState()
    self.GenFwdState()
    self.GenQuotedState()
    self.GenMatchFirstState()
    self.GenInitialState()
    self.GenKeyState()
    self.GenValueState()
    self.GenCatchallState()

  def GenMatchFirstState(self):
    for i, q in enumerate(self.quot):
      self._AddToken(".", q, "PushState", "%s_STRING" % i)
    for c in self.cont:
      self._AddToken(".", c, "PushState", "FWD")

  def GenInitialState(self):
    for c in self.comments:
      self._AddToken("INITIAL", c, "PushState,EndField", "COMMENT")
    for t in self.term:
      self._AddToken("INITIAL", t, "EndField,EndEntry", None)
    for c in self.sep:
      self._AddToken("INITIAL", c, "PushState", "FWD")
    for k in self.kv_sep:
      self._AddToken("INITIAL", k, "BadLine", None)
    self._AddToken("INITIAL", ".", "PushState,PushBack", "KEY")

  def GenKeyState(self):
    for c in self.comments:
      self._AddToken("KEY", c, "EndKeyField,EndEntry,PopState,PushBack",
                     "COMMENT")
    for t in self.term:
      self._AddToken("KEY", t, "EndKeyField,EndEntry,PopState", None)
    for k in self.kv_sep:
      self._AddToken("KEY", k, "EndKeyField", "VALUE")

  def GenValueState(self):
    for c in self.comments:
      self._AddToken("VALUE", c, "EndField,EndEntry,PopState,PushBack",
                     "COMMENT")
    for t in self.term:
      self._AddToken("VALUE", t, "EndField,EndEntry,PopState", None)
    for s in self.sep:
      self._AddToken("VALUE", s, "EndField", None)

  def GenCatchallState(self):
    self._AddToken(".", ".", "AddToField", None)

  def EndKeyField(self, **_):
    self.key_field = self.field
    self.field = ""

  def EndEntry(self, **_):
    key_field = self.key_field.strip()
    if key_field:
      self.entries.append({key_field: self.fields})
    self.key_field = ""
    self.fields = []


class NfsExportsParser(parsers.FileParser, FieldParser):
  """Parser for NFS exports."""

  output_types = ["NfsExport"]
  supported_artifacts = ["NfsExportsFile"]

  def Parse(self, unused_stat, file_obj, unused_knowledge_base):
    self.ParseEntries(file_obj.read())
    for entry in self.entries:
      if not entry:
        continue
      result = rdfvalue.NfsExport()
      result.share = entry[0]
      for field in entry[1:]:
        if field.startswith(("-", "(")):
          result.defaults = field.strip("-()").split(",")
        else:
          client = rdfvalue.NfsClient()
          cfg = field.split("(", 1)
          host = cfg[0]
          if len(cfg) > 1:
            options = cfg[1]
          else:
            options = None
          client.host = host
          if options:
            client.options = options.strip("()").split(",")
          result.clients.append(client)
      yield result


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
