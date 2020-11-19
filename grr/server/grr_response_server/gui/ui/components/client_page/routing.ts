import {NgModule} from '@angular/core';
import {RouterModule, Routes} from '@angular/router';

import {RoutesWithLegacyLinks} from '../../lib/routing';

import {ClientPage} from './client_page';

/**
 * Client details page route.
 */
export const CLIENT_PAGE_ROUTES: Routes&RoutesWithLegacyLinks = [
  {
    path: 'clients/:id',
    component: ClientPage,
    data: {legacyLink: '#/clients/:id'},
    children: [
      {path: ClientPage.CLIENT_DETAILS_ROUTE, component: ClientPage},
    ],
  },
];

@NgModule({
  imports: [
    RouterModule.forChild(CLIENT_PAGE_ROUTES),
  ],
  exports: [RouterModule],
})
export class ClientPageRoutingModule {
}
