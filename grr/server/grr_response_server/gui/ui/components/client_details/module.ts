import {NgModule} from '@angular/core';
import {RouterModule} from '@angular/router';
import {ClientDetails} from './client_details';
import {ClientDetailsRoutingModule} from './routing';


/**
 * Module for the client details component.
 */
@NgModule({
  imports: [
    RouterModule,
    ClientDetailsRoutingModule,
  ],
  declarations: [
    ClientDetails,
  ],
})
export class ClientDetailsModule {
}
