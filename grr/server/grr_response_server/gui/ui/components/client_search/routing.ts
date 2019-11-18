import {NgModule} from '@angular/core';
import {RouterModule, Routes} from '@angular/router';
import {ClientSearch} from './client_search';

/**
 * Routes used by the client search page.
 */
export const CLIENT_SEARCH_ROUTES: Routes = [
  {path: 'v2/client-search/:query', component: ClientSearch},
];

/**
 * Routing module for the client search page.
 */
@NgModule({
  imports: [
    RouterModule.forChild(CLIENT_SEARCH_ROUTES),
  ],
  exports: [RouterModule],
})
export class ClientSearchRoutingModule {
}
