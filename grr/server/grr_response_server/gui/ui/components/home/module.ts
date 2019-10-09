import {NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatIconModule} from '@angular/material/icon';
import {MatSidenavModule} from '@angular/material/sidenav';
import {MatToolbarModule} from '@angular/material/toolbar';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';

import {HomeComponent} from './home';
import {HomeRoutingModule} from './routing';

/** Module providing components related to tickets. */
@NgModule({
  imports: [
    // Core Angular modules.
    RouterModule,
    BrowserAnimationsModule,

    // Angular Material modules.
    MatButtonModule,
    MatIconModule,
    MatSidenavModule,
    MatToolbarModule,

    // GRR modules.
    HomeRoutingModule,
  ],
  declarations: [HomeComponent],
})
export class HomeModule {
}
