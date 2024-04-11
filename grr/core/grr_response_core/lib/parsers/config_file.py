#!/usr/bin/env python
"""Simple parsers for configuration files."""

from collections import abc
import logging
import re

from grr_response_core.lib import lexer
from grr_response_core.lib.rdfvalues import config_file as rdf_config_file
from grr_response_core.lib.util import precondition


def AsIter(arg):
  """Encapsulates an argument in a tuple, if it's not already iterable."""
  if isinstance(arg, str):
    rslt = [arg]
  elif isinstance(arg, abc.Iterable):
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

  def __init__(
      self,
      comments=r"#",
      cont=r"\\\s*\n",
      ml_quote=False,
      quot=(r"\"", r"'"),
      sep=r"[ \t\f\v]+",
      term=r"[\r\n]",
      verbose=0,
  ):
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
    super().__init__()
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
    super().Reset()
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
      escaped = re.escape(q)
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

  def ParseEntries(self, data: str):
    precondition.AssertType(data, str)

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

  def __init__(
      self,
      comments=r"#",
      cont=r"\\\s*\n",
      kv_sep="=",
      ml_quote=False,
      quot=(r"\"", r"'"),
      sep=r"[ \t\f\v]+",
      term=r"[\r\n]",
      verbose=0,
  ):
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
    super().__init__(
        comments=comments,
        cont=cont,
        ml_quote=ml_quote,
        quot=quot,
        sep=sep,
        term=term,
        verbose=verbose,
    )
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
      self._AddToken(
          "KEY", c, "EndKeyField,EndEntry,PopState,PushBack", "COMMENT"
      )
    for t in self.term:
      self._AddToken("KEY", t, "EndKeyField,EndEntry,PopState", None)
    for k in self.kv_sep:
      self._AddToken("KEY", k, "EndKeyField", "VALUE")

  def GenValueState(self):
    for c in self.comments:
      self._AddToken(
          "VALUE", c, "EndField,EndEntry,PopState,PushBack", "COMMENT"
      )
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
    result = dict()
    for field in self.ParseEntries(data):
      result.update(field)
    return result


class RsyslogFieldParser(FieldParser):
  """Field parser for syslog configurations."""

  log_rule_re = re.compile(r"([\w,\*]+)\.([\w,!=\*]+)")
  destinations = dict([
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
    for dst_str, dst_re in self.destinations.items():
      dst = dst_re.match(action)
      if dst:
        rslt.transport = dst_str
        rslt.destination = dst.group(1)
        break
    return rslt
