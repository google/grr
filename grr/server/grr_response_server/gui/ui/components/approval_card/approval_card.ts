import {COMMA, ENTER, SPACE} from '@angular/cdk/keycodes';
import {Location} from '@angular/common';
import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  EventEmitter,
  HostBinding,
  HostListener,
  Input,
  OnDestroy,
  Output,
  ViewChild,
} from '@angular/core';
import {FormControl, FormGroup, Validators} from '@angular/forms';
import {ActivatedRoute, Router} from '@angular/router';
import {BehaviorSubject, Observable, Subject} from 'rxjs';
import {
  filter,
  map,
  startWith,
  take,
  takeUntil,
  tap,
  withLatestFrom,
} from 'rxjs/operators';
import {DurationFormControl} from '../../components/form/duration_input/duration_form_control';
import {toDurationString} from '../form/duration_input/duration_conversion';

import {
  RequestStatusType,
  type RequestStatus,
} from '../../lib/api/track_request';
import {type Approval} from '../../lib/models/user';
import {isNonNull} from '../../lib/preconditions';
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
  expirationTimeUs?: string;
}

/**
 * Component to request approval for the current client.
 */
@Component({
  standalone: false,
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
  @Input() latestApproval: Approval | null = null;
  @Input() showSubmitButton = true;
  @Input() urlTree: string[] = [];
  @Input() validateOnStart = false;
  @Input() showDuration = false;
  @Input() editableDuration = false;

  private readonly requestApprovalStatus$ = new BehaviorSubject<RequestStatus<
    Approval,
    string
  > | null>(null);
  @Input()
  set requestApprovalStatus(
    requestApprovalStatus: RequestStatus<Approval, string> | null,
  ) {
    this.requestApprovalStatus$.next(requestApprovalStatus);
  }
  get requestApprovalStatus() {
    return this.requestApprovalStatus$.value;
  }

  readonly ngOnDestroy = observeOnDestroy(this);

  showForm = false;
  showDurationInput = false;
  defaultAccessDurationDays?: number;
  maxAccessDurationDays?: number;

  readonly controls = {
    reason: new FormControl('', {
      nonNullable: true,
      validators: [Validators.required],
    }),
    ccEnabled: new FormControl(true),
    approvers: new FormControl(''),
    duration: new DurationFormControl(0, {
      nonNullable: true,
      validators: [], // Set validator later after maxAccessDurationDays is retrieved from the config
    }),
  };
  readonly form = new FormGroup(this.controls);

  readonly formRequestedApprovers = new Set<string>();
  @ViewChild('approversInput') approversInputEl!: ElementRef<HTMLInputElement>;
  readonly approverSuggestions$;

  // `approvalParams` emits whenever `submitRequest` is called.
  @Output() readonly approvalParams;
  private readonly submit$;
  submitRequest(event?: Event) {
    event?.preventDefault();
    this.submit$.next();
  }

  readonly ccEmail$;

  readonly defaultAccessDurationDays$;

  readonly maxAccessDurationDays$;

  durationHint$?: Observable<string | undefined>;

  readonly requestInProgress$;

  readonly submitDisabled$;

  readonly error$;

  constructor(
    private readonly route: ActivatedRoute,
    private readonly approvalCardLocalStore: ApprovalCardLocalStore,
    private readonly configGlobalStore: ConfigGlobalStore,
    private readonly router: Router,
    private readonly location: Location,
  ) {
    this.approverSuggestions$ =
      this.approvalCardLocalStore.approverSuggestions$.pipe(
        map((approverSuggestions) =>
          (approverSuggestions ?? []).filter(
            (username) => !this.formRequestedApprovers.has(username),
          ),
        ),
      );
    this.approvalParams = new EventEmitter<ApprovalParams>();
    this.submit$ = new Subject<void>();
    this.ccEmail$ = this.configGlobalStore.approvalConfig$.pipe(
      map((config) => config.optionalCcEmail),
    );
    this.defaultAccessDurationDays$ = this.configGlobalStore.uiConfig$.pipe(
      map(
        (config) =>
          Number(config.defaultAccessDurationSeconds) / (24 * 60 * 60),
      ),
    );
    this.maxAccessDurationDays$ = this.configGlobalStore.uiConfig$.pipe(
      map((config) => {
        this.controls.duration.setValidators([
          DurationFormControl.defaultTimeValidator(
            false,
            Number(config.maxAccessDurationSeconds),
          ),
        ]);
        return Number(config.maxAccessDurationSeconds) / (24 * 60 * 60);
      }),
    );
    this.requestInProgress$ = this.requestApprovalStatus$.pipe(
      map((status) => status?.status === RequestStatusType.SENT),
    );
    this.submitDisabled$ = this.requestApprovalStatus$.pipe(
      map(
        (status) =>
          status?.status === RequestStatusType.SENT ||
          status?.status === RequestStatusType.SUCCESS,
      ),
    );
    this.error$ = this.requestApprovalStatus$.pipe(
      map((status) =>
        status?.status === RequestStatusType.ERROR ? status.error : null,
      ),
    );
    // Trigger the suggestion of previously requested approvers.
    this.approvalCardLocalStore.suggestApprovers('');

    this.controls.approvers.valueChanges.subscribe((value) => {
      this.approvalCardLocalStore.suggestApprovers(value ?? '');
    });

    this.route.queryParams
      .pipe(takeUntil(this.ngOnDestroy.triggered$))
      .subscribe((params) => {
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

        if (this.editableDuration && this.showDurationInput) {
          const expirationTimeUs = String(
            (new Date().getTime() + this.controls.duration.value * 1000) * 1000,
          );
          this.approvalParams.emit({approvers, reason, cc, expirationTimeUs});
        } else {
          this.approvalParams.emit({approvers, reason, cc});
        }
      });
  }

  ngAfterViewInit() {
    if (this.validateOnStart) {
      // Mark reason as touched so validator is triggered.
      this.controls.reason.markAsTouched();
    }

    this.configGlobalStore.uiConfig$
      .pipe(
        filter(isNonNull),
        // We don't want to reset the form on each poll, only once.
        take(1),
        tap((config) => {
          this.controls.duration.setValue(config.defaultAccessDurationSeconds);
          this.durationHint$ = this.controls.duration.printableStringLong$.pipe(
            startWith(
              toDurationString(
                Number(config.defaultAccessDurationSeconds),
                'long',
              ),
            ),
          );
        }),
      )
      .subscribe();
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

  toggleDurationInputField() {
    this.showDurationInput = !this.showDurationInput;
  }
}
