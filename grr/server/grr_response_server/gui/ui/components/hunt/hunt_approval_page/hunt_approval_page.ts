import {ChangeDetectionStrategy, Component, OnDestroy} from '@angular/core';
import {Title} from '@angular/platform-browser';
import {ActivatedRoute} from '@angular/router';
import {combineLatest} from 'rxjs';
import {map, takeUntil} from 'rxjs/operators';

import {RequestStatusType} from '../../../lib/api/track_request';
import {assertNonNull} from '../../../lib/preconditions';
import {observeOnDestroy} from '../../../lib/reactive';
import {HuntApprovalPageGlobalStore} from '../../../store/hunt_approval_page_global_store';
import {UserGlobalStore} from '../../../store/user_global_store';

/** Component that displays a hunt request. */
@Component({
  templateUrl: './hunt_approval_page.ng.html',
  styleUrls: ['./hunt_approval_page.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HuntApprovalPage implements OnDestroy {
  readonly ngOnDestroy = observeOnDestroy(this);

  protected readonly approval$ = this.huntApprovalPageGlobalStore.approval$;

  private readonly canGrant$ =
      combineLatest([this.approval$, this.userGlobalStore.currentUser$])
          .pipe(
              map(([approval, user]) => approval &&
                      user.name !== approval.requestor &&
                      !approval.approvers.includes(user.name)));

  protected readonly requestInProgress$ =
      this.huntApprovalPageGlobalStore.grantRequestStatus$.pipe(
          map(status => status?.status === RequestStatusType.SENT));

  protected readonly disabled$ =
      combineLatest([this.canGrant$, this.requestInProgress$, this.approval$])
          .pipe(
              map(([canGrant, requestInProgress, approval]) => !canGrant ||
                      requestInProgress || approval?.status.type === 'valid'),
          );

  constructor(
      readonly route: ActivatedRoute,
      private readonly huntApprovalPageGlobalStore: HuntApprovalPageGlobalStore,
      private readonly title: Title,
      private readonly userGlobalStore: UserGlobalStore) {
    route.paramMap
        .pipe(
            takeUntil(this.ngOnDestroy.triggered$),
            )
        .subscribe((params) => {
          const huntId = params.get('huntId');
          const requestor = params.get('requestor');
          const approvalId = params.get('approvalId');

          assertNonNull(huntId, 'huntId');
          assertNonNull(requestor, 'requestor');
          assertNonNull(approvalId, 'approvalId');

          this.huntApprovalPageGlobalStore.selectHuntApproval(
              {huntId, requestor, approvalId});
        });

    this.huntApprovalPageGlobalStore.approval$
        .pipe(takeUntil(this.ngOnDestroy.triggered$))
        .subscribe(approval => {
          if (!approval) {
            this.title.setTitle('GRR | Approval');
          } else {
            const hunt = approval.subject;
            this.title.setTitle(
                `GRR | Approval for ${approval.requestor} on ${hunt.huntId}`);
          }
        });
  }

  protected grantApproval() {
    this.huntApprovalPageGlobalStore.grantApproval();
  }
}
