import {ChangeDetectionStrategy, Component, Input} from '@angular/core';
import {BehaviorSubject, Observable, combineLatest} from 'rxjs';
import {map} from 'rxjs/operators';

import {type ClientApproval} from '../../../lib/models/client';
import {FlowWithDescriptor, withDescriptor} from '../../../lib/models/flow';
import {isNull} from '../../../lib/preconditions';
import {ConfigGlobalStore} from '../../../store/config_global_store';
import {RecentClientFlowsLocalStore} from '../../../store/recent_client_flows_local_store';

/**
 * Displays a recent accessed client.
 */
@Component({
  standalone: false,
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
  ) {
    this.showApprovalChip$ = this.recentClientFlowsLocalStore.hasAccess$.pipe(
      map((hasAccess) => {
        if (isNull(this.approval) || isNull(hasAccess)) {
          return false;
        }
        const inconsistency1 =
          hasAccess === true && this.approval.status.type !== 'valid';
        const inconsistency2 =
          hasAccess === false && this.approval.status.type === 'valid';
        return !inconsistency1 && !inconsistency2;
      }),
    );
    this.hasAccess$ = this.recentClientFlowsLocalStore.hasAccess$;
    this.entries$ = combineLatest([
      this.recentClientFlowsLocalStore.flowListEntries$,
      this.configGlobalStore.flowDescriptors$,
    ]).pipe(map(([{flows}, fds]) => flows?.map(withDescriptor(fds)) ?? []));
  }

  private readonly approval$ = new BehaviorSubject<ClientApproval | null>(null);

  readonly showApprovalChip$: Observable<boolean>;

  readonly hasAccess$;

  readonly entries$: Observable<readonly FlowWithDescriptor[]>;

  entryTrackByFunction(index: number, entry: FlowWithDescriptor) {
    return entry.flow.flowId;
  }

  /**
   * Approval to display.
   */
  @Input()
  set approval(approval: ClientApproval | null | undefined) {
    this.approval$.next(approval ?? null);
    if (approval) {
      this.recentClientFlowsLocalStore.selectClient(approval.clientId);
    }
  }

  get approval() {
    return this.approval$.value;
  }
}
