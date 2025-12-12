import {
  HTTP_INTERCEPTORS,
  HttpClient,
  HttpContext,
  provideHttpClient,
  withInterceptorsFromDi,
} from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import {fakeAsync, TestBed, tick, waitForAsync} from '@angular/core/testing';

import {initTestEnvironment} from '../../../testing';
import {POLLING_INTERVAL, PollingInterceptor} from './polling_interceptor';

initTestEnvironment();

describe('PollingInterceptor', () => {
  let client: HttpClient;
  let httpMock: HttpTestingController;

  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      providers: [
        {
          provide: HTTP_INTERCEPTORS,
          useClass: PollingInterceptor,
          multi: true,
        },
        provideHttpClient(withInterceptorsFromDi()),
        provideHttpClientTesting(),
      ],
      teardown: {destroyAfterEach: false},
    }).compileComponents();

    client = TestBed.inject(HttpClient);
    httpMock = TestBed.inject(HttpTestingController);
  }));

  it('polls if requested', fakeAsync(() => {
    const pollingInterval = 100;
    const context = new HttpContext().set(POLLING_INTERVAL, pollingInterval);
    const sub = client.get('/foo', {context}).subscribe();

    tick();
    httpMock.expectOne('/foo').flush('wohoo', {status: 200, statusText: 'OK'});

    tick(pollingInterval);
    httpMock.expectOne('/foo').flush('wohoo', {status: 200, statusText: 'OK'});

    sub.unsubscribe();
  }));

  it('does not poll if not requested', fakeAsync(() => {
    const context = new HttpContext().set(POLLING_INTERVAL, 0);
    const sub = client.get('/foo', {context}).subscribe();

    tick();
    httpMock.expectOne('/foo').flush('wohoo', {status: 200, statusText: 'OK'});

    tick(100);
    httpMock.expectNone('/foo');

    sub.unsubscribe();
  }));
});
