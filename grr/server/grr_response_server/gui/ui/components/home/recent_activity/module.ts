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
    // TODO: re-enable clang format when solved.
    // clang-format off
    // keep-sorted start block=yes
    CommonModule,
    OnlineChipModule,
    RecentClientFlowsModule,
    RouterModule,
    // keep-sorted end
    // clang-format on
  ],
  declarations: [RecentActivity],
  exports: [RecentActivity]
})
export class RecentActivityModule {
}