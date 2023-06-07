import {NgModule} from '@angular/core';
import {RouterModule} from '@angular/router';

import {RoutesWithLegacyLinks} from '../../lib/routing';
import {HuntOverviewPage} from '../hunt/hunt_overview_page/hunt_overview_page';

import {NotFoundPage} from './not_found_page';

const routes: RoutesWithLegacyLinks = [
  {
    path: 'hunts',
    pathMatch: 'full',
    component: HuntOverviewPage,
    data: {legacyLink: '#/hunts'}
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
