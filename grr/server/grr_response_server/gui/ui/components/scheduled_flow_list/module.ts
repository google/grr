import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatIconModule} from '@angular/material/icon';
import {MatLegacyButtonModule} from '@angular/material/legacy-button';
import {MatLegacyMenuModule} from '@angular/material/legacy-menu';
import {MatLegacyTooltipModule} from '@angular/material/legacy-tooltip';
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
    MatLegacyButtonModule,
    MatIconModule,
    MatLegacyMenuModule,
    MatLegacyTooltipModule,
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
