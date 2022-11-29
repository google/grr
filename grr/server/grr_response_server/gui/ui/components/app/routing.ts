import {NgModule} from '@angular/core';
import {RouterModule, Routes} from '@angular/router';

import {HuntOverviewPage} from '../hunt/hunt_overview_page/hunt_overview_page';

import {NotFoundPage} from './not_found_page';

const routes: Routes = [
  {
    path: 'hunts',
    pathMatch: 'full',
    component: HuntOverviewPage,
  },
  {
    path: '**',
    component: NotFoundPage,
  },
];

@NgModule({
  imports: [
    RouterModule.forRoot(routes),
  ],
  exports: [
    RouterModule,
  ]
})
export class AppRoutingModule {
}
