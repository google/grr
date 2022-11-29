import {NgModule} from '@angular/core';
import {RouterModule, Routes} from '@angular/router';

import {HuntResultDetails} from './hunt_result_details';

/**
 * Hunt details sidebar route.
 */
export const HUNT_DETAILS_ROUTES: Routes = [
  {path: 'result-details/:key', component: HuntResultDetails, outlet: 'drawer'},
];

@NgModule({
  imports: [
    RouterModule.forChild(HUNT_DETAILS_ROUTES),
  ],
  exports: [RouterModule],
})
export class HuntResultDetailsRoutingModule {
}
