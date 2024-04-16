#!/usr/bin/env python
"""A module with implementation of the cached keystore."""

import dataclasses
import datetime
from typing import Generic, Optional, TypeVar

from grr_response_server.keystore import abstract


_T = TypeVar("_T")


class CachedKeystore(abstract.Keystore):
  """A keystore implementation that caches key reads."""

  def __init__(
      self,
      delegate: abstract.Keystore,
      validity_duration: Optional[datetime.timedelta] = None,
  ) -> None:
    """Initializes the cached keystore.

    Args:
      delegate: A keystore instance to cache the results for.
      validity_duration: A duration for which cached keys are valid.
    """
    super().__init__()

    if validity_duration is None:
      validity_duration = _DEFAULT_VALIDITY_DURATION

    self._delegate = delegate
    self._validity_duration = validity_duration

    self._cache: dict[str, CachedKeystore._CacheEntry] = dict()

  def Crypter(self, name: str) -> abstract.Crypter:
    """Creates a crypter for the given key to encrypt and decrypt data."""
    try:
      entry = self._cache[name]
    except KeyError:
      entry = CachedKeystore._CacheEntry(
          crypter=self._delegate.Crypter(name),
          expiration_time=datetime.datetime.now() + self._validity_duration,
      )
      self._cache[name] = entry
      return entry.crypter

    if entry.is_valid:
      return entry.crypter

    # The key should be expired. We delete it from the cache and retry reading.
    del self._cache[name]
    return self.Crypter(name)

  @dataclasses.dataclass(frozen=True)
  class _CacheEntry(Generic[_T]):
    """An entry of the cache dictionary."""

    crypter: abstract.Crypter
    expiration_time: datetime.datetime

    @property
    def is_valid(self) -> bool:
      return datetime.datetime.now() < self.expiration_time


_DEFAULT_VALIDITY_DURATION = datetime.timedelta(minutes=5)
