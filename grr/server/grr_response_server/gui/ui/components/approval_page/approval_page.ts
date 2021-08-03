import {Component, OnDestroy} from '@angular/core';
import {Title} from '@angular/platform-browser';
import {ActivatedRoute} from '@angular/router';
import {combineLatest} from 'rxjs';
import {map, takeUntil, tap} from 'rxjs/operators';

import {ClientApproval} from '../../lib/models/client';
import {assertNonNull} from '../../lib/preconditions';
import {observeOnDestroy} from '../../lib/reactive';
import {ApprovalPageGlobalStore} from '../../store/approval_page_global_store';
import {ClientPageGlobalStore} from '../../store/client_page_global_store';
import {SelectedClientGlobalStore} from '../../store/selected_client_global_store';
import {UserGlobalStore} from '../../store/user_global_store';

/** Component that displays an approval request. */
@Component({
  selector: 'app-approval-page',
  templateUrl: './approval_page.ng.html',
  styleUrls: ['./approval_page.scss']
})
export class ApprovalPage implements OnDestroy {
  readonly ngOnDestroy = observeOnDestroy();

  readonly approval$ = this.approvalPageGlobalStore.approval$.pipe(
      tap((approval) => {
        this.setTitle(approval);
      }),
  );

  readonly canGrant$ =
      combineLatest([this.approval$, this.userGlobalStore.currentUser$])
          .pipe(
              map(([approval, user]) => user.name !== approval.requestor &&
                      !approval.approvers.includes(user.name)));

  constructor(
      readonly route: ActivatedRoute,
      private readonly title: Title,
      private readonly approvalPageGlobalStore: ApprovalPageGlobalStore,
      // TODO(user): Refactor ClientOverview to not require
      // ClientPageGlobalStore in ApprovalPage.
      private readonly clientPageGlobalStore: ClientPageGlobalStore,
      private readonly userGlobalStore: UserGlobalStore,
      private readonly selectedClientGlobalStore: SelectedClientGlobalStore,
  ) {
    this.title.setTitle('GRR | Approval');

    route.paramMap
        .pipe(
            takeUntil(this.ngOnDestroy.triggered$),
            )
        .subscribe((params) => {
          const clientId = params.get('clientId');
          const requestor = params.get('requestor');
          const approvalId = params.get('approvalId');

          assertNonNull(clientId, 'clientId');
          assertNonNull(requestor, 'requestor');
          assertNonNull(approvalId, 'approvalId');

          this.approvalPageGlobalStore.selectApproval(
              {clientId, requestor, approvalId});
          this.clientPageGlobalStore.selectClient(clientId);
          this.selectedClientGlobalStore.selectClientId(clientId);
        });
  }

  private setTitle(approval: ClientApproval) {
    const client = approval.subject;
    const fqdn = client.knowledgeBase?.fqdn;
    const info = fqdn ? `${fqdn} (${client.clientId})` : client.clientId;

    this.title.setTitle(`GRR | Approval for ${approval.requestor} on ${info}`);
  }

  grantApproval() {
    this.approvalPageGlobalStore.grantApproval();
  }
}
