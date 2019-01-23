#!/usr/bin/env python
"""A module to allow option processing from files or registry."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import pdb

from absl import app
from absl import flags
from absl.testing import flagsaver

from typing import Text

FLAGS = flags.FLAGS

# TODO(hanuszczak): Use `absl.flags` directly instead of delegating by the
# functions below.


# Helper functions for setting options on the global parser object
# pylint: disable=g-bad-name,redefined-builtin
def DEFINE_string(longopt, default, help):
  flags.DEFINE_string(longopt, default, help)


def DEFINE_multi_string(shortopt, longopt, help):
  flags.DEFINE_multi_string(longopt, [], help, short_name=shortopt)


def DEFINE_bool(longopt, default, help, *args, **kwargs):
  flags.DEFINE_bool(longopt, default, help, *args, **kwargs)


def DEFINE_integer(longopt, default, help):
  flags.DEFINE_integer(longopt, default, help)


def DEFINE_float(longopt, default, help):
  flags.DEFINE_float(longopt, default, help)


def DEFINE_enum(longopt, default, choices, help, type=Text):
  del type  # Unused.
  flags.DEFINE_enum(longopt, default, choices, help)


def DEFINE_list(longopt, default, help):
  flags.DEFINE_list(longopt, default, help)


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
    allow_override_cpp=True,
    help="Print the GRR version number and exit immediately.")


def FlagOverrider(**flag_kwargs):
  """A Helpful decorator which can switch the flag values temporarily."""
  return flagsaver.flagsaver(**flag_kwargs)


def StartMain(main, requires_root=False):
  """The main entry point to start applications.

  Parses flags and catches all exceptions for debugging.

  Args:
     main: A main function to call.
     requires_root: Whether the application needs to be run with root
       privileges.
  """
  try:
    app.run(main)
  except Exception:
    if FLAGS.debug:
      pdb.post_mortem()

    raise
