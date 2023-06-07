import {NgModule} from '@angular/core';
import {RouterModule, Routes} from '@angular/router';

import {HuntHelp} from './hunt_help';

/**
 * Hunt help sidebar route.
 */
export const HUNT_HELP_ROUTES: Routes = [
  {path: 'help', component: HuntHelp, outlet: 'drawer'},
];

@NgModule({
  imports: [
    RouterModule.forChild(HUNT_HELP_ROUTES),
  ],
  exports: [RouterModule],
})
export class HuntHelpRoutingModule {
}
