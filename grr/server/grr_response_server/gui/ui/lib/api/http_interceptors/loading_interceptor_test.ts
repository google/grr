import {
  HTTP_INTERCEPTORS,
  HttpClient,
  HttpContext,
  HttpErrorResponse,
  provideHttpClient,
  withInterceptorsFromDi,
} from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import {TestBed, waitForAsync} from '@angular/core/testing';

import {LoadingService} from '../../service/loading_service/loading_service';
import {LoadingInterceptor, TRACK_LOADING_STATE} from './loading_interceptor';

describe('LoadingInterceptor', () => {
  let client: HttpClient;
  let httpMock: HttpTestingController;
  let loadingServiceSpy: jasmine.SpyObj<LoadingService>;

  beforeEach(waitForAsync(() => {
    loadingServiceSpy = jasmine.createSpyObj('LoadingService', [
      'updateLoadingUrls',
    ]);

    TestBed.configureTestingModule({
      providers: [
        {
          provide: HTTP_INTERCEPTORS,
          useClass: LoadingInterceptor,
          multi: true,
        },
        {
          provide: LoadingService,
          useValue: loadingServiceSpy,
        },
        provideHttpClient(withInterceptorsFromDi()),
        provideHttpClientTesting(),
      ],
      teardown: {destroyAfterEach: true},
    }).compileComponents();

    client = TestBed.inject(HttpClient);
    httpMock = TestBed.inject(HttpTestingController);
  }));

  it('does not set the loading state if not requested', () => {
    const context = new HttpContext().set(TRACK_LOADING_STATE, false);
    client.get('/foo', {context}).subscribe();

    expect(loadingServiceSpy.updateLoadingUrls).not.toHaveBeenCalled();
    httpMock.expectOne('/foo').flush('wohoo', {status: 200, statusText: 'OK'});
    expect(loadingServiceSpy.updateLoadingUrls).not.toHaveBeenCalled();
  });

  it('sets the loading state when a request is made', () => {
    const context = new HttpContext().set(TRACK_LOADING_STATE, true);
    client.get('/foo', {context}).subscribe();

    expect(loadingServiceSpy.updateLoadingUrls).toHaveBeenCalledWith(
      '/foo',
      true,
    );
  });

  it('removes the loading state when a request is completed', () => {
    const context = new HttpContext().set(TRACK_LOADING_STATE, true);
    client.get('/foo', {context}).subscribe();

    httpMock.expectOne('/foo').flush('wohoo', {status: 200, statusText: 'OK'});
    expect(loadingServiceSpy.updateLoadingUrls).toHaveBeenCalledWith(
      '/foo',
      false,
    );
  });

  it('removes the loading state when a request fails', () => {
    const context = new HttpContext().set(TRACK_LOADING_STATE, true);
    client.get('/failing', {context}).subscribe(
      (data) => {
        fail('Should have failed');
      },
      (error: HttpErrorResponse) => {
        expect(error.status).toEqual(500);
      },
    );
    httpMock
      .expectOne('/failing')
      .flush('wohoo', {status: 500, statusText: 'Errrrrrrror'});

    expect(loadingServiceSpy.updateLoadingUrls).toHaveBeenCalledWith(
      '/failing',
      false,
    );
  });
});
