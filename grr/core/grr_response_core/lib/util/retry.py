#!/usr/bin/env python
"""A module with utilities for retrying function execution."""

from collections.abc import Callable
import dataclasses
import datetime
import functools
import logging
import random
import time
from typing import Generic, Optional, TypeVar, Union


@dataclasses.dataclass
class Opts:
  """Options that customize the retry mechanism.

  Attributes:
    attempts: The number of attempts to retry the call.
    init_delay: An initial value for delay between retries.
    max_delay: A maximum value for delay between retries.
    backoff: A backoff multiplayer for the delay between retries.
    jitter: A random jitter to add to delay between retries.
    sleep: A sleep function used for delaying retries.
  """

  attempts: int = 1

  init_delay: datetime.timedelta = datetime.timedelta(0)
  max_delay: datetime.timedelta = datetime.timedelta.max
  backoff: float = 1.0
  jitter: float = 0.0

  # fmt: off
  sleep: Callable[[datetime.timedelta], None] = (
      lambda timedelta: time.sleep(timedelta.total_seconds())
  )
  # fmt: on


_E = TypeVar("_E", bound=Exception)


class On(Generic[_E]):
  """A decorator that retries the wrapped function on exception."""

  def __init__(
      self,
      exception: Union[type[_E], tuple[type[_E], ...]],
      opts: Optional[Opts] = None,
  ) -> None:
    """Initializes the decorator.

    Args:
      exception: A sequence of exceptions to retry on.
      opts: Options that customize the retry behaviour.
    """
    self._when = When(exception, lambda _: True, opts=opts)

  _R = TypeVar("_R")

  def __call__(self, func: Callable[..., _R]) -> Callable[..., _R]:
    """Wraps the specified function into a retryable function.

    The wrapped function will be attempted to be called specified number of
    times after which the error will be propagated.

    Args:
      func: A function to wrap.

    Returns:
      A wrapped function that retries on failures.
    """
    return self._when(func)


class When(Generic[_E]):
  """A decorator that retries function on exception if predicate is met."""

  def __init__(
      self,
      exception: Union[type[_E], tuple[type[_E], ...]],
      predicate: Callable[[_E], bool],
      opts: Optional[Opts] = None,
  ) -> None:
    """Initializes the decorator.

    Args:
      exception: An exception type to catch.
      predicate: A predicate to check whether to retry the exception.
      opts: Options that customize the retry behaviour.
    """
    if opts is None:
      opts = Opts()

    if opts.attempts < 1:
      raise ValueError("Non-positive number of retries")

    self._exception = exception
    self._predicate = predicate
    self._opts = opts

  _R = TypeVar("_R")

  def __call__(self, func: Callable[..., _R]) -> Callable[..., _R]:
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
      delay = opts.init_delay

      while True:
        try:
          return func(*args, **kwargs)
        except self._exception as error:
          attempts += 1
          if attempts == opts.attempts:
            raise

          if not self._predicate(error):
            raise

          jitter = random.uniform(-opts.jitter, +opts.jitter)
          jittered_delay = delay + delay * jitter

          logging.warning("'%s', to be retried in %s", error, jittered_delay)
          opts.sleep(jittered_delay)

          # Note that we calculate the new delay value basing on the base delay,
          # not the jittered one, otherwise the delay values might become too
          # unpredictable.
          delay = min(delay * opts.backoff, opts.max_delay)

    return Wrapped
