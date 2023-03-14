import {NgModule} from '@angular/core';
import {RouterModule, Routes} from '@angular/router';

import {ModifyHunt} from './modify_hunt';

/**
 * Modify hunt sidebar route.
 */
export const MODIFY_HUNT_ROUTES: Routes = [
  {path: 'modify-hunt', component: ModifyHunt, outlet: 'drawer'},
];

@NgModule({
  imports: [
    RouterModule.forChild(MODIFY_HUNT_ROUTES),
  ],
  exports: [RouterModule],
})
export class ModifyHuntRoutingModule {
}