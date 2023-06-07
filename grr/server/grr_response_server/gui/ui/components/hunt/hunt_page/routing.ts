import {NgModule} from '@angular/core';
import {RouterModule} from '@angular/router';

import {RoutesWithLegacyLinks} from '../../../lib/routing';

import {HuntPage} from './hunt_page';

/**
 * Hunt page routes.
 */
export const HUNT_PAGE_ROUTES: RoutesWithLegacyLinks = [
  {path: 'hunts/:id', component: HuntPage, data: {legacyLink: '#/hunts/:id'}},
];
/**
 * Routing module for the hunt home page.
 */
@NgModule({
  imports: [
    RouterModule.forChild(HUNT_PAGE_ROUTES),
  ],
  exports: [RouterModule],
})
export class HuntPageRoutingModule {
}
