import {ChangeDetectionStrategy, ChangeDetectorRef, Component, OnDestroy} from '@angular/core';
import {FormControl, FormGroup} from '@angular/forms';
import {Subject} from 'rxjs';
import {map, takeUntil, withLatestFrom} from 'rxjs/operators';

import {ClientApproval} from '../../lib/models/client';
import {ClientFacade} from '../../store/client_facade';

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

  readonly ccEmail$ = this.clientFacade.approvalConfig$.pipe(
      map(config => config ? config.optionalCcEmail : undefined),
  );

  latestApproval?: ClientApproval;

  private readonly submit$ = new Subject<void>();
  private readonly unsubscribe$ = new Subject<void>();

  constructor(
      private readonly clientFacade: ClientFacade,
      private readonly cdr: ChangeDetectorRef,
  ) {
    this.submit$
        .pipe(
            takeUntil(this.unsubscribe$),
            withLatestFrom(
                this.form.valueChanges, this.clientFacade.selectedClient$,
                this.ccEmail$))
        .subscribe(([_, form, client, ccEmail]) => {
          this.clientFacade.requestApproval({
            clientId: client.clientId,
            approvers: form.approvers.trim().split(/[, ]+/),
            reason: form.reason,
            cc: form.ccEnabled && ccEmail ? [ccEmail] : [],
          });
        });

    this.clientFacade.fetchApprovalConfig();

    this.clientFacade.latestApproval$.pipe(takeUntil(this.unsubscribe$))
        .subscribe(a => {
          this.latestApproval = a;
          this.cdr.markForCheck();
        });
  }

  ngOnDestroy() {
    this.unsubscribe$.next();
    this.unsubscribe$.complete();
  }

  submitRequest() {
    this.submit$.next();
  }
}
