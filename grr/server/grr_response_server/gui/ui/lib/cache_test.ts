import {firstValueFrom, lastValueFrom, NEVER, of} from 'rxjs';

import {initTestEnvironment} from '../testing';

import {cacheLatest, StorageCache} from './cache';

initTestEnvironment();

class MapStorage implements Storage {
  private readonly map = new Map<string, string>();

  get length(): number {
    return this.map.size;
  }

  clear(): void {
    this.map.clear();
  }

  getItem(key: string): string|null {
    return this.map.get(key) ?? null;
  }

  key(index: number): string|null {
    return Array.from(this.map.keys())[index];
  }

  removeItem(key: string): void {
    this.map.delete(key);
  }

  setItem(key: string, value: string): void {
    this.map.set(key, value);
  }
}

describe('cache', () => {
  it('writes emitted values to storage', async () => {
    const storage = new StorageCache<number>(new MapStorage());
    const observable = of(1, 2, 3).pipe(cacheLatest('foo', storage));
    await lastValueFrom(observable);
    expect(storage.getItem('foo')).toBeTruthy();
  });

  it('emits the stored value', async () => {
    const storage = new StorageCache<number>(new MapStorage());
    of(3).pipe(cacheLatest('foo', storage)).subscribe();

    const cachedValue =
        await firstValueFrom(NEVER.pipe(cacheLatest<number>('foo', storage)));
    expect(cachedValue).toEqual(3);
  });

  it('correctly retains JSON-like data', async () => {
    const storage = new StorageCache<{}>(new MapStorage());
    of({a: 42, b: 'foo', c: {d: [true]}})
        .pipe(cacheLatest('foo', storage))
        .subscribe();

    const cachedValue =
        await firstValueFrom(NEVER.pipe(cacheLatest<{}>('foo', storage)));
    expect(cachedValue).toEqual({a: 42, b: 'foo', c: {d: [true]}});
  });

  it('passes through original data', async () => {
    const storage = new StorageCache<number>(new MapStorage());
    const original$ = of(42).pipe(cacheLatest('foo', storage));
    const originalValue = await lastValueFrom(original$);
    expect(originalValue).toEqual(42);

    const cached$ = of(99).pipe(cacheLatest<number>('foo', storage));
    const cachedValue = await firstValueFrom(cached$);
    expect(cachedValue).toEqual(42);

    const newValue = await lastValueFrom(cached$);
    expect(newValue).toEqual(99);
  });
});
