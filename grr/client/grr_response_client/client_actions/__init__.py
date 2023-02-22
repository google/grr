#!/usr/bin/env python
"""Client actions root module."""

from typing import Dict, Text, Type

from grr_response_client import actions

REGISTRY: Dict[Text, Type[actions.ActionPlugin]] = {}


def Register(name: Text, cls: Type[actions.ActionPlugin]) -> None:
  """Registers a client action, optionally overriding its name.

  Args:
    name: Client action name.
    cls: Client action class.
  """
  REGISTRY[name] = cls
