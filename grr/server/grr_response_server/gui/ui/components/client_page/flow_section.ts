import {ChangeDetectionStrategy, Component} from '@angular/core';
import {first} from 'rxjs/operators';

import {assertNonNull} from '../../lib/preconditions';
import {ClientPageGlobalStore} from '../../store/client_page_global_store';
import {UserGlobalStore} from '../../store/user_global_store';
import {ApprovalParams} from '../approval_card/approval_card';

/** Section in ClientPage that shows the flow form and list. */
@Component({
  standalone: false,
  selector: 'app-flow-section',
  templateUrl: './flow_section.ng.html',
  styleUrls: ['./flow_section.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FlowSection {
  readonly client$;

  readonly currentUser$;

  readonly showApprovalView$;

  readonly latestApproval$;

  readonly requestApprovalStatus$;

  readonly clientApprovalRoute$;

  readonly hasAccess$;

  constructor(
    private readonly clientPageGlobalStore: ClientPageGlobalStore,
    private readonly userGlobalStore: UserGlobalStore,
  ) {
    this.client$ = this.clientPageGlobalStore.selectedClient$;
    this.currentUser$ = this.userGlobalStore.currentUser$;
    this.showApprovalView$ = this.clientPageGlobalStore.approvalsEnabled$;
    this.latestApproval$ = this.clientPageGlobalStore.latestApproval$;
    this.requestApprovalStatus$ =
      this.clientPageGlobalStore.requestApprovalStatus$;
    this.clientApprovalRoute$ = this.clientPageGlobalStore.clientApprovalRoute$;
    this.hasAccess$ = this.clientPageGlobalStore.hasAccess$;
  }

  requestApproval(approvalParams: ApprovalParams) {
    this.client$.pipe(first()).subscribe((client) => {
      assertNonNull(client);
      this.clientPageGlobalStore.requestClientApproval({
        clientId: client.clientId,
        approvers: approvalParams.approvers,
        reason: approvalParams.reason,
        cc: approvalParams.cc,
        expirationTimeUs: approvalParams.expirationTimeUs,
      });
    });
  }
}
