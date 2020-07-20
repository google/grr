import {NgModule} from '@angular/core';
import {MatChipsModule} from '@angular/material/chips';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';
import {FlowFormModule} from '@app/components/flow_form/module';
import {FlowListModule} from '@app/components/flow_list/module';

import {ApprovalModule} from '../approval/module';

import {Client} from './client';
import {ClientRoutingModule} from './routing';
import {TimestampModule} from '../timestamp/module';
import {OnlineChipModule} from '../online_chip/module';
import {MatButtonModule} from '@angular/material/button';

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
    MatButtonModule,
  ],
  declarations: [
    Client,
  ],
})
export class ClientModule {
}
