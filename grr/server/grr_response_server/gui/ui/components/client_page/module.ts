import {NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatIconModule} from '@angular/material/icon';
import {MatSidenavModule} from '@angular/material/sidenav';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';
import {FlowFormModule} from '@app/components/flow_form/module';
import {FlowListModule} from '@app/components/flow_list/module';

import {ApprovalModule} from '../approval/module';
import {ClientOverviewModule} from '../client_overview/module';
import {DrawerLinkModule} from '../helpers/drawer_link/drawer_link_module';
import {ScheduledFlowListModule} from '../scheduled_flow_list/module';

import {ClientPage} from './client_page';
import {ClientPageRoutingModule} from './routing';

/**
 * Module for the client details component.
 */
@NgModule({
  imports: [
    ApprovalModule,
    BrowserAnimationsModule,
    ClientOverviewModule,
    ClientPageRoutingModule,
    DrawerLinkModule,
    FlowFormModule,
    FlowListModule,
    MatButtonModule,
    MatIconModule,
    MatSidenavModule,
    RouterModule,
    ScheduledFlowListModule,
  ],
  declarations: [
    ClientPage,
  ],
})
export class ClientPageModule {
}
