import {COMMA, ENTER, SPACE} from '@angular/cdk/keycodes';
import {Location} from '@angular/common';
import {AfterViewInit, ChangeDetectionStrategy, Component, ElementRef, EventEmitter, HostBinding, HostListener, Input, OnDestroy, Output, ViewChild} from '@angular/core';
import {FormControl, FormGroup, Validators} from '@angular/forms';
import {ActivatedRoute, Router} from '@angular/router';
import {BehaviorSubject, Subject} from 'rxjs';
import {map, takeUntil, withLatestFrom} from 'rxjs/operators';

import {type RequestStatus, RequestStatusType} from '../../lib/api/track_request';
import {type Approval} from '../../lib/models/user';
import {observeOnDestroy} from '../../lib/reactive';
import {ApprovalCardLocalStore} from '../../store/approval_card_local_store';
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
  selector: 'approval-card',
  templateUrl: './approval_card.ng.html',
  styleUrls: ['./approval_card.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [ApprovalCardLocalStore],
})
export class ApprovalCard implements OnDestroy, AfterViewInit {
  readonly separatorKeysCodes: number[] = [ENTER, COMMA, SPACE];

  @Input() @HostBinding('class.closed') hideContent = false;
  @Input() requestFormOnly = false;
  @Input() latestApproval: Approval|null = null;
  @Input() showSubmitButton = true;
  @Input() urlTree: string[] = [];
  @Input() validateOnStart = false;

  private readonly requestApprovalStatus$ =
      new BehaviorSubject<RequestStatus<Approval, string>|null>(null);
  @Input()
  set requestApprovalStatus(requestApprovalStatus:
                                RequestStatus<Approval, string>|null) {
    this.requestApprovalStatus$.next(requestApprovalStatus);
  }
  get requestApprovalStatus() {
    return this.requestApprovalStatus$.value;
  }

  readonly ngOnDestroy = observeOnDestroy(this);

  showForm = false;

  readonly controls = {
    reason: new FormControl(
        '', {nonNullable: true, validators: [Validators.required]}),
    ccEnabled: new FormControl(true),
    approvers: new FormControl(''),
  };
  readonly form = new FormGroup(this.controls);

  readonly formRequestedApprovers = new Set<string>();
  @ViewChild('approversInput') approversInputEl!: ElementRef<HTMLInputElement>;
  readonly approverSuggestions$ =
      this.approvalCardLocalStore.approverSuggestions$.pipe(map(
          approverSuggestions =>
              (approverSuggestions ?? [])
                  .filter(
                      username => !this.formRequestedApprovers.has(username))));

  // `approvalParams` emits whenever `submitRequest` is called.
  @Output() readonly approvalParams = new EventEmitter<ApprovalParams>();
  private readonly submit$ = new Subject<void>();
  submitRequest(event?: Event) {
    event?.preventDefault();
    this.submit$.next();
  }

  readonly ccEmail$ = this.configGlobalStore.approvalConfig$.pipe(
      map(config => config.optionalCcEmail));

  readonly requestInProgress$ = this.requestApprovalStatus$.pipe(
      map(status => status?.status === RequestStatusType.SENT));

  readonly submitDisabled$ = this.requestApprovalStatus$.pipe(
      map(status => status?.status === RequestStatusType.SENT ||
              status?.status === RequestStatusType.SUCCESS));

  readonly error$ = this.requestApprovalStatus$.pipe(
      map(status => status?.status === RequestStatusType.ERROR ? status.error :
                                                                 null));

  constructor(
      private readonly route: ActivatedRoute,
      private readonly approvalCardLocalStore: ApprovalCardLocalStore,
      private readonly configGlobalStore: ConfigGlobalStore,
      private readonly router: Router,
      private readonly location: Location,
  ) {
    // Trigger the suggestion of previously requested approvers.
    this.approvalCardLocalStore.suggestApprovers('');

    this.controls.approvers.valueChanges.subscribe(value => {
      this.approvalCardLocalStore.suggestApprovers(value ?? '');
    });

    this.route.queryParams.pipe(takeUntil(this.ngOnDestroy.triggered$))
        .subscribe(params => {
          const reason = params['reason'];
          if (reason) {
            this.controls.reason.patchValue(reason);
          }
        });

    this.submit$
        .pipe(
            takeUntil(this.ngOnDestroy.triggered$),
            withLatestFrom(this.ccEmail$),
            )
        // tslint:disable-next-line:enforce-name-casing
        .subscribe(([_, ccEmail]) => {
          // Mark reason as touched so validator is triggered.
          this.controls.reason.markAsTouched();
          if (!this.form.valid) return;

          // Only emit if form is valid.
          const approvers = Array.from(this.formRequestedApprovers);
          const reason = this.controls.reason.value;
          const cc = this.controls.ccEnabled.value && ccEmail ? [ccEmail] : [];
          this.approvalParams.emit({approvers, reason, cc});
        });
  }

  ngAfterViewInit() {
    if (this.validateOnStart) {
      // Mark reason as touched so validator is triggered.
      this.controls.reason.markAsTouched();
    }
  }

  get url() {
    if (!this.urlTree) {
      return '';
    }
    const pathTree = this.router.createUrlTree(this.urlTree);
    const url = new URL(window.location.origin);
    url.pathname = this.location.prepareExternalUrl(pathTree.toString());
    return url.toString();
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
    this.controls.approvers.setValue('');
    this.approversInputEl.nativeElement.value = '';
  }

  removeRequestedApprover(username: string) {
    this.formRequestedApprovers.delete(username);
  }
}
