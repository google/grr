import {NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatIconModule} from '@angular/material/icon';
import {MatSidenavModule} from '@angular/material/sidenav';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';
import {FlowFormModule} from '@app/components/flow_form/module';
import {FlowListModule} from '@app/components/flow_list/module';

import {ApprovalModule} from '../approval/module';
import {ClientDetailsModule} from '../client_details/module';
import {ClientOverviewModule} from '../client_overview/module';

import {ClientPage} from './client_page';
import {ClientPageRoutingModule} from './routing';

/**
 * Module for the client details component.
 */
@NgModule({
  imports: [
    BrowserAnimationsModule,
    RouterModule,
    ClientPageRoutingModule,
    ApprovalModule,
    FlowFormModule,
    FlowListModule,
    ClientOverviewModule,
    MatSidenavModule,
    ClientDetailsModule,
    MatButtonModule,
    MatIconModule,
  ],
  declarations: [
    ClientPage,
  ],
})
export class ClientPageModule {
}
