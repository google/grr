#!/usr/bin/env python
"""Module for API Call Router registry."""
from typing import Dict, Text, Type

from grr_response_server.gui import api_call_router

_API_CALL_ROUTER_REGISTRY: Dict[str, Type[api_call_router.ApiCallRouter]] = {}


def RegisterApiCallRouter(name: str,
                          cls: Type[api_call_router.ApiCallRouter]) -> None:
  """Registers an API call router, optionally overriding its name.

  Args:
    name: API call router name.
    cls: API call router class.
  """
  _API_CALL_ROUTER_REGISTRY[name] = cls


def UnregisterApiCallRouter(name: str) -> None:
  """Unregisters an API call router.

  Args:
    name: API call router name.
  """
  del _API_CALL_ROUTER_REGISTRY[name]


def GetRouterClass(router_name: Text) -> Type[api_call_router.ApiCallRouter]:
  return _API_CALL_ROUTER_REGISTRY[router_name]
