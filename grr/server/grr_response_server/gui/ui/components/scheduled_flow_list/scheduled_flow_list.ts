import {ChangeDetectionStrategy, ChangeDetectorRef, Component, HostBinding, Input, OnChanges, OnDestroy, OnInit, SimpleChanges} from '@angular/core';
import {map, takeUntil} from 'rxjs/operators';

import {ScheduledFlow} from '../../lib/models/flow';
import {observeOnDestroy} from '../../lib/reactive';
import {ScheduledFlowGlobalStore} from '../../store/scheduled_flow_global_store';
import {UserGlobalStore} from '../../store/user_global_store';

/** Component that displays flows scheduled to run on a client. */
@Component({
  selector: 'scheduled-flow-list',
  templateUrl: './scheduled_flow_list.ng.html',
  styleUrls: ['./scheduled_flow_list.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ScheduledFlowList implements OnInit, OnChanges, OnDestroy {
  @Input() creator?: string;
  @Input() clientId?: string;

  readonly scheduledFlows$ = this.store.scheduledFlows$;

  readonly currentUsername$ = this.userGlobalStore.currentUser$.pipe(
      map(user => user.name),
  );

  // Use Angular's [hidden] directive to hide this view until scheduled flows
  // have been loaded. This prevents spaces around the empty view during
  // loading.
  @HostBinding('hidden') isHidden = true;

  readonly ngOnDestroy = observeOnDestroy(this);

  constructor(
      private readonly store: ScheduledFlowGlobalStore,
      private readonly userGlobalStore: UserGlobalStore,
      private readonly cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.scheduledFlows$
        .pipe(
            takeUntil(this.ngOnDestroy.triggered$),
            )
        .subscribe(scheduledFlows => {
          this.isHidden = scheduledFlows.length === 0;
          this.cdr.detectChanges();
        });
  }

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
