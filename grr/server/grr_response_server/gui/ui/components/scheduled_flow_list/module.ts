import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatIconModule} from '@angular/material/icon';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';

import {ScheduledFlowList} from './scheduled_flow_list';

/**
 * Module for the ScheduledFlowList component.
 */
@NgModule({
  imports: [
    BrowserAnimationsModule,
    RouterModule,
    CommonModule,
    MatIconModule,
    MatButtonModule,
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
