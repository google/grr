import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  OnDestroy,
  OnInit,
  ViewChild,
} from '@angular/core';
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
  standalone: false,
  selector: 'flow-form',
  templateUrl: './flow_form.ng.html',
  styleUrls: ['./flow_form.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FlowForm implements OnInit, OnDestroy, AfterViewInit {
  readonly ngOnDestroy = observeOnDestroy(this);

  readonly selectedFD$;

  @ViewChild('form') formElement!: ElementRef<HTMLFormElement>;

  @ViewChild(FlowArgsForm) flowArgsForm!: FlowArgsForm;

  private readonly flowArgsFormValid$;

  readonly disabled$;

  readonly requestInProgress$;

  readonly error$;

  readonly hasAccess$;

  constructor(private readonly clientPageGlobalStore: ClientPageGlobalStore) {
    this.selectedFD$ = this.clientPageGlobalStore.selectedFlowDescriptor$;
    this.flowArgsFormValid$ = new BehaviorSubject<boolean>(true);
    this.disabled$ = combineLatest([
      this.flowArgsFormValid$,
      this.clientPageGlobalStore.startFlowStatus$,
    ]).pipe(
      map(
        ([valid, startFlowStatus]) =>
          !valid || startFlowStatus?.status === RequestStatusType.SENT,
      ),
      startWith(false),
    );
    this.requestInProgress$ = this.clientPageGlobalStore.startFlowStatus$.pipe(
      map((status) => status?.status === RequestStatusType.SENT),
    );
    this.error$ = this.clientPageGlobalStore.startFlowStatus$.pipe(
      map((status) =>
        status?.status === RequestStatusType.ERROR ? status.error : undefined,
      ),
    );
    this.hasAccess$ = this.clientPageGlobalStore.hasAccess$.pipe(
      startWith(false),
    );
  }

  ngOnInit() {}

  ngAfterViewInit() {
    fromEvent(this.formElement.nativeElement, 'submit')
      .pipe(
        takeUntil(this.ngOnDestroy.triggered$),
        withLatestFrom(this.flowArgsForm.flowArgValues$, this.disabled$),
      )
      .subscribe(([e, flowArgs, disabled]) => {
        e.preventDefault();

        if (!disabled) {
          this.clientPageGlobalStore.scheduleOrStartFlow(flowArgs);
        }
      });

    this.flowArgsForm.valid$
      .pipe(takeUntil(this.ngOnDestroy.triggered$))
      .subscribe((valid) => {
        this.flowArgsFormValid$.next(valid);
      });
  }
}
