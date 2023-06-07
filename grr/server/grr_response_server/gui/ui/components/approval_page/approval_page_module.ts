import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatIconModule} from '@angular/material/icon';
import {MatLegacyButtonModule} from '@angular/material/legacy-button';
import {MatLegacyCardModule} from '@angular/material/legacy-card';
import {MatLegacyProgressSpinnerModule} from '@angular/material/legacy-progress-spinner';
import {MatSidenavModule} from '@angular/material/sidenav';

import {ClientDetailsModule} from '../client_details/module';
import {ClientOverviewModule} from '../client_overview/module';
import {DrawerLinkModule} from '../helpers/drawer_link/drawer_link_module';
import {TextWithLinksModule} from '../helpers/text_with_links/text_with_links_module';
import {ScheduledFlowListModule} from '../scheduled_flow_list/module';
import {UserImageModule} from '../user_image/module';

import {ApprovalPage} from './approval_page';
import {ApprovalRoutingModule} from './routing';

@NgModule({
  imports: [
    CommonModule, MatLegacyButtonModule, MatLegacyCardModule, MatIconModule,
    MatLegacyProgressSpinnerModule, MatSidenavModule,

    ApprovalRoutingModule, ClientDetailsModule, ClientOverviewModule,
    DrawerLinkModule, ScheduledFlowListModule, UserImageModule,
    TextWithLinksModule
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
