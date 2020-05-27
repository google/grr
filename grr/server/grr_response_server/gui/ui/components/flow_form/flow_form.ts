import {AfterViewInit, ChangeDetectionStrategy, Component, ElementRef, OnDestroy, OnInit, ViewChild} from '@angular/core';
import {ClientPageFacade} from '@app/store/client_page_facade';
import {fromEvent, Subject} from 'rxjs';
import {map, takeUntil, withLatestFrom} from 'rxjs/operators';

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
  private readonly unsubscribe$ = new Subject<void>();

  readonly selectedFD$ = this.clientPageFacade.selectedFlowDescriptor$;

  @ViewChild('form') form!: ElementRef<HTMLFormElement>;

  @ViewChild(FlowArgsForm) flowArgsForm!: FlowArgsForm;

  readonly disabled$ = new Subject<boolean>();

  readonly error$ = this.clientPageFacade.startFlowState$.pipe(
      map(state => state.state === 'error' ? state.error : undefined));

  constructor(
      private readonly clientPageFacade: ClientPageFacade,
  ) {}

  ngOnInit() {}

  ngAfterViewInit() {
    fromEvent(this.form.nativeElement, 'submit')
        .pipe(
            takeUntil(this.unsubscribe$),
            withLatestFrom(this.flowArgsForm.flowArgValues$),
            )
        .subscribe(([e, flowArgs]) => {
          e.preventDefault();

          this.clientPageFacade.startFlow(flowArgs);
        });

    this.flowArgsForm.valid$.pipe(takeUntil(this.unsubscribe$))
        .subscribe(valid => {
          this.disabled$.next(!valid);
        });
  }

  ngOnDestroy() {
    this.unsubscribe$.next();
    this.unsubscribe$.complete();
  }
}
