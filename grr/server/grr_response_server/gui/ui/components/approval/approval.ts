import {COMMA, ENTER, SPACE} from '@angular/cdk/keycodes';
import {Location} from '@angular/common';
import {ChangeDetectionStrategy, Component, ElementRef, HostBinding, HostListener, OnDestroy, OnInit, ViewChild} from '@angular/core';
import {FormControl, FormGroup} from '@angular/forms';
import {ActivatedRoute, Router} from '@angular/router';
import {Subject} from 'rxjs';
import {filter, map, takeUntil, withLatestFrom} from 'rxjs/operators';

import {isNonNull} from '../../lib/preconditions';
import {observeOnDestroy} from '../../lib/reactive';
import {ClientPageGlobalStore} from '../../store/client_page_global_store';
import {ConfigGlobalStore} from '../../store/config_global_store';

/**
 * Component to request approval for the current client.
 */
@Component({
  selector: 'approval',
  templateUrl: './approval.ng.html',
  styleUrls: ['./approval.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Approval implements OnInit, OnDestroy {
  readonly separatorKeysCodes: number[] = [ENTER, COMMA, SPACE];

  private readonly reason$ = this.route.queryParamMap.pipe(
      map(params => params.get('reason')), filter(isNonNull));

  readonly form = new FormGroup({
    reason: new FormControl(''),
    ccEnabled: new FormControl(true),
  });

  @ViewChild('approversInput') approversInputEl!: ElementRef<HTMLInputElement>;
  readonly approversInputControl = new FormControl('');

  readonly formRequestedApprovers = new Set<string>();

  readonly ccEmail$ = this.configGlobalStore.approvalConfig$.pipe(
      map(config => config.optionalCcEmail));

  @HostBinding('class.closed') hideContent = true;

  showForm: boolean = false;

  readonly latestApproval$ = this.clientPageGlobalStore.latestApproval$.pipe(
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

  readonly latestApprovalState$ =
      this.clientPageGlobalStore.latestApproval$.pipe(
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
      this.clientPageGlobalStore.approverSuggestions$.pipe(
          map(approverSuggestions => approverSuggestions.filter(
                  username => !this.formRequestedApprovers.has(username))));

  private readonly submit$ = new Subject<void>();

  readonly ngOnDestroy = observeOnDestroy();

  constructor(
      private readonly route: ActivatedRoute,
      private readonly clientPageGlobalStore: ClientPageGlobalStore,
      private readonly configGlobalStore: ConfigGlobalStore,
      private readonly router: Router,
      private readonly location: Location,
  ) {
    this.submit$
        .pipe(
            takeUntil(this.ngOnDestroy.triggered$),
            withLatestFrom(
                this.form.valueChanges,
                this.clientPageGlobalStore.selectedClient$,
                this.ccEmail$,
                ),
            )
        .subscribe(([_, form, client, ccEmail]) => {
          this.clientPageGlobalStore.requestApproval({
            clientId: client.clientId,
            approvers: Array.from(this.formRequestedApprovers),
            reason: form.reason,
            cc: form.ccEnabled && ccEmail ? [ccEmail] : [],
          });
        });

    this.approversInputControl.valueChanges.subscribe(value => {
      this.clientPageGlobalStore.suggestApprovers(value);
    });

    // Trigger the suggestion of previously requested approvers.
    this.clientPageGlobalStore.suggestApprovers('');
  }

  ngOnInit() {
    this.reason$.subscribe(reason => {
      this.form.controls['reason'].patchValue(reason);
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

  showContent(event: Event) {
    if (this.hideContent) {
      this.hideContent = false;
      event.stopPropagation();
    }
  }

  addRequestedApprover(username: string) {
    this.formRequestedApprovers.add(username);
    this.approversInputControl.setValue('');
    this.approversInputEl.nativeElement.value = '';
  }

  removeRequestedApprover(username: string) {
    this.formRequestedApprovers.delete(username);
  }

  submitRequest() {
    this.submit$.next();
  }
}
