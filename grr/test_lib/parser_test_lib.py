#!/usr/bin/env python
"""A module with utilities for testing parsers."""

import functools
from unittest import mock

from grr_response_core.lib import factory
from grr_response_core.lib import parsers
from grr_response_core.lib.parsers import all as all_parsers


def WithParser(name, parser_cls):
  """Makes given function execute with specified parser registered.

  Args:
    name: A name of the parser.
    parser_cls: A parser class object.

  Returns:
    A decorator function that registers and unregisters the parser.
  """

  def Decorator(func):

    @functools.wraps(func)
    def Wrapper(*args, **kwargs):
      with _ParserContext(name, parser_cls):
        func(*args, **kwargs)

    return Wrapper

  return Decorator


def WithAllParsers(func):
  """Makes given function execute with all known parser registered."""

  @functools.wraps(func)
  def Wrapper(*args, **kwargs):  # pylint: disable=missing-docstring
    with mock.patch.object(parsers, "SINGLE_RESPONSE_PARSER_FACTORY",
                           factory.Factory(parsers.SingleResponseParser)),\
         mock.patch.object(parsers, "SINGLE_FILE_PARSER_FACTORY",
                           factory.Factory(parsers.SingleFileParser)),\
         mock.patch.object(parsers, "MULTI_RESPONSE_PARSER_FACTORY",
                           factory.Factory(parsers.MultiResponseParser)),\
         mock.patch.object(parsers, "MULTI_FILE_PARSER_FACTORY",
                           factory.Factory(parsers.MultiFileParser)):
      all_parsers.Register()
      func(*args, **kwargs)

  return Wrapper


class _ParserContext(object):
  """A context manager class for execution with certain parser registered."""

  def __init__(self, name, parser_cls):
    self._name = name
    self._parser = parser_cls

  def __enter__(self):
    if issubclass(self._parser, parsers.SingleResponseParser):
      parsers.SINGLE_RESPONSE_PARSER_FACTORY.Register(self._name, self._parser)
    if issubclass(self._parser, parsers.SingleFileParser):
      parsers.SINGLE_FILE_PARSER_FACTORY.Register(self._name, self._parser)
    if issubclass(self._parser, parsers.MultiResponseParser):
      parsers.MULTI_RESPONSE_PARSER_FACTORY.Register(self._name, self._parser)
    if issubclass(self._parser, parsers.MultiFileParser):
      parsers.MULTI_FILE_PARSER_FACTORY.Register(self._name, self._parser)

  def __exit__(self, exc_type, exc_value, traceback):
    del exc_type, exc_value, traceback  # Unused.

    if issubclass(self._parser, parsers.SingleResponseParser):
      parsers.SINGLE_RESPONSE_PARSER_FACTORY.Unregister(self._name)
    if issubclass(self._parser, parsers.SingleFileParser):
      parsers.SINGLE_FILE_PARSER_FACTORY.Unregister(self._name)
    if issubclass(self._parser, parsers.MultiResponseParser):
      parsers.MULTI_RESPONSE_PARSER_FACTORY.Unregister(self._name)
    if issubclass(self._parser, parsers.MultiFileParser):
      parsers.MULTI_FILE_PARSER_FACTORY.Unregister(self._name)
