import {NgModule} from '@angular/core';
import {MatIconModule} from '@angular/material/icon';
import {MatLegacyButtonModule} from '@angular/material/legacy-button';
import {MatLegacyChipsModule} from '@angular/material/legacy-chips';
import {MatLegacyFormFieldModule} from '@angular/material/legacy-form-field';
import {MatLegacyInputModule} from '@angular/material/legacy-input';
import {MatLegacyTooltipModule} from '@angular/material/legacy-tooltip';
import {MatSidenavModule} from '@angular/material/sidenav';
import {MatToolbarModule} from '@angular/material/toolbar';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';

import {ApprovalChipModule} from '../../components/approval_chip/approval_chip_module';
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
    MatLegacyButtonModule,
    MatLegacyChipsModule,
    MatIconModule,
    MatLegacyInputModule,
    MatLegacyFormFieldModule,
    MatSidenavModule,
    MatToolbarModule,
    MatLegacyTooltipModule,

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
