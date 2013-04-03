#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.
"""The main data store."""

import operator
import re

from grr.lib import aff4
from grr.lib import utils


class IdentityFilter(aff4.AFF4Filter):
  """Just pass all objects."""

  def Filter(self, subjects):
    return subjects


class HasPredicateFilter(aff4.AFF4Filter):
  """Returns only the documents which have the predicate defined."""

  def __init__(self, attribute_name):
    self.attribute_name = attribute_name

  def Filter(self, subjects):
    attribute_name = self.attribute_name
    for subject in subjects:
      if subject.Get(attribute_name):
        yield subject


class AndFilter(aff4.AFF4Filter):
  """A logical And operator."""

  def __init__(self, *parts):
    self.parts = parts

  def Filter(self, subjects):
    result = subjects
    for part in self.parts:
      result = list(part.Filter(result))

    return result or []

  def Compile(self, filter_cls):
    return getattr(filter_cls, self.__class__.__name__)(
        *[x.Compile(filter_cls) for x in self.args])


class OrFilter(AndFilter):
  """A logical Or operator."""

  def Filter(self, subjects):
    for subject in subjects:
      for part in self.parts:
        if list(part.Filter([subject])):
          yield subject
          break


class PredicateLessThanFilter(aff4.AFF4Filter):
  """Filter the predicate according to the operator."""
  operator_function = operator.lt

  def __init__(self, attribute_name, value):
    self.value = value
    self.attribute_name = attribute_name

  def Filter(self, subjects):
    for subject in subjects:
      predicate_value = subject.Get(self.attribute_name)
      if predicate_value and self.operator_function(
          predicate_value, self.value):
        yield subject


class PredicateGreaterThanFilter(PredicateLessThanFilter):
  operator_function = operator.gt


class PredicateGreaterEqualFilter(PredicateLessThanFilter):
  operator_function = operator.ge


class PredicateLesserEqualFilter(PredicateLessThanFilter):
  operator_function = operator.le


class PredicateNumericEqualFilter(PredicateLessThanFilter):
  operator_function = operator.eq


class PredicateEqualFilter(PredicateLessThanFilter):
  operator_function = operator.eq


class PredicateContainsFilter(PredicateLessThanFilter):
  """Applies a RegEx on the content of an attribute."""

  # The compiled regex
  regex = None

  def __init__(self, attribute_name, value):
    super(PredicateContainsFilter, self).__init__(attribute_name, value)
    if value:
      self.regex = re.compile(value)

  def Filter(self, subjects):
    for subject in subjects:
      # If the regex is empty, this is a passthrough.
      if self.regex is None:
        yield subject
      else:
        predicate_value = subject.Get(self.attribute_name)
        if (predicate_value and
            self.regex.search(utils.SmartUnicode(predicate_value))):
          yield subject


class SubjectContainsFilter(aff4.AFF4Filter):
  """Applies a RegEx to the subject name."""

  def __init__(self, regex):
    """Constructor.

    Args:
       regex: For the filter to apply, subject must match this regex.
    """
    self.regex = re.compile(regex)
    super(SubjectContainsFilter, self).__init__()

  def Filter(self, subjects):
    for subject in subjects:
      if self.regex.search(utils.SmartUnicode(subject.urn)):
        yield subject
