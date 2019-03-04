#!/usr/bin/env python
"""A module to allow option processing from files or registry."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl import flags

FLAGS = flags.FLAGS

# TODO(hanuszczak): Use `absl.flags` directly instead of delegating by the
# functions below.


# Helper functions for setting options on the global parser object
# pylint: disable=g-bad-name,redefined-builtin
def DEFINE_string(longopt, default, help):
  flags.DEFINE_string(longopt, default, help)


def DEFINE_multi_string(longopt, default, help, *args, **kwargs):
  flags.DEFINE_multi_string(longopt, default, help, *args, **kwargs)


def DEFINE_bool(longopt, default, help, *args, **kwargs):
  flags.DEFINE_bool(longopt, default, help, *args, **kwargs)


def DEFINE_integer(longopt, default, help):
  flags.DEFINE_integer(longopt, default, help)


def DEFINE_float(longopt, default, help):
  flags.DEFINE_float(longopt, default, help)


def DEFINE_enum(longopt, default, choices, help):
  flags.DEFINE_enum(longopt, default, choices, help)


def DEFINE_list(longopt, default, help):
  flags.DEFINE_list(longopt, default, help)


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
