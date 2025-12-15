#!/usr/bin/env python
"""A module with implementation of the cached keystore."""

from __future__ import annotations

import dataclasses
import datetime
from typing import Callable, Generic, Optional, TypeVar

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

    self._cache_crypters: dict[
        str, CachedKeystore._CacheEntry[abstract.Crypter]
    ] = dict()
    self._cache_macs: dict[str, CachedKeystore._CacheEntry[abstract.MAC]] = (
        dict()
    )

  def _GetCachedCrypto(
      self,
      name: str,
      cache: dict[str, CachedKeystore._CacheEntry[_T]],
      delegate_fn: Callable[[], _T],
  ) -> _T:
    """Returns a cached crypto primitive."""
    try:
      entry = cache[name]
    except KeyError:
      entry = CachedKeystore._CacheEntry(
          crypto=delegate_fn(),
          expiration_time=datetime.datetime.now() + self._validity_duration,
      )
      cache[name] = entry
      return entry.crypto

    if entry.is_valid:
      return entry.crypto

    # The key should be expired. We delete it from the cache and retry reading.
    del cache[name]
    return self._GetCachedCrypto(name, cache, delegate_fn)

  def Crypter(self, name: str) -> abstract.Crypter:
    """Creates a crypter for the given key to encrypt and decrypt data."""
    return self._GetCachedCrypto(
        name, self._cache_crypters, lambda: self._delegate.Crypter(name)
    )

  def MAC(self, name: str) -> abstract.MAC:
    """Creates a MAC for the given key to sign and verify data."""
    return self._GetCachedCrypto(
        name, self._cache_macs, lambda: self._delegate.MAC(name)
    )

  @dataclasses.dataclass(frozen=True)
  class _CacheEntry(Generic[_T]):
    """An entry of the cache dictionary."""

    crypto: _T
    expiration_time: datetime.datetime

    @property
    def is_valid(self) -> bool:
      return datetime.datetime.now() < self.expiration_time


_DEFAULT_VALIDITY_DURATION = datetime.timedelta(minutes=5)
