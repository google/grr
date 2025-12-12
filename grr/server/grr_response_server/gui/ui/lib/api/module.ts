import {
  HTTP_INTERCEPTORS,
  provideHttpClient,
  withInterceptorsFromDi,
  withXsrfConfiguration,
} from '@angular/common/http';
import {NgModule} from '@angular/core';
import {MatSnackBarModule} from '@angular/material/snack-bar';

import {ErrorSnackBar} from '../../lib/error_handler/error_snackbar/error_snackbar';
import {HttpApiService} from './http_api_service';
import {HttpApiWithTranslationService} from './http_api_with_translation_service';
import {LoadingInterceptor} from './http_interceptors/loading_interceptor';
import {PollingInterceptor} from './http_interceptors/polling_interceptor';
import {ShowErrorBarInterceptor} from './http_interceptors/show_error_bar_interceptor';
import {WithCredentialsInterceptor} from './http_interceptors/with_credentials_interceptor';

/**
 * Module containing services for GRR API requests.
 */
@NgModule({
  providers: [
    HttpApiService,
    HttpApiWithTranslationService,
    {
      provide: HTTP_INTERCEPTORS,
      useClass: WithCredentialsInterceptor,
      multi: true,
    },
    // The order matters!! The interceptors are executed in the order they are
    // listed here. The LoadingInterceptor should only trigger once for the
    // first request when polling is enabled, so it should be executed before
    // the PollingInterceptor.
    {
      provide: HTTP_INTERCEPTORS,
      useClass: LoadingInterceptor,
      multi: true,
    },
    {
      provide: HTTP_INTERCEPTORS,
      useClass: PollingInterceptor,
      multi: true,
    },
    {
      provide: HTTP_INTERCEPTORS,
      useClass: ShowErrorBarInterceptor,
      multi: true,
    },
    provideHttpClient(
      withXsrfConfiguration({
        cookieName: 'csrftoken',
        headerName: 'X-CSRFToken',
      }),
      withInterceptorsFromDi(),
    ),
  ],
  imports: [MatSnackBarModule, ErrorSnackBar],
})
export class ApiModule {}
