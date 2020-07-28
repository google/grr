import {NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatChipsModule} from '@angular/material/chips';
import {MatIconModule} from '@angular/material/icon';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';
import {FlowFormModule} from '@app/components/flow_form/module';
import {FlowListModule} from '@app/components/flow_list/module';

import {ApprovalModule} from '../approval/module';
import {ClientAddLabelDialogModule} from '../client_add_label_dialog/module';
import {OnlineChipModule} from '../online_chip/module';
import {TimestampModule} from '../timestamp/module';

import {Client} from './client';
import {ClientRoutingModule} from './routing';

/**
 * Module for the client details component.
 */
@NgModule({
  imports: [
    BrowserAnimationsModule,
    RouterModule,
    MatChipsModule,
    ClientRoutingModule,
    ApprovalModule,
    FlowFormModule,
    FlowListModule,
    TimestampModule,
    OnlineChipModule,
    MatIconModule,
    MatButtonModule,
    ClientAddLabelDialogModule,
  ],
  declarations: [
    Client,
  ],
})
export class ClientModule {
}
