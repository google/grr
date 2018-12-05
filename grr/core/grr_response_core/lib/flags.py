#!/usr/bin/env python
"""A module to allow option processing from files or registry."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import argparse
import copy
import pdb
import re
import sys


from future.utils import iteritems



# A global flags parser
class GRRArgParser(argparse.ArgumentParser):
  pass


PARSER = GRRArgParser(description="GRR Rapid Response")
FLAGS = None


# Helper functions for setting options on the global parser object
# pylint: disable=g-bad-name,redefined-builtin
def DEFINE_string(longopt, default, help):
  PARSER.add_argument("--%s" % longopt, default=default, type=str, help=help)


def DEFINE_multi_string(shortopt, longopt, help):
  PARSER.add_argument(
      "-%s" % shortopt,
      "--%s" % longopt,
      default=[],
      action="append",
      help=help)


def DEFINE_bool(longopt, default, help):
  PARSER.add_argument(
      "--%s" % longopt, dest=longopt, action="store_true", help=help)

  PARSER.set_defaults(**{longopt: default})  # pytype: disable=wrong-arg-types


def DEFINE_integer(longopt, default, help):
  PARSER.add_argument("--%s" % longopt, default=default, type=int, help=help)


def DEFINE_float(longopt, default, help):
  PARSER.add_argument("--%s" % longopt, default=default, type=float, help=help)


def DEFINE_enum(longopt, default, choices, help, type=unicode):
  PARSER.add_argument(
      "--%s" % longopt, default=default, choices=choices, type=type, help=help)


class ListParser(argparse.Action):
  """Parse input as a comma separated list of strings."""

  def __call__(self, parser, namespace, values, option_string=None):
    setattr(namespace, self.dest, values.split(","))


def DEFINE_integer_list(longopt, default, help):
  PARSER.add_argument(
      "--%s" % longopt, default=default, type=int, action=ListParser, help=help)


def DEFINE_list(longopt, default, help):
  PARSER.add_argument(
      "--%s" % longopt, default=default, action=ListParser, help=help)


DEFINE_bool("verbose", default=False, help="Turn on verbose logging.")

DEFINE_bool(
    "debug",
    default=False,
    help="When an unhandled exception occurs break in the debugger.")

# TODO(hanuszczak): The `version` flag is relevant only for entry points and
# should be defined separately for each. However, since currently we have a case
# where one module has multiple entry points (`grr_server`), this cannot be done
# due to conflicting flag definitions. Once that issue is resolved, this can be
# moved appropriately.
DEFINE_bool(
    "version",
    default=False,
    help="Print the GRR version number and exit immediately.")


def FlagOverrider(**flag_kwargs):
  """A Helpful decorator which can switch the flag values temporarily."""

  def Decorator(f):
    """Allow a function to safely change flags, restoring them on return."""

    def Decorated(*args, **kwargs):
      global FLAGS

      old_flags = copy.copy(FLAGS)

      for k, v in iteritems(flag_kwargs):
        setattr(FLAGS, k, v)

      try:
        return f(*args, **kwargs)
      finally:
        FLAGS = old_flags

    return Decorated

  return Decorator


def Initialize():
  """Parses the arguments and setups the `FLAGS` namespace.

  Returns:
    A list of extra arguments that were not recognized by the parser.
  """
  global FLAGS
  FLAGS, extra_args = PARSER.parse_known_args()
  return extra_args


def StartMain(main):
  """The main entry point to start applications.

  Parses flags and catches all exceptions for debugging.

  Args:
     main: A main function to call.
  """
  extra_args = Initialize()

  exec_name = sys.argv[0].decode("utf-8")
  sys.argv = [exec_name.encode("utf-8")] + extra_args

  # Call the main function
  try:
    main(sys.argv)
  except Exception:
    if FLAGS.debug:
      pdb.post_mortem()

    raise
