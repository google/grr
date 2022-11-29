import {HTTP_INTERCEPTORS, HttpClientModule, HttpClientXsrfModule} from '@angular/common/http';
import {NgModule} from '@angular/core';
import {MatSnackBarModule} from '@angular/material/snack-bar';

import {ErrorSnackBarModule} from '../../components/helpers/error_snackbar/error_snackbar_module';

import {HttpApiService, WithCredentialsInterceptor} from './http_api_service';

/**
 * Module containing services for GRR API requests.
 */
@NgModule({
  providers: [
    HttpApiService, {
      provide: HTTP_INTERCEPTORS,
      useClass: WithCredentialsInterceptor,
      multi: true
    }
  ],
  imports: [
    HttpClientModule,
    HttpClientXsrfModule.withOptions({
      cookieName: 'csrftoken',
      headerName: 'X-CSRFToken',
    }),

    MatSnackBarModule,

    ErrorSnackBarModule,
  ],

})
export class ApiModule {
}
