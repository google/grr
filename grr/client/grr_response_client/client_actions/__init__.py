#!/usr/bin/env python
"""Client actions root module."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

from typing import Dict, Text, Type

from grr_response_client import actions

REGISTRY = {}  # type: Dict[Text, Type[actions.ActionPlugin]]


def Register(name, cls):
  """Registers a client action, optionally overriding its name.

  Args:
    name: Client action name.
    cls: Client action class.
  """
  REGISTRY[name] = cls
