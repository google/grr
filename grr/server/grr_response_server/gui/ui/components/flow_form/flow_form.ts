import {AfterViewInit, ChangeDetectionStrategy, Component, ElementRef, OnDestroy, OnInit, ViewChild} from '@angular/core';
import {BehaviorSubject, combineLatest, fromEvent} from 'rxjs';
import {map, startWith, takeUntil, withLatestFrom} from 'rxjs/operators';

import {RequestStatusType} from '../../lib/api/track_request';
import {observeOnDestroy} from '../../lib/reactive';
import {ClientPageGlobalStore} from '../../store/client_page_global_store';
import {FlowArgsForm} from '../flow_args_form/flow_args_form';

/**
 * Component that allows selecting, configuring, and starting a Flow.
 */
@Component({
  selector: 'flow-form',
  templateUrl: './flow_form.ng.html',
  styleUrls: ['./flow_form.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FlowForm implements OnInit, OnDestroy, AfterViewInit {
  readonly ngOnDestroy = observeOnDestroy(this);

  readonly selectedFD$ = this.clientPageGlobalStore.selectedFlowDescriptor$;

  @ViewChild('form') form!: ElementRef<HTMLFormElement>;

  @ViewChild(FlowArgsForm) flowArgsForm!: FlowArgsForm;

  private readonly flowArgsFormValid$ = new BehaviorSubject<boolean>(true);

  readonly disabled$ =
      combineLatest([
        this.flowArgsFormValid$,
        this.clientPageGlobalStore.startFlowStatus$,
      ])
          .pipe(
              map(([valid, startFlowStatus]) => !valid ||
                      startFlowStatus?.status === RequestStatusType.SENT),
              startWith(false),
          );

  readonly requestInProgress$ =
      this.clientPageGlobalStore.startFlowStatus$.pipe(
          map(status => status?.status === RequestStatusType.SENT),
      );

  readonly error$ = this.clientPageGlobalStore.startFlowStatus$.pipe(
      map(status => status?.status === RequestStatusType.ERROR ? status.error :
                                                                 undefined));

  readonly hasAccess$ =
      this.clientPageGlobalStore.hasAccess$.pipe(startWith(false));

  constructor(
      private readonly clientPageGlobalStore: ClientPageGlobalStore,
  ) {}

  ngOnInit() {}

  ngAfterViewInit() {
    fromEvent(this.form.nativeElement, 'submit')
        .pipe(
            takeUntil(this.ngOnDestroy.triggered$),
            withLatestFrom(this.flowArgsForm.flowArgValues$, this.hasAccess$),
            )
        .subscribe(([e, flowArgs, hasApproval]) => {
          e.preventDefault();

          if (hasApproval) {
            this.clientPageGlobalStore.startFlow(flowArgs);
          } else {
            this.clientPageGlobalStore.scheduleFlow(flowArgs);
          }
        });

    this.flowArgsForm.valid$.pipe(takeUntil(this.ngOnDestroy.triggered$))
        .subscribe(this.flowArgsFormValid$);
  }
}
