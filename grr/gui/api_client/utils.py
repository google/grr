#!/usr/bin/env python
"""Utility functions and classes for GRR API client library."""

import itertools

from google.protobuf import symbol_database


class ItemsIterator(object):
  """Iterator object with a total_count property."""

  def __init__(self, items=None, total_count=None):
    super(ItemsIterator, self).__init__()

    self.items = items
    self.total_count = total_count

  def __iter__(self):
    for i in self.items:
      yield i


def MapItemsIterator(function, items):
  """Maps ItemsIterator via given function."""
  return ItemsIterator(items=itertools.imap(function, items),
                       total_count=items.total_count)


AFF4_PREFIX = "aff4:/"


def UrnToClientId(urn):
  """Converts given URN string to a client id string."""
  if urn.startswith(AFF4_PREFIX):
    urn = urn[len(AFF4_PREFIX):]

  components = urn.split("/")
  return components[0]


def UrnToFlowId(urn):
  """Converts given URN string to a flow id string."""
  components = urn.split("/")
  return components[-1]


TYPE_URL_PREFIX = "type.googleapis.com/"


def GetTypeUrl(proto):
  """Returns type URL for a given proto."""

  return TYPE_URL_PREFIX + proto.DESCRIPTOR.full_name


def TypeUrlToMessage(type_url):
  """Returns a message instance corresponding to a given type URL."""

  if not type_url.startswith(TYPE_URL_PREFIX):
    raise ValueError("Type URL has to start with a prefix %s: %s" %
                     (TYPE_URL_PREFIX, type_url))

  full_name = type_url[len(TYPE_URL_PREFIX):]
  return symbol_database.Default().GetSymbol(full_name)()
