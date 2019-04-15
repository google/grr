#!/usr/bin/env python
"""Mixin class to be used in tests for DB implementations."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

import itertools
import random

from future.builtins import range
from typing import Any, Callable, Dict, Iterable, Optional, Text

from grr_response_server.databases import db


class QueryTestHelpersMixin(object):
  """Mixin containing helper methods for list/query methods tests."""

  def TestOffsetAndCount(self,
                         fetch_all_fn,
                         fetch_range_fn,
                         error_desc = None):
    """Tests a DB API method with different offset/count combinations.

    This helper method works by first fetching all available objects with
    fetch_all_fn and then fetching all possible ranges using fetch_fn. The test
    passes if subranges returned by fetch_fn match subranges of values in
    the list returned by fetch_all_fn.

    Args:
      fetch_all_fn: Function without arguments that fetches all available
        objects using the API method that's being tested.
      fetch_range_fn: Function that calls an API method that's being tested
        passing 2 positional arguments: offset and count. It should return a
          list of objects.
      error_desc: Optional string to be used in error messages. May be useful to
        identify errors from a particular test.
    """
    all_objects = fetch_all_fn()
    self.assertNotEmpty(all_objects,
                        "Fetched objects can't be empty (%s)." % error_desc)

    for i in range(len(all_objects)):
      for l in range(1, len(all_objects) + 1):
        results = fetch_range_fn(i, l)
        expected = all_objects[i:i + l]

        self.assertListEqual(
            results, expected,
            "Results differ from expected (offset %d, count %d%s): %s vs %s" %
            (i, l,
             (", " + error_desc) if error_desc else "", results, expected))

  def TestFilterCombinations(self,
                             fetch_fn,
                             conditions,
                             error_desc = None):
    """Tests a DB API method with different keyword arguments combinations.

    This test method works by fetching sets of objects for each individual
    condition and then checking that combinations of conditions produce
    expected sets of objects.

    Args:
      fetch_fn: Function accepting keyword "query filter" arguments and
        returning a list of fetched objects. When called without arguments,
        fetch_fn is expected to return all available objects.
      conditions: A dictionary of key -> value, where key is a string
        identifying a keyword argument to be passed to fetch_fn and value is a
        value to be passed. All possible permutations of conditions will be
        tried on fetch_fn.
      error_desc: Optional string to be used in error messages. May be useful to
        identify errors from a particular test.
    """
    perms = list(
        itertools.chain.from_iterable([
            itertools.combinations(sorted(conditions.keys()), i)
            for i in range(1,
                           len(conditions) + 1)
        ]))
    self.assertNotEmpty(perms)

    all_objects = fetch_fn()
    expected_objects = {}
    for k, v in conditions.items():
      expected_objects[k] = fetch_fn(**{k: v})

    for condition_perm in perms:
      expected = all_objects
      kw_args = {}
      for k in condition_perm:
        expected = [e for e in expected if e in expected_objects[k]]
        kw_args[k] = conditions[k]

      got = fetch_fn(**kw_args)

      # Make sure that the order of keys->values is stable in the error message.
      kw_args_str = ", ".join(
          "%r: %r" % (k, kw_args[k]) for k in sorted(kw_args))
      self.assertListEqual(
          got, expected, "Results differ from expected ({%s}%s): %s vs %s" %
          (kw_args_str,
           (", " + error_desc) if error_desc else "", got, expected))

  def TestFilterCombinationsAndOffsetCount(
      self,
      fetch_fn,
      conditions,
      error_desc = None):
    """Tests a DB API methods with combinations of offset/count args and kwargs.

    This test methods works in 2 steps:
    1. It tests that different conditions combinations work fine when offset
    and count are 0 and db.MAX_COUNT respectively.
    2. For every condition combination it tests all possible offset and count
    combinations to make sure correct subsets of results are returned.

    Args:
      fetch_fn: Function accepting positional offset and count arguments and
        keyword "query filter" arguments and returning a list of fetched
        objects.
      conditions: A dictionary of key -> value, where key is a string
        identifying a keyword argument to be passed to fetch_fn and value is a
        value to be passed. All possible permutations of conditions will be
        tried on fetch_fn.
      error_desc: Optional string to be used in error messages. May be useful to
        identify errors from a particular test.
    """
    self.TestFilterCombinations(
        lambda **kw_args: fetch_fn(0, db.MAX_COUNT, **kw_args),
        conditions,
        error_desc=error_desc)

    perms = list(
        itertools.chain.from_iterable([
            itertools.combinations(sorted(conditions.keys()), i)
            for i in range(1,
                           len(conditions) + 1)
        ]))
    self.assertNotEmpty(perms)

    for condition_perm in perms:
      kw_args = {}
      for k in condition_perm:
        kw_args[k] = conditions[k]

      # Make sure that the order of keys->values is stable in the error message.
      kw_args_str = ", ".join(
          "%r: %r" % (k, kw_args[k]) for k in sorted(kw_args))
      self.TestOffsetAndCount(
          lambda: fetch_fn(0, db.MAX_COUNT, **kw_args),  # pylint: disable=cell-var-from-loop
          lambda offset, count: fetch_fn(offset, count, **kw_args),  # pylint: disable=cell-var-from-loop
          error_desc="{%s}%s" %
          (kw_args_str, ", " + error_desc) if error_desc else "")


def InitializeClient(db_obj, client_id=None):
  """Initializes a test client.

  Args:
    db_obj: A database object.
    client_id: A specific client id to use for initialized client. If none is
      provided a randomly generated one is used.

  Returns:
    A client id for initialized client.
  """
  if client_id is None:
    client_id = "C."
    for _ in range(16):
      client_id += random.choice("0123456789abcdef")

  db_obj.WriteClientMetadata(client_id, fleetspeak_enabled=True)
  return client_id
