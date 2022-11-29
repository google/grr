import {NgModule} from '@angular/core';
import {RouterModule, Routes} from '@angular/router';

import {ClientDetails} from './client_details';

/**
 * Client details sidebar route.
 */
export const CLIENT_DETAILS_ROUTES: Routes = [
  {
    path: 'details/:clientId',
    component: ClientDetails,
    outlet: 'drawer',
  },
  {
    path: 'details/:clientId/:sourceFlowId',
    component: ClientDetails,
    outlet: 'drawer',
  },
];

@NgModule({
  imports: [
    RouterModule.forChild(CLIENT_DETAILS_ROUTES),
  ],
  exports: [RouterModule],
})
export class ClientDetailsRoutingModule {
}
