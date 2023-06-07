import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatIconModule} from '@angular/material/icon';
import {MatLegacyChipsModule} from '@angular/material/legacy-chips';
import {RouterModule} from '@angular/router';

import {ApprovalChipModule} from '../../../components/approval_chip/approval_chip_module';
import {FlowDetailsModule} from '../../flow_details/module';
import {OnlineChipModule} from '../../online_chip/module';

import {RecentClientFlows} from './recent_client_flows';

/**
 * Module for the RecentClientFlows component.
 */
@NgModule({
  imports: [
    // Core Angular modules.
    CommonModule,
    RouterModule,

    // Angular Material modules.
    MatLegacyChipsModule,
    MatIconModule,

    // GRR modules.
    ApprovalChipModule,
    OnlineChipModule,
    FlowDetailsModule,
  ],
  declarations: [RecentClientFlows],
  exports: [RecentClientFlows]
})
export class RecentClientFlowsModule {
}