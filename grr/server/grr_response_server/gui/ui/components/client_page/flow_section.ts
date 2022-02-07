import {ChangeDetectionStrategy, Component} from '@angular/core';
import {first} from 'rxjs/operators';

import {assertNonNull} from '../../lib/preconditions';
import {ClientPageGlobalStore} from '../../store/client_page_global_store';
import {UserGlobalStore} from '../../store/user_global_store';
import {ApprovalParams} from '../approval/approval';

/** Section in ClientPage that shows the flow form and list. */
@Component({
  selector: 'app-flow-section',
  templateUrl: './flow_section.ng.html',
  styleUrls: ['./flow_section.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FlowSection {
  readonly client$ = this.clientPageGlobalStore.selectedClient$;

  readonly currentUser$ = this.userGlobalStore.currentUser$;

  readonly showApprovalView$ = this.clientPageGlobalStore.approvalsEnabled$;

  readonly latestApproval$ = this.clientPageGlobalStore.latestApproval$;

  readonly hasAccess$ = this.clientPageGlobalStore.hasAccess$;

  constructor(
      private readonly clientPageGlobalStore: ClientPageGlobalStore,
      private readonly userGlobalStore: UserGlobalStore,
  ) {}

  requestApproval(approvalParams: ApprovalParams) {
    this.client$.pipe(first()).subscribe(client => {
      assertNonNull(client);
      this.clientPageGlobalStore.requestApproval({
        clientId: client.clientId,
        approvers: approvalParams.approvers,
        reason: approvalParams.reason,
        cc: approvalParams.cc,
      });
    });
  }
}
