import {ChangeDetectionStrategy, Component, Input, OnChanges, SimpleChanges} from '@angular/core';
import {map} from 'rxjs/operators';

import {ScheduledFlow} from '../../lib/models/flow';
import {ScheduledFlowFacade} from '../../store/scheduled_flow_facade';
import {UserFacade} from '../../store/user_facade';

/** Component that displays flows scheduled to run on a client. */
@Component({
  selector: 'scheduled-flow-list',
  templateUrl: './scheduled_flow_list.ng.html',
  styleUrls: ['./scheduled_flow_list.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ScheduledFlowList implements OnChanges {
  @Input() creator?: string;
  @Input() clientId?: string;

  readonly scheduledFlows$ = this.facade.scheduledFlows$;

  readonly currentUsername$ = this.userFacade.currentUser$.pipe(
      map(user => user.name),
  );

  constructor(
      private readonly facade: ScheduledFlowFacade,
      private readonly userFacade: UserFacade,
  ) {}

  ngOnChanges(changes: SimpleChanges): void {
    this.facade.selectSource({creator: this.creator, clientId: this.clientId});
  }

  unscheduleFlow(scheduledFlowId: string) {
    this.facade.unscheduleFlow(scheduledFlowId);
  }

  trackScheduledFlow(index: number, scheduledFlow: ScheduledFlow) {
    return scheduledFlow.scheduledFlowId;
  }
}
