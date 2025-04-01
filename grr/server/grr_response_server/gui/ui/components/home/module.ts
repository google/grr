import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatChipsModule} from '@angular/material/chips';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatSidenavModule} from '@angular/material/sidenav';
import {MatToolbarModule} from '@angular/material/toolbar';
import {MatTooltipModule} from '@angular/material/tooltip';
import {RouterModule} from '@angular/router';

import {ApprovalChipModule} from '../../components/approval_chip/approval_chip_module';
import {ApiModule} from '../../lib/api/module';
import {ClientSearchModule} from '../client_search/module';
import {OnlineChipModule} from '../online_chip/module';
import {TimestampModule} from '../timestamp/module';

import {Home} from './home';
import {RecentActivityModule} from './recent_activity/module';

/**
 * Module for the home page and related components.
 */
@NgModule({
  imports: [
    // TODO: re-enable clang format when solved.
    // prettier-ignore
    // keep-sorted start block=yes
    ApiModule,
    ApprovalChipModule,
    ClientSearchModule,
    CommonModule,
    MatButtonModule,
    MatChipsModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSidenavModule,
    MatToolbarModule,
    MatTooltipModule,
    OnlineChipModule,
    RecentActivityModule,
    RouterModule,
    TimestampModule,
    // keep-sorted end
  ],
  declarations: [Home],
})
export class HomeModule {}
