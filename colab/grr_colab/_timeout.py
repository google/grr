#!/usr/bin/env python
"""Module containing functions for managing flow timeout."""
from typing import Optional

from grr_api_client import errors as api_errors
from grr_api_client import flow
from grr_colab import errors

_DEFAULT_FLOW_TIMEOUT = 30
_FLOW_TIMEOUT = _DEFAULT_FLOW_TIMEOUT


def set_timeout(timeout: Optional[int]) -> None:
  """Sets flow timeout in seconds.

  Args:
    timeout: Flow timeout in seconds.

  Returns:
    Nothing.
  """
  global _FLOW_TIMEOUT
  _FLOW_TIMEOUT = timeout


def reset_timeout() -> None:
  """Sets flow timeout to a default value of 30 seconds.

  Returns:
    Nothing.
  """
  global _FLOW_TIMEOUT
  _FLOW_TIMEOUT = _DEFAULT_FLOW_TIMEOUT


def await_flow(f: flow.Flow) -> None:
  """Awaits flow until timeout is exceeded.

  Args:
    f: Flow to await.

  Returns:
    Nothing.

  Raises:
    FlowTimeoutError: Timeout is exceeded while awaiting a flow.
  """
  if _FLOW_TIMEOUT == 0:
    raise errors.FlowTimeoutError(f.client_id, f.flow_id)
  try:
    timeout = 0 if _FLOW_TIMEOUT is None else _FLOW_TIMEOUT
    f.WaitUntilDone(timeout=timeout)
  except api_errors.PollTimeoutError as e:
    raise errors.FlowTimeoutError(f.client_id, f.flow_id, e)
