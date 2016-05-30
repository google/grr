#!/usr/bin/env python
"""A quick script that normalizes a config file."""

import logging


import yaml

from grr.lib import flags
from grr.lib import lexer

flags.PARSER.add_argument("filename", type=str, help="Filename to normalize")


class Option(object):

  def __init__(self):
    self.comments = []
    self.name = ""
    self.lines = []
    self.indent = ""
    self.parent = ""

  def __str__(self):
    if self.lines[-1] != "\n":
      self.lines.append("\n")

    # Filter empty lines in comments.
    comments = "".join([x for x in self.comments if x != "\n"])

    indent = self.indent or ""
    return "%s%s%s%s" % (comments, indent, self.name, "".join(self.lines))


class Context(object):
  """A class to represent a context clause."""

  def __init__(self):
    self.name = ""
    self.options = []
    self.subcontexts = []
    self.parent = None
    self.comments = []
    self.indent = ""

  def CheckForRepeatedNames(self, objects):
    names = sorted(objects, key=lambda x: x.name)
    last_name = None
    for x in names:
      if x.name == last_name:
        raise ValueError(x.name)
      last_name = x.name

  def Validate(self):
    """Check the context makes sense."""
    try:
      self.CheckForRepeatedNames(self.subcontexts)
    except ValueError as e:
      raise ValueError("Repeated subcontext name %s in %s" % (e, self.name))

    try:
      self.CheckForRepeatedNames(self.options)
    except ValueError as e:
      raise ValueError("Repeated option name %s in context %s" % (e, self.name))

    for x in self.subcontexts:
      x.Validate()

  def __str__(self):
    indent = self.indent or ""

    # Filter empty lines in comments.
    comments = "".join([x for x in self.comments if x != "\n"])

    options = sorted(self.options, key=lambda x: x.name)
    subcontexts = sorted(self.subcontexts, key=lambda x: x.name)

    result = [str(x) for x in options] + [str(x) for x in subcontexts]
    return "%s%s%s%s" % (comments, indent, self.name, "".join(result))


class YamlConfigLexer(lexer.Lexer):
  """A rough parser that breaks the config into distinct stanzas.

  NOTE: This is _NOT_ a yaml parser. It simply breaks the yaml file into chunks
  which may be rearranged to normalize the file (i.e. sort options). This is
  used to increase readability of the yaml file.
  """
  verbose = False

  tokens = [
      lexer.Token("OPTION", r"( *)[^\n]+\n", "OptionData", None),
      lexer.Token("OPTION", r" +", "OptionIndent", None),
      lexer.Token(None, r" *#[^\n]*\n", "Comment", None),
      lexer.Token(None, r"\n", "NewLine", None),
      lexer.Token(None, r"( *)([A-Z][^\n]+?:[ \n])", "Option", "OPTION"),
      lexer.Token(None, "---\n", "StartDocument", None),
  ]

  def __init__(self, data):
    super(YamlConfigLexer, self).__init__(data)
    self.root = Context()

    self.current_context = self.root
    self.current_context.parent = self.root
    self.current_option = None
    self.current_comments = []

  def StartDocument(self, string=None, **_):
    self.current_comments.append(string)
    self.current_context.comments = self.current_comments
    self.current_comments = []

  def PushOptionToContext(self):
    if self.current_option:
      self.current_context.options.append(self.current_option)
      self.current_option.parent = self.current_context

      self.current_option = None

  def Comment(self, string=None, **_):
    # A comment represents the end of the previous stanza and the start of the
    # new stanza.
    self.PushOptionToContext()
    self.current_comments.append(string)

  def NewLine(self, string=None, **_):
    # New lines are allowed between a comment and its following stanza.
    if self.current_option is None:
      self.current_comments.append(string)

    else:
      # Otherwise its considered part of the previous option - for options with
      # multiple lines.
      self.current_option.lines.append(string)

  def Option(self, match=None, string=None):
    """A New option is detected."""
    # Current line indent.
    indent = match.group(1)

    # Push the previous option to the current context.
    self.PushOptionToContext()

    # Current indent is smaller than the current context, this line belongs to a
    # parent context. We find the context this line belongs to.
    if indent <= self.current_context.indent:
      # Switch the current context to match the indent.
      self.current_context = self.FindContextForOption(indent)

    # Currently we tell the difference between an option and a context name by
    # the inclusion of a "." in the name. This means contexts can not have a
    # . in them,
    if "." in string:  # Regular option.
      self.current_option = Option()
      self.current_option.name = match.group(2)
      self.current_option.indent = match.group(1)
      self.current_option.comments = self.current_comments
      self.current_comments = []
      logging.debug("Added Option %s to context %s", string,
                    self.current_context.name)

    else:  # This is a new context.
      context = Context()
      context.name = match.group(2)
      context.comments = self.current_comments
      context.indent = match.group(1)

      # This context is a sibling to the previous one.
      if indent == self.current_context.indent:
        context.parent = self.current_context.parent

        # This context is deeper than the previous one
      else:
        context.parent = self.current_context

      self.current_context.subcontexts.append(context)
      self.current_context = context
      self.current_comments = []

      return "INITIAL"

  def Error(self, message):
    raise RuntimeError(message)

  def FindContextForOption(self, indent):
    """Returns the context which contains this option's indent."""
    context = self.current_context
    while indent <= context.indent and context != self.root:
      context = context.parent

    return context

  def OptionData(self, string=None, match=None):
    # Current line indent is the same as the option name.
    indent = match.group(1)

    # This data is on the same line as the option name, it must belong to the
    # current option.
    if not self.current_option.lines:
      self.current_option.lines.append(string)

    # Current indent is less or equal to the option indent - it can not belong
    # to the present option.
    elif indent <= self.current_option.indent:
      self.PushBack(string)
      return "INITIAL"

    # Indent is bigger than this option - it represents data in this option.
    else:
      self.current_option.lines.append(string)

  def OptionIndent(self, string=None, **_):
    if not self.current_option:
      self.current_comments.append(string)

    else:
      # An indent was found with the same indent as last option - this
      # represents the end of this option and the start of the next option.
      if string == self.current_option.indent:
        self.PushBack(string)
        return "INITIAL"

      else:
        self.current_option.lines.append(string)

  def Close(self):
    super(YamlConfigLexer, self).Close()
    self.PushOptionToContext()


def main(_):
  data = open(flags.FLAGS.filename, "rb").read()
  parser = YamlConfigLexer(data)
  parser.Close()

  # First check that we actually parsed it correctly.
  normalized_form = unicode(parser.root)
  normalized_data = yaml.safe_load(normalized_form)

  if normalized_data != yaml.safe_load(data):
    raise RuntimeError("Error in parsing and normalizing yaml file.")

  # Check the config file for sanity.
  parser.root.Validate()

  print normalized_form


if __name__ == "__main__":
  flags.StartMain(main)
