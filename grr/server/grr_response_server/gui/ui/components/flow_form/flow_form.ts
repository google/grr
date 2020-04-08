import {AfterViewInit, ChangeDetectionStrategy, Component, ElementRef, OnDestroy, OnInit, ViewChild} from '@angular/core';
import {ClientFacade} from '@app/store/client_facade';
import {fromEvent, Subject} from 'rxjs';
import {takeUntil, withLatestFrom} from 'rxjs/operators';

import {FlowDescriptor} from '../../lib/models/flow';
import {FlowFacade} from '../../store/flow_facade';
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

  selectedFlow?: FlowDescriptor;
  readonly selectedFlow$ = this.flowFacade.selectedFlow$;
  readonly selectedClient$ = this.clientFacade.selectedClient$;

  @ViewChild('form') form!: ElementRef<HTMLFormElement>;

  @ViewChild(FlowArgsForm) flowArgsForm!: FlowArgsForm;

  constructor(
      private readonly flowFacade: FlowFacade,
      private readonly clientFacade: ClientFacade,
  ) {
    this.flowFacade.selectedFlow$.subscribe(selectedFlow => {
      this.selectedFlow = selectedFlow;
    });
  }

  ngOnInit() {}

  ngAfterViewInit() {
    fromEvent(this.form.nativeElement, 'submit')
        .pipe(
            takeUntil(this.unsubscribe$),
            withLatestFrom(
                this.selectedFlow$, this.selectedClient$,
                this.flowArgsForm.flowArgValues$),
            )
        .subscribe(([e, selectedFlow, selectedClient, flowArgs]) => {
          e.preventDefault();

          if (selectedFlow === undefined) {
            throw new Error('Cannot submit flow form without selected flow.');
          }

          this.clientFacade.startFlow(
              selectedClient.clientId, selectedFlow.name, flowArgs);
        });
  }

  ngOnDestroy() {
    this.unsubscribe$.next();
    this.unsubscribe$.complete();
  }
}
