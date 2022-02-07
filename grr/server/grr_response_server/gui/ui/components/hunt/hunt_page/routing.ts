import {NgModule} from '@angular/core';
import {RouterModule, Routes} from '@angular/router';

import {HuntPage} from './hunt_page';

/**
 * Hunt page routes.
 */
export const HUNT_PAGE_ROUTES: Routes = [
  {path: 'hunts/:id', component: HuntPage},
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
