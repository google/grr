import {concat, Observable, OperatorFunction} from 'rxjs';
import {tap} from 'rxjs/operators';

/** A key-value storage to quickly retrieve items in the future. */
export declare interface Cache<T> {
  setItem(key: string, value: T): void;
  getItem(key: string): T|null;
}

/** A cache that persists over sessions, backed by window.localStorage. */
export class StorageCache<T> implements Cache<T> {
  constructor(private readonly storage: Storage = window.localStorage) {}

  setItem(key: string, value: T): void {
    this.storage.setItem(key, JSON.stringify(value));
  }
  getItem(key: string): T|null {
    const cached = this.storage.getItem(key);
    return cached === null ? null : JSON.parse(cached) as T;
  }
}

/**
 * Caches the latest emitted value of an Observable in the localStorage.
 *
 * Upon subscription, the latest cached value is emitted first, if one exists.
 *
 * ## Usage
 * Pipe your data source (e.g. HTTP API requests) into cache() and
 * provide a unique key for the cached data.
 *
 * ```ts
 * of(1, 2, 3).pipe(cacheLatest("foo")).subscribe(console.log);
 * ```
 *
 * This observable emits `1`, `2`, and `3` on the first execution. On any
 * succeeding execution, the observable will first emit the last value of the
 * previous execution `3`, followed by the values of the underlying observable
 * `1`, `2`, and `3`.
 */
export function cacheLatest<T>(
    key: string, cache: Cache<T> = new StorageCache()): OperatorFunction<T, T> {
  const cache$ = new Observable<T>((observer) => {
    const rawCached = cache.getItem(key);
    if (rawCached !== null) {
      observer.next(rawCached);
    }
    observer.complete();
  });

  return (source) => concat(
             cache$,
             source.pipe(tap((value: T) => {
               cache.setItem(key, value);
             })),
         );
}
