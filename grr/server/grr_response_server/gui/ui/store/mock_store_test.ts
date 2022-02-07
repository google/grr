import {firstValueFrom, Observable, of, ReplaySubject, Subject} from 'rxjs';

import {initTestEnvironment} from '../testing';

import {mockStore} from './store_test_util';


initTestEnvironment();


class Store {
  readonly foo$: Observable<number> = of();
  incrementFoo() {}
}

describe('MockStore', () => {
  it('lazily instantiates observables', () => {
    const mock = mockStore(Store);
    expect(mock.foo$).toBeInstanceOf(Observable);
    expect(mock.mockedObservables.foo$).toBeInstanceOf(Subject);
  });

  it('mocks functions', () => {
    const mock = mockStore(Store);
    expect(mock.incrementFoo).not.toHaveBeenCalled();
    mock.incrementFoo();
    expect(mock.incrementFoo).toHaveBeenCalled();
  });

  it('replays emitted observable value', async () => {
    const mock = mockStore(Store);
    mock.mockedObservables.foo$.next(5);
    expect(await firstValueFrom(mock.foo$)).toBe(5);
    expect(await firstValueFrom(mock.foo$)).toBe(5);
  });

  it('keeps reference between Observable and Subject', async () => {
    const mock = mockStore(Store);
    const foo$ = mock.foo$;
    const promise = firstValueFrom(foo$);
    mock.mockedObservables.foo$.next(8);
    expect(await promise).toBe(8);
  });

  it('keeps reference between Subject and Observable', async () => {
    const mock = mockStore(Store);
    const fooSubject = mock.mockedObservables.foo$;
    const promise = firstValueFrom(mock.foo$);
    fooSubject.next(8);
    expect(await promise).toBe(8);
  });

  it('works for multiple emits', async () => {
    const mock = mockStore(Store);
    mock.mockedObservables.foo$.next(5);
    expect(await firstValueFrom(mock.foo$)).toBe(5);
    mock.mockedObservables.foo$.next(12);
    expect(await firstValueFrom(mock.foo$)).toBe(12);
  });

  it('returns provided values', async () => {
    const foo$ = new ReplaySubject<number>();
    const mock = mockStore(Store, {foo$});

    expect(foo$ as Observable<number>).toBe(mock.foo$);

    foo$.next(5);
    expect(await firstValueFrom(mock.foo$)).toBe(5);
  });

  it('throws when trying to auto-create manually set Observable', async () => {
    const foo$ = new ReplaySubject<number>();
    const mock = mockStore(Store, {foo$});

    expect(() => {
      // tslint:disable-next-line:no-unused-expression
      mock.mockedObservables.foo$;
    }).toThrowError(/property is already set on MockStore.foo\$/);
  });

  it('throws when trying to auto-create unexpected properties', async () => {
    const mock = mockStore(Store);

    expect(() => {
      // tslint:disable-next-line:no-any no-unused-expression
      (mock as any).bar;
    }).toThrowError(/does not know how to mock bar/);
  });
});
