import {NgModule} from '@angular/core';
import {RouterModule, Routes} from '@angular/router';
import {Home} from './home';

/**
 * Home page-related routes.
 */
export const HOME_ROUTES: Routes = [
  {path: '', component: Home},
];

/**
 * Routing module for the home page.
 */
@NgModule({
  imports: [
    RouterModule.forChild(HOME_ROUTES),
  ],
  exports: [RouterModule],
})
export class HomeRoutingModule {
}
