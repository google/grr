import {NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatCardModule} from '@angular/material/card';
import {MatIconModule} from '@angular/material/icon';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
import {MatSidenavModule} from '@angular/material/sidenav';
import {MatTableModule} from '@angular/material/table';
import {MatTabsModule} from '@angular/material/tabs';
import {MatTreeModule} from '@angular/material/tree';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';
import {AngularSplitModule} from 'angular-split';

import {FlowFormModule} from '../../components/flow_form/module';
import {FlowListModule} from '../../components/flow_list/module';
import {ApprovalModule} from '../approval/module';
import {ClientOverviewModule} from '../client_overview/module';
import {FileDetailsModule} from '../file_details/file_details_module';
import {DrawerLinkModule} from '../helpers/drawer_link/drawer_link_module';
import {HumanReadableSizeModule} from '../human_readable_size/module';
import {ScheduledFlowListModule} from '../scheduled_flow_list/module';
import {TimestampModule} from '../timestamp/module';

import {ClientPage} from './client_page';
import {FlowSection} from './flow_section';
import {ClientPageRoutingModule} from './routing';
import {VfsSection} from './vfs_section';

/**
 * Module for the client details component.
 */
@NgModule({
  imports: [
    BrowserAnimationsModule, RouterModule,

    MatButtonModule,         MatCardModule,
    MatIconModule,           MatProgressSpinnerModule,
    MatSidenavModule,        MatTableModule,
    MatTabsModule,           MatTreeModule,

    AngularSplitModule,

    ApprovalModule,          ClientOverviewModule,
    ClientPageRoutingModule, DrawerLinkModule,
    FileDetailsModule,       FlowFormModule,
    FlowListModule,          HumanReadableSizeModule,
    ScheduledFlowListModule, TimestampModule,
  ],
  declarations: [
    ClientPage,
    FlowSection,
    VfsSection,
  ],
  exports: [FlowSection, VfsSection],
})
export class ClientPageModule {
}
