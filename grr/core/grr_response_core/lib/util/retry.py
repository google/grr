#!/usr/bin/env python
"""A module with utilities for retrying function execution."""
import functools
import logging
import math
import time
from typing import Callable
from typing import Optional
from typing import Tuple
from typing import Type
from typing import TypeVar


class Opts:
  """Options that customize the retry mechanism.

  Attributes:
    attempts: The number of attempts to retry the call.
    init_delay_secs: An initial value for delay between retries.
    max_delay_secs: A maximum value for delay between retries.
    backoff: A backoff multiplayer for the delay between retries.
    sleep: A sleep function used for delaying retries.
  """
  attempts: int = 1

  init_delay_secs: float = 0.0
  max_delay_secs: float = math.inf
  backoff: float = 1.0

  sleep: Callable[[float], None] = time.sleep


class On:
  """A decorator that retries the wrapped function on exception."""

  def __init__(
      self,
      exceptions: Tuple[Type[Exception], ...],
      opts: Optional[Opts] = None,
  ) -> None:
    """Initializes the decorator.

    Args:
      exceptions: A sequence of exceptions to retry on.
      opts: Options that customize the retry behaviour.
    """
    if opts is None:
      opts = Opts()

    if opts.attempts < 1:
      raise ValueError("Non-positive number of retries")

    self._exceptions = exceptions
    self._opts = opts

  _R = TypeVar("_R")

  # TODO(hanuszczak): Looks like there is a bug in the linter: it recognizes
  # `_R` in the argument but doesn't recognize it in the result type position.
  def __call__(self, func: Callable[..., _R]) -> Callable[..., _R]:  # pylint: disable=undefined-variable
    """Wraps the specified function into a retryable function.

    The wrapped function will be attempted to be called specified number of
    times after which the error will be propagated.

    Args:
      func: A function to wrap.

    Returns:
      A wrapped function that retries on failures.
    """
    opts = self._opts

    @functools.wraps(func)
    def Wrapped(*args, **kwargs) -> On._R:
      attempts = 0
      delay_secs = opts.init_delay_secs

      while True:
        try:
          return func(*args, **kwargs)
        except self._exceptions as error:
          attempts += 1
          if attempts == opts.attempts:
            raise

          logging.warning("'%s', to be retried in %s s.", error, delay_secs)

          opts.sleep(delay_secs)
          delay_secs = min(delay_secs * opts.backoff, opts.max_delay_secs)

    return Wrapped
