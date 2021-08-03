/** Test helpers to mock Stores. */
// tslint:disable:no-any

import {Observable, ReplaySubject} from 'rxjs';

/** Type of a mocked Store with Observable helpers. */
export type MockStore<T> = {
  [K in keyof T]: T[K] extends Function ? jasmine.Spy&T[K] : T[K];
}&{
  mockedObservables: {
    [K in keyof T]: T[K] extends Observable<infer V>? ReplaySubject<V>: never;
  }
};

interface Constructor<ClassType> {
  new(...args: never[]): ClassType;
}

/**
 * Mocks a Store providing method spies and Observables.
 *
 * Any function present in cls.prototype will be mocked with a
 * jasmine.Spy.
 *
 * Any accessed Observable whose property name ends with `$` will
 * be mocked as ReplaySubject(1). To emit a value from a mocked Observable
 * foo$ call mockedStore.mockedObservables.foo$.emit().
 *
 * Angular callbacks ngOn* will be mocked as `undefined` to prevent
 * Angular's Injector from failing test.
 *
 * Any other unknown property will raise on access. Use
 * mockStore(X, {foo: bar}) to supply `bar` manually.
 */
export function mockStore<T>(
    cls: Constructor<T>, initial: Partial<MockStore<T>> = {}): MockStore<T> {
  const mockedObservables: MockStore<T>['mockedObservables'] =
      initial.mockedObservables ?? {} as any;

  initial.mockedObservables = new Proxy(mockedObservables, {
    get(target, prop, receiver) {
      if (prop in target) {
        return target[prop as keyof T];
      }

      const propName = String(prop);

      if (prop in initial) {
        throw new Error(
            `Cannot instantiate MockStore<${cls.name}.mockedObservables.${
                propName}: The property is already set on MockStore.${
                propName}. Did you supply it manually via mockStore(${cls}, {${
                propName}: value})?`);
      }

      const subject = new ReplaySubject<any>(1);
      target[prop as keyof T] = subject as any;
      return subject;
    }
  });

  return new Proxy(initial as MockStore<T>, {
    get(target, prop, receiver) {
      if (prop in target) {
        return target[prop as keyof MockStore<T>];
      }

      const propName = String(prop);

      if (cls.prototype[prop] instanceof Function) {
        const fn = jasmine.createSpy(propName);
        target[prop as keyof MockStore<T>] = fn as any;
        return fn;
      }

      if (propName.endsWith('$')) {
        // mockedObservable Proxy lazily instantiates Subject on access.
        const subject = target.mockedObservables[prop as keyof T];
        target[prop as keyof MockStore<T>] = subject.asObservable() as any;
        return subject;
      }

      // Angular Injector tests existence of ngOnDestroy - if ngOn* properties
      // are not set manually, we always return undefined.
      if (propName.startsWith('ngOn')) {
        return undefined;
      }

      throw new Error(`MockStore<${cls.name}> does not know how to mock ${
          propName} on the fly. Provide it manually, like: mockStore(${
          cls.name}, {${propName}: value})`);
    }
  });
}
