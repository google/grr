import {NgModule} from '@angular/core';
import {RouterModule, Routes} from '@angular/router';

const routes: Routes = [
  {path: 'v2', redirectTo: 'v2/home', pathMatch: 'full'},
  // TODO(user): Change to error page.
  {path: '**', redirectTo: 'v2/home'},
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
