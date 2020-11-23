import {COMMA, ENTER, SPACE} from '@angular/cdk/keycodes';
import {Location} from '@angular/common';
import {ChangeDetectionStrategy, Component, ElementRef, HostBinding, HostListener, OnDestroy, ViewChild} from '@angular/core';
import {FormControl, FormGroup} from '@angular/forms';
import {Router} from '@angular/router';
import {Subject} from 'rxjs';
import {filter, map, withLatestFrom} from 'rxjs/operators';

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
  readonly separatorKeysCodes: number[] = [ENTER, COMMA, SPACE];

  readonly form = new FormGroup({
    reason: new FormControl(''),
    ccEnabled: new FormControl(true),
  });

  @ViewChild('approversInput') approversInputEl!: ElementRef<HTMLInputElement>;
  readonly approversInputControl = new FormControl('');

  readonly formRequestedApprovers = new Set<string>();

  readonly ccEmail$ = this.configFacade.approvalConfig$.pipe(
      map(config => config.optionalCcEmail));

  @HostBinding('class.closed') hideContent = true;

  showForm: boolean = false;

  readonly latestApproval$ = this.clientPageFacade.latestApproval$.pipe(
      filter(isNonNull),
      map(approval => {
        const pathTree = this.router.createUrlTree([
          'clients',
          approval.clientId,
          'users',
          approval.requestor,
          'approvals',
          approval.approvalId,
        ]);

        const url = new URL(window.location.origin);
        url.pathname = this.location.prepareExternalUrl(pathTree.toString());

        return {
          ...approval,
          url: url.toString(),
        };
      }),
  );

  readonly latestApprovalState$ = this.clientPageFacade.latestApproval$.pipe(
      map(approval => {
        switch (approval?.status.type) {
          case 'valid':
            return 'valid';
          case 'pending':
            return 'pending';
          default:
            return 'missing';
        }
      }),
  );

  readonly approverSuggestions$ =
      this.clientPageFacade.approverSuggestions$.pipe(
          map(approverSuggestions => approverSuggestions.filter(
                  username => !this.formRequestedApprovers.has(username))));

  private readonly submit$ = new Subject<void>();

  constructor(
      private readonly clientPageFacade: ClientPageFacade,
      private readonly configFacade: ConfigFacade,
      private readonly router: Router,
      private readonly location: Location,
  ) {
    this.submit$
        .pipe(withLatestFrom(
            this.form.valueChanges, this.clientPageFacade.selectedClient$,
            this.ccEmail$))
        .subscribe(([_, form, client, ccEmail]) => {
          this.clientPageFacade.requestApproval({
            clientId: client.clientId,
            approvers: Array.from(this.formRequestedApprovers),
            reason: form.reason,
            cc: form.ccEnabled && ccEmail ? [ccEmail] : [],
          });
        });

    this.approversInputControl.valueChanges.subscribe(value => {
      this.clientPageFacade.suggestApprovers(value);
    });
  }

  @HostListener('click')
  onClick() {
    this.hideContent = false;
  }

  toggleContent(event: Event) {
    this.hideContent = !this.hideContent;
    event.stopPropagation();
  }

  addRequestedApprover(username: string) {
    this.formRequestedApprovers.add(username);
    this.approversInputControl.setValue('');
    this.approversInputEl.nativeElement.value = '';
  }

  removeRequestedApprover(username: string) {
    this.formRequestedApprovers.delete(username);
  }

  ngOnDestroy() {
    this.submit$.complete();
  }

  submitRequest() {
    this.submit$.next();
  }
}
