/**
 * Test helpers.
 */
// tslint:disable:no-any

import {TestBed} from '@angular/core/testing';
import {Subject} from 'rxjs';

import {MockService} from './http_api_service_test_util';
import {HttpApiWithTranslationService} from './http_api_with_translation_service';

/** HttpApiWithTranslationServiceMock with Spy properties and mocked Observable return values. */
export declare interface HttpApiWithTranslationServiceMock
  extends MockService<HttpApiWithTranslationService> {}

/**
 * Mocks a HttpApiWithTranslationService using a mockHttpApiService.
 */
export function mockHttpApiWithTranslationService(): HttpApiWithTranslationServiceMock {
  const mockHttpClient = {
    get: jasmine.createSpy('get').and.callFake(() => new Subject()),
    post: jasmine.createSpy('post').and.callFake(() => new Subject()),
  };

  const service: any = new HttpApiWithTranslationService(mockHttpClient as any);
  const mockedObservables: any = {};

  const properties = Object.getOwnPropertyNames(
    HttpApiWithTranslationService.prototype,
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

/**
 * Injects a HttpApiWithTranslationServiceMock into the test.
 */
export function injectHttpApiWithTranslationServiceMock(): HttpApiWithTranslationServiceMock {
  const mock = TestBed.inject(
    HttpApiWithTranslationService,
  ) as unknown as HttpApiWithTranslationServiceMock;

  if (!mock.mockedObservables) {
    const val = JSON.stringify(mock).slice(0, 100);
    throw new Error(
      `TestBed.inject(HttpApiWithTranslationService) returned ${val}, which does not look like HttpApiWithTranslationServiceMock. Did you register the HttpApiWithTranslationService providers?`,
    );
  }

  return mock;
}
