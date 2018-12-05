#!/usr/bin/env python
"""Simple parsers for configuration files."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import logging
import re


from builtins import zip  # pylint: disable=redefined-builtin
from future.utils import iteritems
from future.utils import string_types

from grr_response_core.lib import lexer
from grr_response_core.lib import parser
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import anomaly as rdf_anomaly
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import config_file as rdf_config_file
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import standard as rdf_standard


def AsIter(arg):
  """Encapsulates an argument in a tuple, if it's not already iterable."""
  if isinstance(arg, string_types):
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

  def __init__(self,
               comments=r"#",
               cont=r"\\\s*\n",
               ml_quote=False,
               quot=(r"\"", r"'"),
               sep=r"[ \t\f\v]+",
               term=r"[\r\n]",
               verbose=0):
    r"""A generalized field-based parser.

    Handles whitespace, csv etc.

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

  def Reset(self):
    super(FieldParser, self).Reset()
    self.entries = []
    self.fields = []
    self.field = ""

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
      escaped = q.encode("unicode_escape")
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
    logging.debug("Skipped bad line in file at %s", self.processed)
    self.field = ""

  def ParseEntries(self, data):
    # Flush any old results.
    self.Reset()
    self.Feed(data)
    self.Close()
    # In case there isn't a terminating field at the end of the feed, e.g. \n
    self.EndEntry()
    return self.entries


class KeyValueParser(FieldParser):
  """A generalized KeyValue parser that splits entries into key/value pairs.

  Capabilities and parameters are identical to FieldParser, with one difference.
  The parser also accepts the parameter "kv_sep"
  Patterns specified in kv_sep are used to demarcate key/value processing.

  kv_sep defaults to "="
  """

  def __init__(self,
               comments=r"#",
               cont=r"\\\s*\n",
               kv_sep="=",
               ml_quote=False,
               quot=(r"\"", r"'"),
               sep=r"[ \t\f\v]+",
               term=r"[\r\n]",
               verbose=0):
    """A generalized key-value parser.

    Handles whitespace, csv etc.

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
    super(KeyValueParser, self).__init__(
        comments=comments,
        cont=cont,
        ml_quote=ml_quote,
        quot=quot,
        sep=sep,
        term=term,
        verbose=verbose)
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
    # Finalize processing for non-terminated entries. Key first, then fields.
    if self.field and not self.key_field:
      self.EndKeyField()
    else:
      self.EndField()
    # Set up the entry.
    key_field = self.key_field.strip()
    if key_field:
      self.entries.append({key_field: self.fields})
    self.key_field = ""
    self.fields = []

  def ParseToOrderedDict(self, data):
    result = collections.OrderedDict()
    for field in self.ParseEntries(data):
      result.update(field)
    return result


class NfsExportsParser(parser.FileParser):
  """Parser for NFS exports."""

  output_types = ["NfsExport"]
  supported_artifacts = ["NfsExportsFile"]

  def __init__(self, *args, **kwargs):
    super(NfsExportsParser, self).__init__(*args, **kwargs)
    self._field_parser = FieldParser()

  def Parse(self, unused_stat, file_obj, unused_knowledge_base):
    for entry in self._field_parser.ParseEntries(
        utils.ReadFileBytesAsUnicode(file_obj)):
      if not entry:
        continue
      result = rdf_config_file.NfsExport()
      result.share = entry[0]
      for field in entry[1:]:
        if field.startswith(("-", "(")):
          result.defaults = field.strip("-()").split(",")
        else:
          client = rdf_config_file.NfsClient()
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


class SshdFieldParser(object):
  """The base class for the ssh config parsers."""

  # Specify the values that are boolean or integer. Anything else is a string.
  _integers = ["clientalivecountmax",
               "magicudsport",
               "maxauthtries",
               "maxsessions",
               "port",
               "protocol",
               "serverkeybits",
               "x11displayoffset"]  # pyformat: disable
  _booleans = ["allowagentforwarding",
               "challengeresponseauthentication",
               "dsaauthentication"
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
               "permittunnel",
               "permituserenvironment",
               "pubkeyauthentication",
               "rhostsrsaauthentication",
               "rsaauthentication",
               "strictmodes",
               "uselogin",
               "usepam",
               "x11forwarding",
               "x11uselocalhost"]  # pyformat: disable
  # Valid ways that parameters can repeat
  _repeated = {
      "acceptenv": r"[\n\s]+",
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
      "pubkeyacceptedkeytypes": r"[,]+",
      "subsystem": r"[\n]+"
  }
  _true = ["yes", "true", "1"]
  _aliases = {"dsaauthentication": "pubkeyauthentication"}
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
      "permittemphomedir", "permittty", "permittunnel",
      "pubkeyacceptedkeytypes", "pubkeyauthentication", "rekeylimit",
      "rhostsrsaauthentication", "rsaauthentication", "temphomedirpath",
      "x11displayoffset", "x11forwarding", "x11uselocalhost"
  ]

  def __init__(self):
    super(SshdFieldParser, self).__init__()
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
    # If it's an alias, resolve it.
    if keyword in self._aliases:
      keyword = self._aliases[keyword]
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

  def GenerateResults(self):
    matches = []
    for match in self.matches:
      criterion, config = match["criterion"], match["config"]
      block = rdf_config_file.SshdMatchBlock(criterion=criterion, config=config)
      matches.append(block)
    yield rdf_config_file.SshdConfig(config=self.config, matches=matches)


class SshdConfigParser(parser.FileParser):
  """A parser for sshd_config files."""

  supported_artifacts = ["SshdConfigFile"]
  output_types = ["SshdConfig"]

  def __init__(self, *args, **kwargs):
    super(SshdConfigParser, self).__init__(*args, **kwargs)
    self._field_parser = SshdFieldParser()

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
    self._field_parser.Flush()
    lines = [
        l.strip()
        for l in utils.ReadFileBytesAsUnicode(file_object).splitlines()
    ]
    for line in lines:
      # Remove comments (will break if it includes a quoted/escaped #)
      line = line.split("#")[0].strip()
      if line:
        self._field_parser.ParseLine(line)
    for result in self._field_parser.GenerateResults():
      yield result


class SshdConfigCmdParser(parser.CommandParser):
  """A command parser for sshd -T output."""

  supported_artifacts = ["SshdConfigCmd"]
  output_types = ["SshdConfig"]

  def __init__(self, *args, **kwargs):
    super(SshdConfigCmdParser, self).__init__(*args, **kwargs)
    self._field_parser = SshdFieldParser()

  def Parse(self, cmd, args, stdout, stderr, return_val, time_taken,
            knowledge_base):
    # Clean out any residual state.
    self._field_parser.Flush()
    lines = [l.strip() for l in stdout.splitlines()]
    for line in lines:
      if line:
        self._field_parser.ParseLine(line)
    for result in self._field_parser.GenerateResults():
      yield result


class MtabParser(parser.FileParser):
  """Parser for mounted filesystem data acquired from /proc/mounts."""
  output_types = ["Filesystem"]
  supported_artifacts = ["LinuxProcMounts", "LinuxFstab"]

  def __init__(self, *args, **kwargs):
    super(MtabParser, self).__init__(*args, **kwargs)
    self._field_parser = FieldParser()

  def Parse(self, unused_stat, file_obj, unused_knowledge_base):
    for entry in self._field_parser.ParseEntries(
        utils.ReadFileBytesAsUnicode(file_obj)):
      if not entry:
        continue
      result = rdf_client_fs.Filesystem()
      result.device = entry[0].decode("string_escape")
      result.mount_point = entry[1].decode("string_escape")
      result.type = entry[2].decode("string_escape")
      options = KeyValueParser(term=",").ParseToOrderedDict(entry[3])
      # Keys without values get assigned [] by default. Because these keys are
      # actually true, if declared, change any [] values to True.
      for k, v in iteritems(options):
        options[k] = v or [True]
      result.options = rdf_protodict.AttributedDict(**options)
      yield result


class MountCmdParser(parser.CommandParser):
  """Parser for mounted filesystem data acquired from the mount command."""
  output_types = ["Filesystem"]
  supported_artifacts = ["LinuxMountCmd"]

  mount_re = re.compile(r"(.*) on (.*) type (.*) \((.*)\)")

  def __init__(self, *args, **kwargs):
    super(MountCmdParser, self).__init__(*args, **kwargs)
    self._field_parser = FieldParser()

  def Parse(self, cmd, args, stdout, stderr, return_val, time_taken,
            knowledge_base):
    """Parse the mount command output."""
    _ = stderr, time_taken, args, knowledge_base  # Unused.
    self.CheckReturn(cmd, return_val)
    result = rdf_protodict.AttributedDict()
    for entry in self._field_parser.ParseEntries(stdout):
      line_str = " ".join(entry)
      mount_rslt = self.mount_re.match(line_str)
      if mount_rslt:
        device, mount_point, fs_type, option_str = mount_rslt.groups()
        result = rdf_client_fs.Filesystem()
        result.device = device
        result.mount_point = mount_point
        result.type = fs_type
        # Parse these options as a dict as some items may be key/values.
        # KeyValue parser uses OrderedDict as the native parser method. Use it.
        options = KeyValueParser(term=",").ParseToOrderedDict(option_str)
        # Keys without values get assigned [] by default. Because these keys are
        # actually true, if declared, change any [] values to True.
        for k, v in iteritems(options):
          options[k] = v or [True]
        result.options = rdf_protodict.AttributedDict(**options)
        yield result


class RsyslogFieldParser(FieldParser):
  """Field parser for syslog configurations."""

  log_rule_re = re.compile(r"([\w,\*]+)\.([\w,!=\*]+)")
  destinations = collections.OrderedDict([
      ("TCP", re.compile(r"(?:@@)([^;]*)")),
      ("UDP", re.compile(r"(?:@)([^;]*)")),
      ("PIPE", re.compile(r"(?:\|)([^;]*)")),
      ("NONE", re.compile(r"(?:~)([^;]*)")),
      ("SCRIPT", re.compile(r"(?:\^)([^;]*)")),
      ("MODULE", re.compile(r"(?::om\w:)([^;]*)")),
      ("FILE", re.compile(r"-?(/[^;]*)")), ("WALL", re.compile(r"(\*)"))
  ])  # pyformat: disable

  def ParseAction(self, action):
    """Extract log configuration data from rsyslog actions.

    Actions have the format:
      <facility>/<severity> <type_def><destination>;<template>
      e.g. *.* @@loghost.example.com.:514;RSYSLOG_ForwardFormat

    Actions are selected by a type definition. These include:
      "@@": TCP syslog
      "@": UDP syslog
      "|": Named pipe
      "~": Drop to /dev/null
      "^": Shell script
      ":om<string>:": An output module
      Or a file path.

    Args:
      action: The action string from rsyslog.

    Returns:
      a rdfvalue.LogTarget message.
    """
    rslt = rdf_config_file.LogTarget()
    for dst_str, dst_re in iteritems(self.destinations):
      dst = dst_re.match(action)
      if dst:
        rslt.transport = dst_str
        rslt.destination = dst.group(1)
        break
    return rslt


class RsyslogParser(parser.FileMultiParser):
  """Artifact parser for syslog configurations."""

  output_types = ["AttributedDict"]
  supported_artifacts = ["LinuxRsyslogConfigs"]

  def __init__(self, *args, **kwargs):
    super(RsyslogParser, self).__init__(*args, **kwargs)
    self._field_parser = RsyslogFieldParser()

  def ParseMultiple(self, unused_stats, file_objs, unused_knowledge_base):
    # TODO(user): review quoting and line continuation.
    result = rdf_config_file.LogConfig()
    for file_obj in file_objs:
      for entry in self._field_parser.ParseEntries(
          utils.ReadFileBytesAsUnicode(file_obj)):
        directive = entry[0]
        log_rule = self._field_parser.log_rule_re.match(directive)
        if log_rule and entry[1:]:
          target = self._field_parser.ParseAction(entry[1])
          target.facility, target.priority = log_rule.groups()
          result.targets.append(target)
    return [result]


class PackageSourceParser(parser.FileParser):
  """Common code for APT and YUM source list parsing."""
  output_types = ["AttributedDict"]

  # Prevents this from automatically registering.
  __abstract = True  # pylint: disable=g-bad-name

  def Parse(self, stat, file_obj, unused_knowledge_base):
    uris_to_parse = self.FindPotentialURIs(file_obj)
    uris = []

    for url_to_parse in uris_to_parse:
      url = rdf_standard.URI()
      url.ParseFromString(url_to_parse)

      # if no transport then url_to_parse wasn't actually a valid URL
      # either host or path also have to exist for this to be a valid URL
      if url.transport and (url.host or url.path):
        uris.append(url)

    filename = stat.pathspec.path
    cfg = {"filename": filename, "uris": uris}
    yield rdf_protodict.AttributedDict(**cfg)

  def FindPotentialURIs(self, file_obj):
    """Stub Method to be overriden by APT and Yum source parsers."""
    raise NotImplementedError("Please implement FindPotentialURIs.")

  def ParseURIFromKeyValues(self, data, separator, uri_key):
    """Parse key/value formatted source listing and return potential URLs.

    The fundamental shape of this format is as follows:
    key: value   # here : = separator
    key : value
    URI: [URL]   # here URI = uri_key
      [URL]      # this is where it becomes trickey because [URL]
      [URL]      # can contain 'separator' specially if separator is :
    key: value

    The key uri_key is of interest to us and since the next line
    in the config could contain another [URL], we need to keep track of context
    when we hit uri_key  to be able to check if the next line(s)
    have more [URL].

    Args:
      data: unprocessed lines from a file
      separator: how the key/value pairs are seperated
      uri_key: starting name of the key containing URI.

    Returns:
      A list of potential URLs found in data
    """
    kv_entries = KeyValueParser(kv_sep=separator).ParseEntries(data)
    spaced_entries = FieldParser().ParseEntries(data)

    uris = []
    check_uri_on_next_line = False
    for kv_entry, sp_entry in zip(kv_entries, spaced_entries):
      for k, v in iteritems(kv_entry):
        # This line could be a URL if a) from  key:value, value is empty OR
        # b) if separator is : and first character of v starts with /.
        if (check_uri_on_next_line and
            (not v or (separator == ":" and v[0].startswith("/")))):
          uris.append(sp_entry[0])
        else:
          check_uri_on_next_line = False
          if k.lower().startswith(uri_key) and v:
            check_uri_on_next_line = True
            uris.append(v[0])  # v is a list

    return uris


class APTPackageSourceParser(PackageSourceParser):
  """Parser for APT source lists to extract URIs only."""
  supported_artifacts = ["APTSources"]

  def FindPotentialURIs(self, file_obj):
    """Given a file, this will return all potenial APT source URIs."""
    rfc822_format = ""  # will contain all lines not in legacy format
    uris_to_parse = []

    for line in utils.ReadFileBytesAsUnicode(file_obj).splitlines(True):
      # check if legacy style line - if it is then extract URL
      m = re.search(r"^\s*deb(?:-\S+)?(?:\s+\[[^\]]*\])*\s+(\S+)(?:\s|$)", line)
      if m:
        uris_to_parse.append(m.group(1))
      else:
        rfc822_format += line

    uris_to_parse.extend(self.ParseURIFromKeyValues(rfc822_format, ":", "uri"))
    return uris_to_parse


class YumPackageSourceParser(PackageSourceParser):
  """Parser for Yum source lists to extract URIs only."""
  supported_artifacts = ["YumSources"]

  def FindPotentialURIs(self, file_obj):
    """Given a file, this will return all potenial Yum source URIs."""
    return self.ParseURIFromKeyValues(
        utils.ReadFileBytesAsUnicode(file_obj), "=", "baseurl")


class CronAtAllowDenyParser(parser.FileParser):
  """Parser for /etc/cron.allow /etc/cron.deny /etc/at.allow & /etc/at.deny."""
  output_types = ["AttributedDict"]
  supported_artifacts = ["CronAtAllowDenyFiles"]

  def Parse(self, stat, file_obj, unused_knowledge_base):
    lines = set([
        l.strip() for l in utils.ReadFileBytesAsUnicode(file_obj).splitlines()
    ])

    users = []
    bad_lines = []
    for line in lines:
      # behaviour of At/Cron is undefined for lines with whitespace separated
      # fields/usernames
      if " " in line:
        bad_lines.append(line)
      elif line:  # drop empty lines
        users.append(line)

    filename = stat.pathspec.path
    cfg = {"filename": filename, "users": users}
    yield rdf_protodict.AttributedDict(**cfg)

    if bad_lines:
      yield rdf_anomaly.Anomaly(
          type="PARSER_ANOMALY",
          symptom="Dodgy entries in %s." % (filename),
          reference_pathspec=stat.pathspec,
          finding=bad_lines)


class NtpdFieldParser(FieldParser):
  """Field parser for ntpd.conf file."""
  output_types = ["NtpConfig"]
  supported_artifacts = ["NtpConfFile"]

  # The syntax is based on:
  #   https://www.freebsd.org/cgi/man.cgi?query=ntp.conf&sektion=5
  # keywords with integer args.
  _integers = set(["ttl", "hop"])
  # keywords with floating point args.
  _floats = set(["broadcastdelay", "calldelay"])
  # keywords that have repeating args.
  _repeated = set(["ttl", "hop"])
  # keywords that set an option state, but can be "repeated" as well.
  _boolean = set(["enable", "disable"])
  # keywords that are keyed to their first argument, an address.
  _address_based = set([
      "trap", "fudge", "server", "restrict", "peer", "broadcast",
      "manycastclient"
  ])
  # keywords that append/augment the config.
  _accumulators = set(["includefile", "setvar"])
  # keywords that can appear multiple times, accumulating data each time.
  _duplicates = _address_based | _boolean | _accumulators
  # All the expected keywords.
  _match_keywords = _integers | _floats | _repeated | _duplicates | set([
      "autokey", "revoke", "multicastclient", "driftfile", "broadcastclient",
      "manycastserver", "includefile", "interface", "disable", "includefile",
      "discard", "logconfig", "logfile", "tos", "tinker", "keys", "keysdir",
      "requestkey", "trustedkey", "crypto", "control", "statsdir", "filegen"
  ])

  defaults = {
      "auth": True,
      "bclient": False,
      "calibrate": False,
      "kernel": False,
      "monitor": True,
      "ntp": True,
      "pps": False,
      "stats": False
  }

  def __init__(self):
    super(NtpdFieldParser, self).__init__()
    # ntp.conf has no line continuation. Override the default 'cont' values
    # then parse up the lines.
    self.cont = ""
    self.config = self.defaults.copy()
    self.keyed = {}

  def ParseLine(self, entries):
    """Extracts keyword/value settings from the ntpd config.

    The keyword is always the first entry item.
    Values are the remainder of the entries. In cases where an ntpd config
    allows multiple values, these are split according to whitespace or
    duplicate entries.

    Keywords and values are normalized. Keywords are converted to lowercase.
    Values are converted into integers, floats or strings. Strings are always
    lowercased.

    Args:
      entries: A list of items making up a single line of a ntp.conf file.
    """
    # If no entries were found, short circuit.
    if not entries:
      return
    keyword = entries[0].lower()
    # Set the argument string if it wasn't found.
    values = entries[1:] or [""]

    # Convert any types we need too.
    if keyword in self._integers:
      values = [int(v) for v in values]
    if keyword in self._floats:
      values = [float(v) for v in values]

    if keyword not in self._repeated | self._duplicates:
      # We have a plain and simple single key/value config line.
      if isinstance(values[0], string_types):
        self.config[keyword] = " ".join(values)
      else:
        self.config[keyword] = values

    elif keyword in self._repeated:
      # The keyword can have multiple single-word options, so add them as a list
      # and overwrite previous settings.
      self.config[keyword] = values

    elif keyword in self._duplicates:
      if keyword in self._address_based:
        # If we have an address keyed keyword, join the keyword and address
        # together to make the complete key for this data.
        address = values[0].lower()
        values = values[1:] or [""]
        # Add/overwrite the address in this 'keyed' keywords dictionary.
        existing_keyword_config = self.keyed.setdefault(keyword, [])
        # Create a dict which stores the server name and the options.
        # Flatten the remaining options into a single string.
        existing_keyword_config.append({
            "address": address,
            "options": " ".join(values)
        })

      # Are we toggling an option?
      elif keyword in self._boolean:
        for option in values:
          if keyword == "enable":
            self.config[option] = True
          else:
            # As there are only two items in this set, we can assume disable.
            self.config[option] = False

      else:
        # We have a non-keyed & non-boolean keyword, so add to the collected
        # data so far. Order matters technically.
        prev_settings = self.config.setdefault(keyword, [])
        prev_settings.append(" ".join(values))


class NtpdParser(parser.FileParser):
  """Artifact parser for ntpd.conf file."""

  def Parse(self, stat, file_object, knowledge_base):
    """Parse a ntp config into rdf."""
    _, _ = stat, knowledge_base

    # TODO(hanuszczak): This parser only allows single use because it messes
    # with its state. This should be fixed.
    field_parser = NtpdFieldParser()
    for line in field_parser.ParseEntries(
        utils.ReadFileBytesAsUnicode(file_object)):
      field_parser.ParseLine(line)

    yield rdf_config_file.NtpConfig(
        config=field_parser.config,
        server=field_parser.keyed.get("server"),
        restrict=field_parser.keyed.get("restrict"),
        fudge=field_parser.keyed.get("fudge"),
        trap=field_parser.keyed.get("trap"),
        peer=field_parser.keyed.get("peer"),
        broadcast=field_parser.keyed.get("broadcast"),
        manycastclient=field_parser.keyed.get("manycastclient"))

  def ParseMultiple(self, stats, file_objects, knowledge_base):
    for s, f in zip(stats, file_objects):
      for rslt in self.Parse(s, f, knowledge_base):
        yield rslt


class SudoersFieldParser(FieldParser):
  """Parser for privileged configuration files such as sudoers and pam.d/su."""

  # Regex to remove comments from the file. The first group in the OR condition
  # handles comments that cover a full line, while also ignoring #include(dir).
  # The second group in the OR condition handles comments that begin partways
  # through a line, without matching UIDs or GIDs which are specified with # in
  # the format.
  # TODO(user): this regex fails to match '#32 users', but handles quite a
  # lot else.
  # TODO(user): this should be rewritten as a proper lexer
  COMMENTS_RE = re.compile(r"(#(?!include(?:dir)?\s+)\D+?$)", re.MULTILINE)

  ALIAS_TYPES = {
      "User_Alias": rdf_config_file.SudoersAlias.Type.USER,
      "Runas_Alias": rdf_config_file.SudoersAlias.Type.RUNAS,
      "Host_Alias": rdf_config_file.SudoersAlias.Type.HOST,
      "Cmnd_Alias": rdf_config_file.SudoersAlias.Type.CMD
  }
  ALIAS_FIELDS = {
      "User_Alias": "users",
      "Runas_Alias": "runas",
      "Host_Alias": "hosts",
      "Cmnd_Alias": "cmds"
  }
  DEFAULTS_KEY = "Defaults"
  INCLUDE_KEYS = ["#include", "#includedir"]

  def __init__(self, *args, **kwargs):
    kwargs["comments"] = []
    super(SudoersFieldParser, self).__init__(*args, **kwargs)

  def _ExtractList(self, fields, ignores=(",",), terminators=()):
    """Extract a list from the given fields."""
    extracted = []
    i = 0
    for i, field in enumerate(fields):
      # Space-separated comma; ignore, but this is not a finished list.
      # Similar for any other specified ignores (eg, equals sign).
      if field in ignores:
        continue

      # However, some fields are specifically meant to terminate iteration.
      if field in terminators:
        break

      extracted.append(field.strip("".join(ignores)))
      # Check for continuation; this will either be a trailing comma or the
      # next field after this one being a comma. The lookahead here is a bit
      # nasty.
      if not (field.endswith(",") or
              set(fields[i + 1:i + 2]).intersection(ignores)):
        break

    return extracted, fields[i + 1:]

  def ParseSudoersEntry(self, entry, sudoers_config):
    """Parse an entry and add it to the given SudoersConfig rdfvalue."""

    key = entry[0]
    if key in SudoersFieldParser.ALIAS_TYPES:
      # Alias.
      alias_entry = rdf_config_file.SudoersAlias(
          type=SudoersFieldParser.ALIAS_TYPES.get(key), name=entry[1])

      # Members of this alias, comma-separated.
      members, _ = self._ExtractList(entry[2:], ignores=(",", "="))
      field = SudoersFieldParser.ALIAS_FIELDS.get(key)
      getattr(alias_entry, field).Extend(members)

      sudoers_config.aliases.append(alias_entry)
    elif key.startswith(SudoersFieldParser.DEFAULTS_KEY):
      # Default.
      # Identify scope if one exists (Defaults<scope> ...)
      scope = None
      if len(key) > len(SudoersFieldParser.DEFAULTS_KEY):
        scope = key[len(SudoersFieldParser.DEFAULTS_KEY) + 1:]

      # There can be multiple defaults on a line, for the one scope.
      entry = entry[1:]
      defaults, _ = self._ExtractList(entry)
      for default in defaults:
        default_entry = rdf_config_file.SudoersDefault(scope=scope)

        # Extract key name and value(s).
        default_name = default
        value = []
        if "=" in default_name:
          default_name, remainder = default_name.split("=", 1)
          value = [remainder]
        default_entry.name = default_name
        if entry:
          default_entry.value = " ".join(value)

        sudoers_config.defaults.append(default_entry)
    elif key in SudoersFieldParser.INCLUDE_KEYS:
      # TODO(user): make #includedir more obvious in the RDFValue somewhere
      target = " ".join(entry[1:])
      sudoers_config.includes.append(target)
    else:
      users, entry = self._ExtractList(entry)
      hosts, entry = self._ExtractList(entry, terminators=("=",))

      # Remove = from <user> <host> = <specs>
      if entry[0] == "=":
        entry = entry[1:]

      # Command specification.
      sudoers_entry = rdf_config_file.SudoersEntry(
          users=users, hosts=hosts, cmdspec=entry)

      sudoers_config.entries.append(sudoers_entry)

  def Preprocess(self, data):
    """Preprocess the given data, ready for parsing."""
    # Add whitespace to line continuations.
    data = data.replace(":\\", ": \\")

    # Strip comments manually because sudoers has multiple meanings for '#'.
    data = SudoersFieldParser.COMMENTS_RE.sub("", data)
    return data


class SudoersParser(parser.FileParser):
  """Artifact parser for privileged configuration files."""

  output_types = ["SudoersConfig"]
  supported_artifacts = ["UnixSudoersConfiguration"]

  def __init__(self, *args, **kwargs):
    super(SudoersParser, self).__init__(*args, **kwargs)
    self._field_parser = SudoersFieldParser()

  def Parse(self, unused_stat, file_obj, unused_knowledge_base):
    self._field_parser.ParseEntries(
        self._field_parser.Preprocess(utils.ReadFileBytesAsUnicode(file_obj)))
    result = rdf_config_file.SudoersConfig()
    for entry in self._field_parser.entries:
      # Handle multiple entries in one line, eg:
      # foo bar : baz
      # ... would become ...
      # [[foo, bar], [foo, baz]]
      key = entry[0]
      nested_entries = []
      if ":" not in entry:
        nested_entries = [entry]
      else:
        runner = []
        for field in entry:
          if field == ":":
            nested_entries.append(runner)
            runner = [key]
            continue

          runner.append(field)

        nested_entries.append(runner)

      for nested_entry in nested_entries:
        self._field_parser.ParseSudoersEntry(nested_entry, result)

    yield result
