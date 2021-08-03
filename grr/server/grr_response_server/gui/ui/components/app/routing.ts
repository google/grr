import {NgModule} from '@angular/core';
import {RouterModule, Routes} from '@angular/router';

const routes: Routes = [
  // TODO(user): Change to error page.
  // {path: '**', redirectTo: '/'},
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
