import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {RouterModule} from '@angular/router';

import {OnlineChipModule} from '../../online_chip/module';
import {RecentClientFlowsModule} from '../recent_client_flows/module';

import {RecentActivity} from './recent_activity';

/**
 * Module for the RecentActivity component.
 */
@NgModule({
  imports: [
    // Core Angular modules.
    CommonModule,
    RouterModule,

    // GRR modules.
    OnlineChipModule,
    RecentClientFlowsModule,
  ],
  declarations: [RecentActivity],
  exports: [RecentActivity]
})
export class RecentActivityModule {
}