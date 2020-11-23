import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatIconModule} from '@angular/material/icon';
import {MatMenuModule} from '@angular/material/menu';
import {MatTooltipModule} from '@angular/material/tooltip';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';

import {UserImageModule} from '../user_image/module';

import {ScheduledFlowList} from './scheduled_flow_list';

/**
 * Module for the ScheduledFlowList component.
 */
@NgModule({
  imports: [
    BrowserAnimationsModule,
    CommonModule,
    MatButtonModule,
    MatIconModule,
    MatMenuModule,
    MatTooltipModule,
    RouterModule,
    UserImageModule,
  ],
  declarations: [
    ScheduledFlowList,
  ],
  exports: [
    ScheduledFlowList,
  ],
})
export class ScheduledFlowListModule {
}
