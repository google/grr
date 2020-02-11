import {HTTP_INTERCEPTORS, HttpClientModule, HttpClientXsrfModule} from '@angular/common/http';
import {NgModule} from '@angular/core';

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
  ],

})
export class ApiModule {
}
