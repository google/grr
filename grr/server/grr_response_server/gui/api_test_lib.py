#!/usr/bin/env python
"""Base test classes for API handlers tests."""

import functools
from typing import Type

from grr_response_server.gui import api_call_context
# This import guarantees that all API-related RDF types will get imported
# (as they're all references by api_call_router).
# pylint: disable=unused-import
from grr_response_server.gui import api_call_router
# pylint: enable=unused-import
from grr_response_server.gui import api_call_router_registry
from grr.test_lib import acl_test_lib
from grr.test_lib import test_lib


class ApiCallHandlerTest(test_lib.GRRBaseTest):

  def setUp(self):
    super().setUp()
    # The user we use for API tests.
    self.context = api_call_context.ApiCallContext("api_test_user")
    self.test_username = self.context.username
    acl_test_lib.CreateUser(self.context.username)


def WithApiCallRouter(
    name, api_call_router_cls: Type[api_call_router.ApiCallRouter]
):
  """Makes given function execute with specified router registered.

  Args:
    name: A name of the api call router.
    api_call_router_cls: An ApiCallRouter class object.

  Returns:
    A decorator function that registers and unregisters the ApiCallRouter.
  """

  def Decorator(func):

    @functools.wraps(func)
    def Wrapper(*args, **kwargs):
      with _ApiCallRouterContext(name, api_call_router_cls):
        func(*args, **kwargs)

    return Wrapper

  return Decorator


class _ApiCallRouterContext(object):
  """A context manager for execution with certain ApiCallRouter registered."""

  def __init__(self, name, api_call_router_cls):
    self._name = name
    self._api_call_router = api_call_router_cls

  def __enter__(self):
    api_call_router_registry.RegisterApiCallRouter(
        self._name, self._api_call_router
    )

  def __exit__(self, exc_type, exc_value, traceback):
    del exc_type, exc_value, traceback  # Unused.

    api_call_router_registry.UnregisterApiCallRouter(self._name)
