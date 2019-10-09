import {NgModule} from '@angular/core';
import {RouterModule, Routes} from '@angular/router';
import {HomeComponent} from './home';

const HOME_ROUTES: Routes = [{path: 'home', component: HomeComponent}];

@NgModule({
  imports: [
    RouterModule.forChild(HOME_ROUTES),
  ],
  exports: [RouterModule],
})
export class HomeRoutingModule {
}
