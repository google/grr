#!/usr/bin/env python
"""A module to allow option processing from files or registry."""


import argparse
import copy
import pdb
import sys



# A global flags parser
class GRRArgParser(argparse.ArgumentParser):
  pass


PARSER = GRRArgParser(description="GRR Rapid Response")
FLAGS = None


# Helper functions for setting options on the global parser object
# pylint: disable=g-bad-name,redefined-builtin
def DEFINE_string(longopt, default, help):
  PARSER.add_argument("--%s" % longopt, default=default, type=str, help=help)


def DEFINE_bool(longopt, default, help):
  PARSER.add_argument("--%s" % longopt,
                      dest=longopt,
                      action="store_true",
                      help=help)

  PARSER.set_defaults(**{longopt: default})


def DEFINE_integer(longopt, default, help):
  PARSER.add_argument("--%s" % longopt, default=default, type=int, help=help)


def DEFINE_float(longopt, default, help):
  PARSER.add_argument("--%s" % longopt, default=default, type=float, help=help)


def DEFINE_enum(longopt, default, choices, help, type=unicode):
  PARSER.add_argument("--%s" % longopt,
                      default=default,
                      choices=choices,
                      type=type,
                      help=help)


class ListParser(argparse.Action):
  """Parse input as a comma separated list of strings."""

  def __call__(self, parser, namespace, values, option_string=None):
    setattr(namespace, self.dest, values.split(","))


def DEFINE_integer_list(longopt, default, help):
  PARSER.add_argument("--%s" % longopt,
                      default=default,
                      type=int,
                      action=ListParser,
                      help=help)


def DEFINE_list(longopt, default, help):
  PARSER.add_argument("--%s" % longopt,
                      default=default,
                      action=ListParser,
                      help=help)


DEFINE_bool("verbose", default=False, help="Turn of verbose logging.")

DEFINE_bool("debug",
            default=False,
            help="When an unhandled exception occurs break in the "
            "debugger.")


def FlagOverrider(**flag_kwargs):
  """A Helpful decorator which can switch the flag values temporarily."""

  def Decorator(f):
    """Allow a function to safely change flags, restoring them on return."""

    def Decorated(*args, **kwargs):
      global FLAGS

      old_flags = copy.copy(FLAGS)

      for k, v in flag_kwargs.items():
        setattr(FLAGS, k, v)

      try:
        return f(*args, **kwargs)
      finally:
        FLAGS = old_flags

    return Decorated

  return Decorator


def StartMain(main, argv=None):
  """The main entry point to start applications.

  Parses flags and catches all exceptions for debugging.

  Args:
     main: A main function to call.
     argv: The argv to parse. Default from sys.argv.
  """
  global FLAGS

  FLAGS = PARSER.parse_args(args=argv)

  # Call the main function
  try:
    main([sys.argv[0]])
  except Exception:
    if FLAGS.debug:
      pdb.post_mortem()

    raise
