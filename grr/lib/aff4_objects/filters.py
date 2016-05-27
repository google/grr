#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.
"""The main data store."""

import operator
import re

from grr.lib import aff4
from grr.lib import utils


class IdentityFilter(aff4.AFF4Filter):
  """Just pass all objects."""

  def FilterOne(self, fd):
    return fd

  def Filter(self, subjects):
    return subjects


class HasPredicateFilter(aff4.AFF4Filter):
  """Returns only the documents which have the predicate defined."""

  def __init__(self, attribute_name):
    self.attribute_name = attribute_name

  def FilterOne(self, subject):
    if subject.Get(self.attribute_name):
      return subject

    return False


class AndFilter(aff4.AFF4Filter):
  """A logical And operator."""

  def __init__(self, *parts):
    self.parts = parts

  def FilterOne(self, subject):
    result = subject
    for part in self.parts:
      result = part.FilterOne(result)
      if not result:
        return False

    return result

  def Compile(self, filter_cls):
    return getattr(filter_cls, self.__class__.__name__)(*[x.Compile(filter_cls)
                                                          for x in self.args])


class OrFilter(AndFilter):
  """A logical Or operator."""

  def FilterOne(self, subject):
    for part in self.parts:
      result = part.FilterOne(subject)
      # If any of the parts is not False, return it.
      if result:
        return result


class PredicateLessThanFilter(aff4.AFF4Filter):
  """Filter the predicate according to the operator."""
  operator_function = operator.lt

  def __init__(self, attribute_name, value):
    self.value = value
    self.attribute_name = attribute_name

  def FilterOne(self, subject):
    predicate_value = subject.Get(self.attribute_name)
    if predicate_value and self.operator_function(predicate_value, self.value):
      return subject


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

  def FilterOne(self, subject):
    # If the regex is empty, this is a passthrough.
    if self.regex is None:
      return subject
    else:
      predicate_value = subject.Get(self.attribute_name)
      if (predicate_value and
          self.regex.search(utils.SmartUnicode(predicate_value))):
        return subject


class SubjectContainsFilter(aff4.AFF4Filter):
  """Applies a RegEx to the subject name."""

  def __init__(self, regex):
    """Constructor.

    Regex matching occurs on unicode sequences only.

    Args:
       regex: For the filter to apply, subject must match this regex.
    """
    self.regex_text = utils.SmartUnicode(regex)
    self.regex = re.compile(self.regex_text)
    super(SubjectContainsFilter, self).__init__()

  def FilterOne(self, subject):
    if self.regex.search(utils.SmartUnicode(subject.urn)):
      return subject
