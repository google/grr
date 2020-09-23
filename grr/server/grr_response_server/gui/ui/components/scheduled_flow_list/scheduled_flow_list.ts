import {ChangeDetectionStrategy, Component} from '@angular/core';

import {ScheduledFlow} from '../../lib/models/flow';
import {ClientPageFacade} from '../../store/client_page_facade';

/** Component that displays flows scheduled to run on a client. */
@Component({
  selector: 'scheduled-flow-list',
  templateUrl: './scheduled_flow_list.ng.html',
  styleUrls: ['./scheduled_flow_list.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ScheduledFlowList {
  readonly scheduledFlows$ = this.clientPageFacade.scheduledFlows$;

  constructor(
      private readonly clientPageFacade: ClientPageFacade,
  ) {}

  unscheduleFlow(scheduledFlowId: string) {
    this.clientPageFacade.unscheduleFlow(scheduledFlowId);
  }

  trackScheduledFlow(index: number, scheduledFlow: ScheduledFlow) {
    return scheduledFlow.scheduledFlowId;
  }
}
