import {ChangeDetectionStrategy, Component, OnDestroy} from '@angular/core';
import {Title} from '@angular/platform-browser';
import {ActivatedRoute} from '@angular/router';
import {combineLatest} from 'rxjs';
import {map, takeUntil} from 'rxjs/operators';

import {RequestStatusType} from '../../lib/api/track_request';
import {assertNonNull} from '../../lib/preconditions';
import {observeOnDestroy} from '../../lib/reactive';
import {ApprovalPageGlobalStore} from '../../store/approval_page_global_store';
import {ClientPageGlobalStore} from '../../store/client_page_global_store';
import {ConfigGlobalStore} from '../../store/config_global_store';
import {SelectedClientGlobalStore} from '../../store/selected_client_global_store';
import {UserGlobalStore} from '../../store/user_global_store';

/** Component that displays an approval request. */
@Component({
  standalone: false,
  selector: 'app-approval-page',
  templateUrl: './approval_page.ng.html',
  styleUrls: ['./approval_page.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ApprovalPage implements OnDestroy {
  readonly ngOnDestroy = observeOnDestroy(this);

  readonly approval$;

  // TODO: Evaluate moving canGrant$ to ApprovalPageGlobalStore,
  // which would then depend on UserGlobalStore.
  private readonly canGrant$;

  readonly requestInProgress$;

  readonly disabled$;

  longExpiration?: boolean;
  defaultAccessDurationDays?: number;

  constructor(
    readonly route: ActivatedRoute,
    private readonly title: Title,
    private readonly approvalPageGlobalStore: ApprovalPageGlobalStore,
    private readonly clientPageGlobalStore: ClientPageGlobalStore,
    private readonly userGlobalStore: UserGlobalStore,
    private readonly selectedClientGlobalStore: SelectedClientGlobalStore,
    private readonly configGlobalStore: ConfigGlobalStore,
  ) {
    this.approval$ = this.approvalPageGlobalStore.approval$;
    this.canGrant$ = combineLatest([
      this.approval$,
      this.userGlobalStore.currentUser$,
    ]).pipe(
      map(
        ([approval, user]) =>
          approval &&
          user.name !== approval.requestor &&
          !approval.approvers.includes(user.name),
      ),
    );
    this.requestInProgress$ =
      this.approvalPageGlobalStore.grantRequestStatus$.pipe(
        map((status) => status?.status === RequestStatusType.SENT),
      );
    this.disabled$ = combineLatest([
      this.canGrant$,
      this.requestInProgress$,
    ]).pipe(
      map(([canGrant, requestInProgress]) => !canGrant || requestInProgress),
    );
    route.paramMap
      .pipe(takeUntil(this.ngOnDestroy.triggered$))
      .subscribe((params) => {
        const clientId = params.get('clientId');
        const requestor = params.get('requestor');
        const approvalId = params.get('approvalId');

        assertNonNull(clientId, 'clientId');
        assertNonNull(requestor, 'requestor');
        assertNonNull(approvalId, 'approvalId');

        this.approvalPageGlobalStore.selectApproval({
          clientId,
          requestor,
          approvalId,
        });
        this.clientPageGlobalStore.selectClient(clientId);
        this.selectedClientGlobalStore.selectClientId(clientId);
      });

    this.approvalPageGlobalStore.approval$
      .pipe(takeUntil(this.ngOnDestroy.triggered$))
      .subscribe((approval) => {
        if (!approval) {
          this.title.setTitle('GRR | Approval');
        } else {
          const client = approval.subject;
          const fqdn = client.knowledgeBase?.fqdn;
          const info = fqdn ? `${fqdn} (${client.clientId})` : client.clientId;
          this.title.setTitle(
            `GRR | Approval for ${approval.requestor} on ${info}`,
          );

          this.configGlobalStore.uiConfig$
            .pipe(takeUntil(this.ngOnDestroy.triggered$))
            .subscribe((config) => {
              if (!config) return;
              if (!config.defaultAccessDurationSeconds) return;
              if (!approval.expirationTime) return;

              this.defaultAccessDurationDays =
                Number(config.defaultAccessDurationSeconds) / (24 * 60 * 60);

              const watermark = new Date();
              watermark.setDate(
                watermark.getDate() + this.defaultAccessDurationDays,
              );
              // TODO: Use a daylight saving time resistant time
              // measurement.
              watermark.setHours(watermark.getHours() + 1);

              this.longExpiration = approval.expirationTime > watermark;
            });
        }
      });
  }

  grantApproval() {
    this.approvalPageGlobalStore.grantApproval();
  }
}
