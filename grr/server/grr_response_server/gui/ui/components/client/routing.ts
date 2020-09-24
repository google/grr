import {NgModule} from '@angular/core';
import {RouterModule, Routes} from '@angular/router';
import {Client} from './client';


/**
 * Client details page route.
 */
export const CLIENT_ROUTES: Routes = [
  {
    path: 'clients/:id',
    component: Client,
    children: [
      {path: Client.CLIENT_DETAILS_ROUTE, component: Client},
    ],
  },
];

@NgModule({
  imports: [
    RouterModule.forChild(CLIENT_ROUTES),
  ],
  exports: [RouterModule],
})
export class ClientRoutingModule {
}
