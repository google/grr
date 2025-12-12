/**
 * Test helpers.
 */
// tslint:disable:no-any

import {TestBed} from '@angular/core/testing';
import {Observable, Subject} from 'rxjs';

import {HttpApiService} from './http_api_service';

type Func = (...args: any[]) => any;

/**
 * A service with Spy properties and mocked Observable return
 * values.
 */
export type MockService<T> = {
  [K in keyof T]: T[K] extends Function ? jasmine.Spy & T[K] : T[K];
} & {
  readonly mockedObservables: {
    [K in keyof T]: T[K] extends Func
      ? ReturnType<T[K]> extends Observable<infer V>
        ? Subject<V>
        : never
      : never;
  };
};

/** HttpApiService with Spy properties and mocked Observable return values. */
export declare interface HttpApiServiceMock
  extends MockService<HttpApiService> {}

/**
 * Mocks a HttpApiService, replacing methods with jasmine spies that return
 * Observables from `httpApiServiceMock.mockedObservables`.
 */
export function mockHttpApiService(): HttpApiServiceMock {
  const mockHttpClient = {
    get: jasmine.createSpy('get').and.callFake(() => new Subject()),
    post: jasmine.createSpy('post').and.callFake(() => new Subject()),
  };

  const service: any = new HttpApiService(mockHttpClient as any);
  const mockedObservables: any = {};

  const properties = Object.getOwnPropertyNames(
    HttpApiService.prototype,
  ).filter((key) => service[key] instanceof Function);

  for (const property of properties) {
    mockedObservables[property] = new Subject();
    service[property] = jasmine
      .createSpy(property)
      .and.callFake(() => mockedObservables[property].asObservable());
  }

  service.mockedObservables = mockedObservables;
  return service;
}

/** Injects the MockStore for the given Store class. */
export function injectHttpApiServiceMock(): HttpApiServiceMock {
  const mock = TestBed.inject(HttpApiService) as unknown as HttpApiServiceMock;

  if (!mock.mockedObservables) {
    const val = JSON.stringify(mock).slice(0, 100);
    throw new Error(
      `TestBed.inject(HttpApiService) returned ${val}, which does not look like HttpApiServiceMock. Did you register the HttpApiService providers?`,
    );
  }

  return mock;
}
