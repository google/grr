#!/usr/bin/env python
# Copyright 2011 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A module to allow option processing from files or registry."""


import argparse
import pdb
import sys




# A global flags parser
class GRRArgParser(argparse.ArgumentParser):

  def parse_args(self, **kwargs):
    global FLAGS
    FLAGS = super(GRRArgParser, self).parse_args(**kwargs)
    return FLAGS


PARSER = GRRArgParser(description="GRR Rapid Response")
FLAGS = None



# Helper functions for setting options on the global parser object
# pylint: disable=g-bad-name,redefined-builtin
def DEFINE_string(longopt, default, help):
  PARSER.add_argument("--%s" % longopt, default=default, type=str,
                      help=help)


def DEFINE_bool(longopt, default, help):
  PARSER.add_argument("--%s" % longopt, default=default, action="store_true",
                      help=help)


def DEFINE_integer(longopt, default, help):
  PARSER.add_argument("--%s" % longopt, default=default, type=int,
                      help=help)


def DEFINE_float(longopt, default, help):
  PARSER.add_argument("--%s" % longopt, default=default, type=float,
                      help=help)


def DEFINE_enum(longopt, default, choices, help):
  PARSER.add_argument("--%s" % longopt, default=default, choices=choices,
                      type="choice", help=help)


class ListParser(argparse.Action):
  """Parse input as a comma separated list of strings."""

  def __call__(self, parser, namespace, values, option_string=None):
    setattr(namespace, self.dest, values.split(","))


def DEFINE_list(longopt, default, help):
  PARSER.add_argument("--%s" % longopt, default=default,
                      action=ListParser, help=help)

# pylint: enable=g-bad-name,redefined-builtin


def StartMain(main, argv=None):
  """The main entry point to start applications.

  Parses flags and catches all exceptions for debugging.

  Args:
     main: A main function to call.
     argv: The argv to parse. Default from sys.argv.
  """
  PARSER.parse_args(args=argv)

  # Call the main function
  try:
    main([sys.argv[0]])
  except Exception:
    if FLAGS.debug:
      pdb.post_mortem()

    raise
