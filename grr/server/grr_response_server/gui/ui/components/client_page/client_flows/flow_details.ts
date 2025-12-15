import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  inject,
  Input as RouterInput,
} from '@angular/core';
import {MatTabsModule} from '@angular/material/tabs';
import {RouterModule} from '@angular/router';

import {ClientStore} from '../../../store/client_store';
import {FlowStore} from '../../../store/flow_store';

/**
 * Component displaying details of a single flow.
 */
@Component({
  selector: 'flow-details',
  templateUrl: './flow_details.ng.html',
  styleUrls: ['./flow_details.scss'],
  imports: [CommonModule, RouterModule, MatTabsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [FlowStore],
})
export class FlowDetails {
  readonly clientStore = inject(ClientStore);
  readonly flowStore = inject(FlowStore);

  @RouterInput()
  set flowId(flowId: string) {
    this.clientStore.pollFlow(flowId);

    const clientId = this.clientStore.clientId();
    if (clientId === null) {
      throw new Error('Client ID is not set.');
    }
    this.flowStore.initialize(clientId, flowId);
  }
}
