import {NgModule} from '@angular/core';
import {RouterModule, Routes} from '@angular/router';
import {Client} from './client';


/**
 * Client details page route.
 */
export const CLIENT_ROUTES: Routes = [
  {path: 'v2/clients/:id', component: Client},
  {path: 'v2/clients/:id/details', component: Client},
];

@NgModule({
  imports: [
    RouterModule.forChild(CLIENT_ROUTES),
  ],
  exports: [RouterModule],
})
export class ClientRoutingModule {
}
