import {COMMA, ENTER, SPACE} from '@angular/cdk/keycodes';
import {Location} from '@angular/common';
import {ChangeDetectionStrategy, Component, ElementRef, EventEmitter, HostBinding, HostListener, Input, OnDestroy, Output, ViewChild} from '@angular/core';
import {UntypedFormControl, UntypedFormGroup} from '@angular/forms';
import {ActivatedRoute, Router} from '@angular/router';
import {BehaviorSubject, Subject} from 'rxjs';
import {filter, map, take, takeUntil, withLatestFrom} from 'rxjs/operators';

import {RequestStatusType} from '../../lib/api/track_request';
import {ClientApproval} from '../../lib/models/client';
import {isNonNull} from '../../lib/preconditions';
import {observeOnDestroy} from '../../lib/reactive';
import {ClientPageGlobalStore} from '../../store/client_page_global_store';
import {ConfigGlobalStore} from '../../store/config_global_store';

/**
 * Composed data structure for approval requested params.
 */
export declare interface ApprovalParams {
  approvers: string[];
  reason: string;
  cc: string[];
}

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
  @Input() requestFormOnly = false;

  private readonly latestApproval$ =
      new BehaviorSubject<ClientApproval|null>(null);
  @Input()
  set latestApproval(latestApproval: ClientApproval|null) {
    this.latestApproval$.next(latestApproval);
  }
  get latestApproval() {
    return this.latestApproval$.value;
  }
  @Input() showSubmitButton: boolean = true;

  readonly ngOnDestroy = observeOnDestroy(this);

  private readonly reason$ = this.route.queryParamMap.pipe(
      takeUntil(this.ngOnDestroy.triggered$),
      map(params => params.get('reason')),
      filter(isNonNull),
  );

  readonly controls = {
    reason: new UntypedFormControl(''),
    ccEnabled: new UntypedFormControl(true),
  };
  readonly form = new UntypedFormGroup(this.controls);

  @ViewChild('approversInput') approversInputEl!: ElementRef<HTMLInputElement>;
  @Output() readonly approvalParams = new EventEmitter<ApprovalParams>();
  readonly approversInputControl = new UntypedFormControl('');

  readonly formRequestedApprovers = new Set<string>();

  readonly ccEmail$ = this.configGlobalStore.approvalConfig$.pipe(
      map(config => config.optionalCcEmail));

  @HostBinding('class.closed') hideContent = false;

  readonly approverSuggestions$ =
      this.clientPageGlobalStore.approverSuggestions$.pipe(map(
          approverSuggestions =>
              (approverSuggestions ?? [])
                  .filter(
                      username => !this.formRequestedApprovers.has(username))));


  private readonly submit$ = new Subject<void>();

  showForm: boolean = false;

  readonly url$ = this.latestApproval$.pipe(
      map(latestApproval => {
        if (!latestApproval) {
          return null;
        }

        const pathTree = this.router.createUrlTree([
          'clients',
          latestApproval.clientId,
          'users',
          latestApproval.requestor,
          'approvals',
          latestApproval.approvalId,
        ]);
        const url = new URL(window.location.origin);
        url.pathname = this.location.prepareExternalUrl(pathTree.toString());
        return url.toString();
      }),
  );

  readonly requestInProgress$ =
      this.clientPageGlobalStore.requestApprovalStatus$.pipe(
          map(status => status?.status === RequestStatusType.SENT));

  readonly submitDisabled$ =
      this.clientPageGlobalStore.requestApprovalStatus$.pipe(
          map(status => status?.status === RequestStatusType.SENT ||
                  status?.status === RequestStatusType.SUCCESS));

  readonly error$ = this.clientPageGlobalStore.requestApprovalStatus$.pipe(
      map(status => status?.status === RequestStatusType.ERROR ? status.error :
                                                                 null));

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
                this.ccEmail$,
                ),
            )
        // tslint:disable-next-line:enforce-name-casing
        .subscribe(([_, form, ccEmail]) => {
          const approvers = Array.from(this.formRequestedApprovers);
          const reason = form.reason;
          const cc = form.ccEnabled && ccEmail ? [ccEmail] : [];
          this.approvalParams.emit({approvers, reason, cc});
        });

    this.approversInputControl.valueChanges.subscribe(value => {
      this.clientPageGlobalStore.suggestApprovers(value);
    });

    // Trigger the suggestion of previously requested approvers.
    this.clientPageGlobalStore.suggestApprovers('');

    this.reason$.pipe(takeUntil(this.ngOnDestroy.triggered$))
        .subscribe(reason => {
          this.form.controls['reason'].patchValue(reason);
        });

    this.latestApproval$
        .pipe(
            takeUntil(this.ngOnDestroy.triggered$),
            filter(isNonNull),
            filter(approval => approval.status.type === 'valid'),
            take(1),
            )
        .subscribe((approval) => {
          this.hideContent = true;
        });

    this.clientPageGlobalStore.requestApprovalStatus$
        .pipe(
            takeUntil(this.ngOnDestroy.triggered$),
            filter(status => status?.status === RequestStatusType.SUCCESS),
            )
        .subscribe(() => {
          this.showForm = false;
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

  submitRequest(event?: Event) {
    event?.preventDefault();
    this.submit$.next();
  }
}
