#!/usr/bin/env python
"""Client actions root module."""

from grr_response_client import actions

REGISTRY: dict[str, type[actions.ActionPlugin]] = {}


def Register(name: str, cls: type[actions.ActionPlugin]) -> None:
  """Registers a client action, optionally overriding its name.

  Args:
    name: Client action name.
    cls: Client action class.
  """
  REGISTRY[name] = cls
