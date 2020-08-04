import {ChangeDetectionStrategy, ChangeDetectorRef, Component, OnDestroy} from '@angular/core';
import {FormControl, FormGroup} from '@angular/forms';
import {Subject} from 'rxjs';
import {map, takeUntil, withLatestFrom} from 'rxjs/operators';

import {ClientApproval} from '../../lib/models/client';
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

  latestApproval?: ClientApproval;

  scheduledFlows$ = this.clientPageFacade.scheduledFlows$;

  private readonly submit$ = new Subject<void>();
  private readonly unsubscribe$ = new Subject<void>();

  constructor(
      private readonly clientPageFacade: ClientPageFacade,
      private readonly configFacade: ConfigFacade,
      private readonly cdr: ChangeDetectorRef,
  ) {
    this.submit$
        .pipe(
            takeUntil(this.unsubscribe$),
            withLatestFrom(
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

    this.clientPageFacade.latestApproval$.pipe(takeUntil(this.unsubscribe$))
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
