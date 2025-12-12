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
import {MatSnackBar, MatSnackBarModule} from '@angular/material/snack-bar';

import {ErrorSnackBar} from '../../../lib/error_handler/error_snackbar/error_snackbar';
import {initTestEnvironment} from '../../../testing';
import {
  SHOW_ERROR_BAR,
  SHOW_ERROR_BAR_FOR_403,
  SHOW_ERROR_BAR_FOR_404,
  ShowErrorBarInterceptor,
} from './show_error_bar_interceptor';

initTestEnvironment();

describe('ShowErrorBarInterceptor', () => {
  let client: HttpClient;
  let snackbar: Partial<MatSnackBar>;
  let httpMock: HttpTestingController;

  beforeEach(waitForAsync(() => {
    snackbar = jasmine.createSpyObj('MatSnackBar', ['openFromComponent']);

    TestBed.configureTestingModule({
      providers: [
        {
          provide: HTTP_INTERCEPTORS,
          useClass: ShowErrorBarInterceptor,
          multi: true,
        },
        {provide: MatSnackBar, useFactory: () => snackbar},
        provideHttpClient(withInterceptorsFromDi()),
        provideHttpClientTesting(),
      ],
      imports: [MatSnackBarModule, ErrorSnackBar],
      teardown: {destroyAfterEach: false},
    }).compileComponents();

    client = TestBed.inject(HttpClient);

    httpMock = TestBed.inject(HttpTestingController);
  }));

  it('shows error bar when error bar is requested', () => {
    const context = new HttpContext().set(SHOW_ERROR_BAR, true);

    client.get('/failing', {context}).subscribe(
      (data) => {
        fail('Should have failed');
      },
      (error: HttpErrorResponse) => {
        expect(error.status).toEqual(500);
        expect(error.error).toContain('wohoo');
      },
    );
    httpMock
      .expectOne('/failing')
      .flush('wohoo', {status: 500, statusText: 'Errrrrrrror'});

    expect(snackbar.openFromComponent).toHaveBeenCalledOnceWith(
      ErrorSnackBar,
      jasmine.objectContaining({
        data: 'wohoo (from /failing)',
      }),
    );
  });

  it('does not show error bar when bar is not requested', () => {
    const context = new HttpContext().set(SHOW_ERROR_BAR, false);
    client.get('/failing', {context}).subscribe(
      (data) => {
        fail('Should have failed');
      },
      (error: HttpErrorResponse) => {
        expect(error.status).toEqual(500);
        expect(error.error).toContain('wohoo');
      },
    );

    httpMock
      .expectOne('/failing')
      .flush('wohoo', {status: 500, statusText: 'Errrrrrrror'});

    expect(snackbar.openFromComponent).not.toHaveBeenCalled();
  });

  it('shows error bar for access denied errors if requested', () => {
    const context = new HttpContext()
      .set(SHOW_ERROR_BAR, true)
      .set(SHOW_ERROR_BAR_FOR_403, true);
    client.get('/failing', {context}).subscribe(
      (data) => {
        fail('Should have failed');
      },
      (error: HttpErrorResponse) => {
        expect(error.status).toEqual(403);
        expect(error.error).toContain('access denied');
      },
    );

    httpMock
      .expectOne('/failing')
      .flush('access denied', {status: 403, statusText: 'Errrrrrrror'});

    expect(snackbar.openFromComponent).toHaveBeenCalledTimes(1);
  });

  it('does not show error bar for access denied errors if not requested', () => {
    const context = new HttpContext()
      .set(SHOW_ERROR_BAR, true)
      .set(SHOW_ERROR_BAR_FOR_403, false);
    client.get('/failing', {context}).subscribe(
      (data) => {
        fail('Should have failed');
      },
      (error: HttpErrorResponse) => {
        expect(error.status).toEqual(403);
        expect(error.error).toContain('access denied');
      },
    );

    httpMock
      .expectOne('/failing')
      .flush('access denied', {status: 403, statusText: 'Errrrrrrror'});

    expect(snackbar.openFromComponent).not.toHaveBeenCalled();
  });

  it('shows error bar for 404 errors if requested', () => {
    const context = new HttpContext()
      .set(SHOW_ERROR_BAR, true)
      .set(SHOW_ERROR_BAR_FOR_404, true);
    client.get('/failing', {context}).subscribe(
      (data) => {
        fail('Should have failed');
      },
      (error: HttpErrorResponse) => {
        expect(error.status).toEqual(404);
        expect(error.error).toContain('file not found');
      },
    );

    httpMock
      .expectOne('/failing')
      .flush('file not found', {status: 404, statusText: 'Errrrrrrror'});

    expect(snackbar.openFromComponent).toHaveBeenCalled();
  });

  it('does not show error bar for 404 errors if not requested', () => {
    const context = new HttpContext()
      .set(SHOW_ERROR_BAR, true)
      .set(SHOW_ERROR_BAR_FOR_404, false);
    client.get('/failing', {context}).subscribe(
      (data) => {
        fail('Should have failed');
      },
      (error: HttpErrorResponse) => {
        expect(error.status).toEqual(404);
        expect(error.error).toContain('file not found');
      },
    );

    httpMock
      .expectOne('/failing')
      .flush('file not found', {status: 404, statusText: 'Errrrrrrror'});

    expect(snackbar.openFromComponent).not.toHaveBeenCalled();
  });

  it('does not show error bar when no error is returned', () => {
    const context = new HttpContext().set(SHOW_ERROR_BAR, true);
    client.get('/succeeding', {context}).subscribe();

    httpMock
      .expectOne('/succeeding')
      .flush('Yippie', {status: 200, statusText: 'OK'});

    expect(snackbar.openFromComponent).not.toHaveBeenCalled();
  });
});
