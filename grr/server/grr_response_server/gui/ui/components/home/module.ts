import {NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatChipsModule} from '@angular/material/chips';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatSidenavModule} from '@angular/material/sidenav';
import {MatToolbarModule} from '@angular/material/toolbar';
import {MatTooltipModule} from '@angular/material/tooltip';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';

import {ApprovalChipModule} from '../../components/client/approval_chip/approval_chip_module';
import {ApiModule} from '../../lib/api/module';
import {ClientSearchModule} from '../client_search/module';
import {OnlineChipModule} from '../online_chip/module';
import {TimestampModule} from '../timestamp/module';

import {Home} from './home';
import {RecentActivityModule} from './recent_activity/module';
import {HomeRoutingModule} from './routing';


/**
 * Module for the home page and related components.
 */
@NgModule({
  imports: [
    // Core Angular modules.
    BrowserAnimationsModule,
    RouterModule,

    // Angular Material modules.
    MatButtonModule,
    MatChipsModule,
    MatIconModule,
    MatInputModule,
    MatFormFieldModule,
    MatSidenavModule,
    MatToolbarModule,
    MatTooltipModule,

    // GRR modules.
    ApprovalChipModule,
    ApiModule,
    ClientSearchModule,
    HomeRoutingModule,
    OnlineChipModule,
    TimestampModule,
    RecentActivityModule,
  ],
  declarations: [Home],
})
export class HomeModule {
}
