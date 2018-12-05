#!/usr/bin/env python
"""An LL(1) lexer. This lexer is very tolerant of errors and can resync."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
import re


# pytype: disable=import-error
from builtins import filter  # pylint: disable=redefined-builtin
from builtins import range  # pylint: disable=redefined-builtin
# pytype: enable=import-error

from grr_response_core.lib import utils
from grr_response_core.lib.util import precondition


class Token(object):
  """A token action."""

  state_regex = None

  def __init__(self, state_regex, regex, actions, next_state, flags=re.I):
    """Constructor.

    Args:

      state_regex: If this regular expression matches the current state this
                   rule is considered.
      regex: A regular expression to try and match from the current point.
      actions: A command separated list of method names in the Lexer to call.
      next_state: The next state we transition to if this Token matches.
      flags: re flags.
    """
    if state_regex:
      self.state_regex = re.compile(state_regex, re.DOTALL | re.M | re.S | re.U
                                    | flags)
    self.regex = re.compile(regex, re.DOTALL | re.M | re.S | re.U | flags)

    self.re_str = regex
    self.actions = []
    if actions:
      self.actions = actions.split(",")

    self.next_state = next_state

  def Action(self, lexer):
    """Method is called when the token matches."""


class Error(Exception):
  """Module exception."""


class ParseError(Error):
  """A parse error occured."""


class Lexer(object):
  """A generic feed lexer."""
  # A list of Token() instances.
  tokens = []
  # Regex flags
  flags = 0

  def __init__(self, data=""):
    precondition.AssertType(data, unicode)
    # Set the lexer up to process a new data feed.
    self.Reset()
    # Populate internal token list with class tokens, if defined.
    self._tokens = self.tokens[:]
    # Populate the lexer with any data we got.
    self.buffer = data

  def Reset(self):
    """Reset the lexer to process a new data feed."""
    # The first state
    self.state = "INITIAL"
    self.state_stack = []

    # The buffer we are parsing now
    self.buffer = ""
    self.error = 0
    self.verbose = 0

    # The index into the buffer where we are currently pointing
    self.processed = 0
    self.processed_buffer = ""

  def NextToken(self):
    """Fetch the next token by trying to match any of the regexes in order."""
    # Nothing in the input stream - no token can match.
    if not self.buffer:
      return

    current_state = self.state
    for token in self._tokens:
      # Does the rule apply to us?
      if token.state_regex and not token.state_regex.match(current_state):
        continue

      if self.verbose:
        logging.debug("%s: Trying to match %r with %r", self.state,
                      self.buffer[:10], token.re_str)

      # Try to match the rule
      m = token.regex.match(self.buffer)
      if not m:
        continue

      if self.verbose:
        logging.debug("%s matched %s", token.re_str, m.group(0))

      # A token matched the empty string. We can not consume the token from the
      # input stream.
      if m.end() == 0:
        raise RuntimeError("Lexer bug! Token can not match the empty string.")

      # The match consumes the data off the buffer (the handler can put it back
      # if it likes)
      self.processed_buffer += self.buffer[:m.end()]
      self.buffer = self.buffer[m.end():]
      self.processed += m.end()

      next_state = token.next_state
      for action in token.actions:
        if self.verbose:
          logging.debug("Calling %s with %s", action, m.group(0))

        # Is there a callback to handle this action?
        cb = getattr(self, action, self.Default)

        # Allow a callback to skip other callbacks.
        try:
          possible_next_state = cb(string=m.group(0), match=m)
          if possible_next_state == "CONTINUE":
            continue
          # Override the state from the Token
          elif possible_next_state:
            next_state = possible_next_state
        except ParseError as e:
          self.Error(e)

      # Update the next state
      if next_state:
        self.state = next_state

      return token

    # Check that we are making progress - if we are too full, we assume we are
    # stuck.
    self.Error("Lexer stuck at state %s" % (self.state))
    self.processed_buffer += self.buffer[:1]
    self.buffer = self.buffer[1:]
    return "Error"

  def Feed(self, data):
    precondition.AssertType(data, unicode)
    self.buffer += data

  def Empty(self):
    return not self.buffer

  def Default(self, **kwarg):
    logging.debug("Default handler: %s", kwarg)

  def Error(self, message=None, weight=1):
    logging.debug("Error(%s): %s", weight, message)
    # Keep a count of errors
    self.error += weight

  def PushState(self, **_):
    """Push the current state on the state stack."""
    if self.verbose:
      logging.debug("Storing state %r", self.state)
    self.state_stack.append(self.state)

  def PopState(self, **_):
    """Pop the previous state from the stack."""
    try:
      self.state = self.state_stack.pop()
      if self.verbose:
        logging.debug("Returned state to %s", self.state)

      return self.state
    except IndexError:
      self.Error("Tried to pop the state but failed - possible recursion error")

  def PushBack(self, string="", **_):
    """Push the match back on the stream."""
    precondition.AssertType(string, unicode)
    self.buffer = string + self.buffer
    self.processed_buffer = self.processed_buffer[:-len(string)]

  def Close(self):
    """A convenience function to force us to parse all the data."""
    while self.NextToken():
      if not self.buffer:
        return


class Expression(object):
  """A class representing an expression."""
  attribute = None
  args = None
  operator = None

  # The expected number of args
  number_of_args = 1

  def __init__(self):
    self.args = []

  def SetAttribute(self, attribute):
    self.attribute = attribute

  def SetOperator(self, operator):
    self.operator = operator

  def AddArg(self, arg):
    """Adds a new arg to this expression.

    Args:
       arg: The argument to add (string).

    Returns:
      True if this arg is the last arg, False otherwise.

    Raises:
      ParseError: If there are too many args.
    """
    self.args.append(arg)
    if len(self.args) > self.number_of_args:
      raise ParseError("Too many args for this expression.")

    elif len(self.args) == self.number_of_args:
      return True

    return False

  def __str__(self):
    return "Expression: (%s) (%s) %s" % (self.attribute, self.operator,
                                         self.args)

  def PrintTree(self, depth=""):
    return "%s %s" % (depth, self)

  def Compile(self, filter_implemention):
    """Given a filter implementation, compile this expression."""
    raise NotImplementedError(
        "%s does not implement Compile." % self.__class__.__name__)


class BinaryExpression(Expression):
  """An expression which takes two other expressions."""

  def __init__(self, operator="", part=None):
    self.operator = operator
    self.args = []
    if part:
      self.args.append(part)
    super(BinaryExpression, self).__init__()

  def __str__(self):
    return "Binary Expression: %s %s" % (self.operator,
                                         [str(x) for x in self.args])

  def AddOperands(self, lhs, rhs):
    if isinstance(lhs, Expression) and isinstance(rhs, Expression):
      self.args.insert(0, lhs)
      self.args.append(rhs)
    else:
      raise ParseError(
          "Expected expression, got %s %s %s" % (lhs, self.operator, rhs))

  def PrintTree(self, depth=""):
    result = "%s%s\n" % (depth, self.operator)
    for part in self.args:
      result += "%s-%s\n" % (depth, part.PrintTree(depth + "  "))

    return result

  def Compile(self, filter_implemention):
    """Compile the binary expression into a filter object."""
    operator = self.operator.lower()
    if operator == "and" or operator == "&&":
      method = "AndFilter"
    elif operator == "or" or operator == "||":
      method = "OrFilter"
    else:
      raise ParseError("Invalid binary operator %s" % operator)

    args = [x.Compile(filter_implemention) for x in self.args]
    return filter_implemention.GetFilter(method)(*args)


class IdentityExpression(Expression):
  """An Expression which always evaluates to True."""

  def Compile(self, filter_implemention):
    return filter_implemention.IdentityFilter()


class SearchParser(Lexer):
  """This parser can parse the mini query language and build an AST.

  Examples of valid syntax:
    filename contains "foo" and (size > 100k or date before "2011-10")
    date between 2011 and 2010
    files older than 1 year
  """

  expression_cls = Expression
  binary_expression_cls = BinaryExpression
  identity_expression_cls = IdentityExpression
  string = ""

  tokens = [
      # Double quoted string
      Token("STRING", "\"", "PopState,StringFinish", None),
      Token("STRING", r"\\(.)", "StringEscape", None),
      Token("STRING", r"[^\\\"]+", "StringInsert", None),

      # Single quoted string
      Token("SQ_STRING", "'", "PopState,StringFinish", None),
      Token("SQ_STRING", r"\\(.)", "StringEscape", None),
      Token("SQ_STRING", r"[^\\']+", "StringInsert", None),

      # TODO(user): Implement a unary not operator.
      # The first thing we see in the initial state takes up to the ATTRIBUTE
      Token("INITIAL", r"(and|or|\&\&|\|\|)", "BinaryOperator", None),
      Token("INITIAL", r"[^\s\(\)]", "PushState,PushBack", "ATTRIBUTE"),
      Token("INITIAL", r"\(", "BracketOpen", None),
      Token("INITIAL", r"\)", "BracketClose", None),
      Token("ATTRIBUTE", r"[\w._0-9]+", "StoreAttribute", "OPERATOR"),
      Token("OPERATOR", r"[a-z0-9<>=\-\+\!\^\&%]+", "StoreOperator",
            "ARG_LIST"),
      Token("OPERATOR", "(!=|[<>=])", "StoreSpecialOperator", "ARG_LIST"),
      Token("ARG_LIST", r"[^\s'\"]+", "InsertArg", None),

      # Start a string.
      Token(".", "\"", "PushState,StringStart", "STRING"),
      Token(".", "'", "PushState,StringStart", "SQ_STRING"),

      # Skip whitespace.
      Token(".", r"\s+", None, None),
  ]

  def __init__(self, data):
    # Holds expression
    self.current_expression = self.expression_cls()
    self.filter_string = data

    # The token stack
    self.stack = []
    Lexer.__init__(self, data)

  def BinaryOperator(self, string=None, **_):
    self.stack.append(self.binary_expression_cls(string))

  def BracketOpen(self, **_):
    self.stack.append("(")

  def BracketClose(self, **_):
    self.stack.append(")")

  def StringStart(self, **_):
    self.string = ""

  def StringEscape(self, string, match, **_):
    """Escape backslashes found inside a string quote.

    Backslashes followed by anything other than ['"rnbt] will just be included
    in the string.

    Args:
       string: The string that matched.
       match: The match object (m.group(1) is the escaped code)
    """
    if match.group(1) in "'\"rnbt":
      self.string += string.decode("string_escape")
    else:
      self.string += string

  def StringInsert(self, string="", **_):
    self.string += string

  def StringFinish(self, **_):
    if self.state == "ATTRIBUTE":
      return self.StoreAttribute(string=self.string)

    elif self.state == "ARG_LIST":
      return self.InsertArg(string=self.string)

  def StoreAttribute(self, string="", **_):
    if self.verbose:
      logging.debug("Storing attribute %r", string)

    # TODO(user): Update the expected number_of_args
    try:
      self.current_expression.SetAttribute(string)
    except AttributeError:
      raise ParseError("Invalid attribute '%s'" % string)

    return "OPERATOR"

  def StoreOperator(self, string="", **_):
    if self.verbose:
      logging.debug("Storing operator %r", string)
    self.current_expression.SetOperator(string)

  def InsertArg(self, string="", **_):
    """Insert an arg to the current expression."""
    if self.verbose:
      logging.debug("Storing Argument %s", utils.SmartUnicode(string))

    # This expression is complete
    if self.current_expression.AddArg(string):
      self.stack.append(self.current_expression)
      self.current_expression = self.expression_cls()
      return self.PopState()

  def _CombineBinaryExpressions(self, operator):
    for i in range(1, len(self.stack) - 1):
      item = self.stack[i]
      if (isinstance(item, BinaryExpression) and item.operator == operator and
          isinstance(self.stack[i - 1], Expression) and
          isinstance(self.stack[i + 1], Expression)):
        lhs = self.stack[i - 1]
        rhs = self.stack[i + 1]

        item.AddOperands(lhs, rhs)
        self.stack[i - 1] = None
        self.stack[i + 1] = None

    self.stack = list(filter(None, self.stack))

  def _CombineParenthesis(self):
    for i in range(len(self.stack) - 2):
      if (self.stack[i] == "(" and self.stack[i + 2] == ")" and
          isinstance(self.stack[i + 1], Expression)):
        self.stack[i] = None
        self.stack[i + 2] = None

    self.stack = list(filter(None, self.stack))

  def Reduce(self):
    """Reduce the token stack into an AST."""
    # Check for sanity
    if self.state != "INITIAL":
      self.Error("Premature end of expression")

    length = len(self.stack)
    while length > 1:
      # Precendence order
      self._CombineParenthesis()
      self._CombineBinaryExpressions("and")
      self._CombineBinaryExpressions("or")

      # No change
      if len(self.stack) == length:
        break
      length = len(self.stack)

    if length != 1:
      self.Error("Illegal query expression")

    return self.stack[0]

  def Error(self, message=None, weight=1):
    raise ParseError(u"%s in position %s: %s <----> %s )" %
                     (utils.SmartUnicode(message), len(self.processed_buffer),
                      self.processed_buffer, self.buffer))

  def Parse(self):
    if not self.filter_string:
      return self.identity_expression_cls()

    self.Close()
    return self.Reduce()
