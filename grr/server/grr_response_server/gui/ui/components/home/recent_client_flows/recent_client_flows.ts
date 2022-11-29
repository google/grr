import {ChangeDetectionStrategy, Component, Input} from '@angular/core';
import {BehaviorSubject, combineLatest, Observable} from 'rxjs';
import {map} from 'rxjs/operators';

import {ClientApproval} from '../../../lib/models/client';
import {FlowWithDescriptor, withDescriptor} from '../../../lib/models/flow';
import {ConfigGlobalStore} from '../../../store/config_global_store';
import {RecentClientFlowsLocalStore} from '../../../store/recent_client_flows_local_store';

/**
 * Displays a recent accessed client.
 */
@Component({
  selector: 'app-recent-client-flows',
  templateUrl: './recent_client_flows.ng.html',
  styleUrls: ['./recent_client_flows.scss'],
  providers: [RecentClientFlowsLocalStore],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RecentClientFlows {
  constructor(
      private readonly configGlobalStore: ConfigGlobalStore,
      private readonly recentClientFlowsLocalStore: RecentClientFlowsLocalStore,
  ) {}

  private readonly approval$ = new BehaviorSubject<ClientApproval|null>(null);

  readonly entries$: Observable<readonly FlowWithDescriptor[]> =
      combineLatest([
        this.recentClientFlowsLocalStore.flowListEntries$,
        this.configGlobalStore.flowDescriptors$,
      ])
          .pipe(
              map(([{flows}, fds]) => flows?.map(withDescriptor(fds)) ?? []),
          );

  entryTrackByFunction(index: number, entry: FlowWithDescriptor) {
    return entry.flow.flowId;
  }

  /**
   * Approval to display.
   */
  @Input()
  set approval(approval: ClientApproval|null|undefined) {
    this.approval$.next(approval ?? null);
    if (approval) {
      this.recentClientFlowsLocalStore.selectClient(approval.clientId);
    }
  }

  get approval() {
    return this.approval$.value;
  }
}