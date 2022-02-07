import {NgModule} from '@angular/core';
import {RouterModule, Routes} from '@angular/router';

import {NewHunt} from './new_hunt';

/**
 * New hunt-related routes.
 */
export const NEW_HUNT_ROUTES: Routes = [
  {path: 'new-hunt', component: NewHunt},
];

/**
 * Routing module for the home page.
 */
@NgModule({
  imports: [
    RouterModule.forChild(NEW_HUNT_ROUTES),
  ],
  exports: [RouterModule],
})
export class NewHuntRoutingModule {
}
