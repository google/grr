import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatCardModule} from '@angular/material/card';
import {MatIconModule} from '@angular/material/icon';
import {MatSidenavModule} from '@angular/material/sidenav';

import {ClientDetailsModule} from '../client_details/module';
import {ClientOverviewModule} from '../client_overview/module';
import {ScheduledFlowListModule} from '../scheduled_flow_list/module';
import {UserImageModule} from '../user_image/module';

import {ApprovalPage} from './approval_page';
import {ApprovalRoutingModule} from './routing';

@NgModule({
  imports: [
    ApprovalRoutingModule,
    ClientDetailsModule,
    ClientOverviewModule,
    CommonModule,
    MatButtonModule,
    MatCardModule,
    MatIconModule,
    MatSidenavModule,
    ScheduledFlowListModule,
    UserImageModule,
  ],
  declarations: [
    ApprovalPage,
  ],
  exports: [
    ApprovalPage,
  ]
})
export class ApprovalPageModule {
}
