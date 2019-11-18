import {HttpClientModule} from '@angular/common/http';
import {NgModule} from '@angular/core';

import {ClientApiService} from './client_api_service';

/**
 * Module containing services for GRR API requests.
 */
@NgModule({
  providers: [
    ClientApiService,
  ],
  imports: [
    HttpClientModule,
  ],
})
export class ApiModule {
}
