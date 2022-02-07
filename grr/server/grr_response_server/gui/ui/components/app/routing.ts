import {NgModule} from '@angular/core';
import {RouterModule, Routes} from '@angular/router';

import {NotFoundPage} from './not_found_page';

const routes: Routes = [
  {
    path: '**',
    component: NotFoundPage,
  },
];

@NgModule({
  imports: [
    RouterModule.forRoot(routes, {relativeLinkResolution: 'corrected'}),
  ],
  exports: [
    RouterModule,
  ]
})
export class AppRoutingModule {
}
