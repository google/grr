import {NgModule} from '@angular/core';
import {RouterModule, Routes} from '@angular/router';
import {ClientDetails} from './client_details';


/**
 * Client details page route.
 */
export const CLIENT_ROUTES: Routes = [
  {path: 'v2/clients/:id/details', component: ClientDetails},
];

@NgModule({
  imports: [
    RouterModule.forChild(CLIENT_ROUTES),
  ],
  exports: [RouterModule],
})
export class ClientDetailsRoutingModule {
}
