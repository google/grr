#!/usr/bin/env python
"""A module with utilities for string interpolation."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

import collections
import re

from future.builtins import str
from future.utils import iteritems
from future.utils import iterkeys
from typing import Any
from typing import AnyStr
from typing import Dict
from typing import Generic
from typing import Iterator
from typing import Match
from typing import NewType
from typing import Set
from typing import Text

from grr_response_core.lib.util import collection

VarId = NewType("VarId", Text)
ScopeId = NewType("ScopeId", Text)

VarConfig = Dict[VarId, Any]
ScopeConfig = Dict[ScopeId, VarConfig]


class Substitution(object):
  """A class representing substitution environment."""

  def __init__(self, var_config, scope_config):
    """Initializes the substitution environment.

    Args:
      var_config: A configuration (concrete values) of pattern variables.
      scope_config: A configuration (concrete values) of pattern scopes.
    """
    self._substs = {}
    self._var_config = var_config
    self._scope_config = scope_config

    for var_id, var_value in iteritems(var_config):
      key = "%%{var}%%".format(var=var_id)
      self._substs[key] = str(var_value)

    for scope_id, var_config in iteritems(scope_config):
      for var_id, var_value in iteritems(var_config):
        key = "%%{scope}.{var}%%".format(scope=scope_id, var=var_id)
        self._substs[key] = str(var_value)

  def Substitute(self, pattern):
    """Formats given pattern with this substitution environment.

    A pattern can contain placeholders for variables (`%%foo%%`) and scopes
    (`%%bar.baz%%`) that are replaced with concrete values in this substiution
    environment (specified in the constructor).

    Args:
      pattern: A pattern with placeholders to substitute.

    Returns:
      A pattern with placeholders substituted with concrete values.
    """
    if isinstance(pattern, bytes):
      substs = [re.escape(subst.encode("ascii")) for subst in self._substs]
      regex = re.compile(b"|".join(substs))

      def Replacement(match):
        key = match.group(0).decode("ascii")
        return self._substs[key].encode("utf-8")

    elif isinstance(pattern, Text):
      substs = [re.escape(subst) for subst in self._substs]
      regex = re.compile("|".join(substs))

      def Replacement(match):
        key = match.group(0)
        return self._substs[key]

    else:
      raise TypeError("Unexpected pattern type '{}'".format(type(pattern)))

    if not substs:
      return pattern
    else:
      return regex.sub(Replacement, pattern)


class Interpolator(Generic[AnyStr]):
  """A string interpolator that allows multiple values for given placeholder.

  This can be though of as extended version of format strings that allow many
  values to be plugged into a single placeholder yielding multiple possible
  output strings.

  Format string use `%%` to denote placeholders. For example, `%%foo%%` refers
  to a variable `foo` and `%%bar.baz%%` refers to a variable `baz` in scope
  `bar`.
  """

  _VAR_PLACEHOLDER_PATTERN = r"%%(?P<var>\w+)%%"
  _SCOPE_PLACEHOLDER_PATTERN = r"%%(?P<scope>\w+)\.(?P<var>\w+)%%"

  def __init__(self, pattern):
    """Initializes the interpolator.

    Args:
      pattern: A string (either of unicode or byte characters) with placeholders
        to format.
    """
    super(Interpolator, self).__init__()
    self._pattern = pattern

    if isinstance(pattern, bytes):
      var_regex = re.compile(self._VAR_PLACEHOLDER_PATTERN.encode("ascii"))
      scope_regex = re.compile(self._SCOPE_PLACEHOLDER_PATTERN.encode("ascii"))
      decoder = lambda _: _.decode("ascii")
    elif isinstance(pattern, Text):
      var_regex = re.compile(self._VAR_PLACEHOLDER_PATTERN)
      scope_regex = re.compile(self._SCOPE_PLACEHOLDER_PATTERN)
      decoder = lambda _: _
    else:
      raise TypeError("Unexpected pattern type '{}'".format(type(pattern)))

    self._vars = set()
    for matches in var_regex.finditer(pattern):
      var = matches.group("var")
      self._vars.add(decoder(var))

    self._scopes = dict()
    for matches in scope_regex.finditer(pattern):
      scope = matches.group("scope")
      var = matches.group("var")
      self._scopes.setdefault(decoder(scope), set()).add(decoder(var))

    self._var_bindings = collections.defaultdict(lambda: [])
    self._scope_bindings = collections.defaultdict(lambda: [])

  def Vars(self):
    """A set of variable names of the interpolation pattern."""
    return set(self._vars)

  def Scopes(self):
    """A set of scope names of the interpolation pattern."""
    return set(self._scopes.keys())

  def ScopeVars(self, vid):
    """A set of variables names for given scope of the interpolation pattern."""
    return set(self._scopes[vid])

  def BindVar(self, var_id, value):
    """Associates a value with given variable.

    This can be called multiple times to associate multiple values.

    Args:
      var_id: A variable id to bind the values to.
      value: A value to bind to the specified variable.

    Raises:
      KeyError: If given variable is not specified in the pattern.
    """
    if var_id not in self._vars:
      raise KeyError(var_id)

    self._var_bindings[var_id].append(value)

  def BindScope(self, scope_id, values):
    """Associates given values with given scope.

    This can be called multiple times to associate multiple values.

    Args:
      scope_id: A scope id to bind the values to.
      values: A mapping from scope variable ids to values to bind in scope.

    Raises:
      KeyError: If given scope or scope variable is not specified in the
        pattern.
    """
    if scope_id not in self._scopes:
      raise KeyError(scope_id)

    keys = set(iterkeys(values))
    if keys != self._scopes[scope_id]:
      raise KeyError(keys ^ self._scopes[scope_id])

    self._scope_bindings[scope_id].append(values)

  def Interpolate(self):
    """Interpolates the pattern.

    Yields:
      All possible interpolation results.
    """
    for var_config in collection.DictProduct(self._var_bindings):
      for scope_config in collection.DictProduct(self._scope_bindings):
        subst = Substitution(var_config=var_config, scope_config=scope_config)
        yield subst.Substitute(self._pattern)
