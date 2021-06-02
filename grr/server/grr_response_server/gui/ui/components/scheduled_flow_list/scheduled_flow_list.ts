import {ChangeDetectionStrategy, Component, Input, OnChanges, SimpleChanges} from '@angular/core';
import {map} from 'rxjs/operators';

import {ScheduledFlow} from '../../lib/models/flow';
import {ScheduledFlowGlobalStore} from '../../store/scheduled_flow_global_store';
import {UserGlobalStore} from '../../store/user_global_store';

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

  readonly scheduledFlows$ = this.store.scheduledFlows$;

  readonly currentUsername$ = this.userGlobalStore.currentUser$.pipe(
      map(user => user.name),
  );

  constructor(
      private readonly store: ScheduledFlowGlobalStore,
      private readonly userGlobalStore: UserGlobalStore,
  ) {}

  ngOnChanges(changes: SimpleChanges): void {
    this.store.selectSource({creator: this.creator, clientId: this.clientId});
  }

  unscheduleFlow(scheduledFlowId: string) {
    this.store.unscheduleFlow(scheduledFlowId);
  }

  trackScheduledFlow(index: number, scheduledFlow: ScheduledFlow) {
    return scheduledFlow.scheduledFlowId;
  }
}
