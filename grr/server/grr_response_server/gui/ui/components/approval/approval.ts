import {ChangeDetectionStrategy, Component, OnDestroy} from '@angular/core';
import {FormControl, FormGroup} from '@angular/forms';
import {Subject} from 'rxjs';
import {filter, map, withLatestFrom} from 'rxjs/operators';

import {ClientApproval} from '../../lib/models/client';
import {isNonNull} from '../../lib/preconditions';
import {ClientPageFacade} from '../../store/client_page_facade';
import {ConfigFacade} from '../../store/config_facade';

/**
 * Component to request approval for the current client.
 */
@Component({
  selector: 'approval',
  templateUrl: './approval.ng.html',
  styleUrls: ['./approval.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Approval implements OnDestroy {
  readonly form = new FormGroup({
    approvers: new FormControl(''),
    reason: new FormControl(''),
    ccEnabled: new FormControl(true),
  });

  readonly ccEmail$ = this.configFacade.approvalConfig$.pipe(
      map(config => config.optionalCcEmail));

  readonly latestApproval$ = this.clientPageFacade.latestApproval$.pipe(
      filter(isNonNull), map(approval => {
        const url = new URL(window.location.origin);
        url.hash = `/users/${approval.requestor}/approvals/client/${
            approval.clientId}/${approval.approvalId}`;
        return {...approval, url: url.toString()};
      }));

  readonly scheduledFlows$ = this.clientPageFacade.scheduledFlows$;

  private readonly submit$ = new Subject<void>();

  constructor(
      private readonly clientPageFacade: ClientPageFacade,
      private readonly configFacade: ConfigFacade,
  ) {
    this.submit$
        .pipe(withLatestFrom(
            this.form.valueChanges, this.clientPageFacade.selectedClient$,
            this.ccEmail$))
        .subscribe(([_, form, client, ccEmail]) => {
          this.clientPageFacade.requestApproval({
            clientId: client.clientId,
            approvers: form.approvers.trim().split(/[, ]+/),
            reason: form.reason,
            cc: form.ccEnabled && ccEmail ? [ccEmail] : [],
          });
        });
  }

  ngOnDestroy() {
    this.submit$.complete();
  }

  submitRequest() {
    this.submit$.next();
  }
}
