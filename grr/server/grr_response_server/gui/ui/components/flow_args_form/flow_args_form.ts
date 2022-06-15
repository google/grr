import {AfterViewInit, ChangeDetectionStrategy, Component, Input, OnChanges, OnDestroy, Output, SimpleChanges, ViewChild, ViewContainerRef} from '@angular/core';
import {Observable, ReplaySubject} from 'rxjs';
import {takeUntil} from 'rxjs/operators';

import {DEFAULT_FORM, FORMS} from '../../components/flow_args_form/sub_forms';
import {FlowDescriptor} from '../../lib/models/flow';
import {observeOnDestroy} from '../../lib/reactive';

import {FlowArgumentForm} from './form_interface';

/** Component that allows configuring Flow arguments. */
@Component({
  selector: 'flow-args-form',
  template: '<template #formContainer></template>',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FlowArgsForm implements OnChanges, AfterViewInit, OnDestroy {
  readonly ngOnDestroy = observeOnDestroy(this, () => {
    this.flowArgValuesSubject.complete();
    this.validSubject.complete();
  });

  @Input() flowDescriptor?: FlowDescriptor|null;

  /**
   * Automatically focus on the first input after the respective
   * FlowArgumentForm is loaded.
   */
  @Input() autofocus?: boolean;

  private readonly flowArgValuesSubject = new ReplaySubject<unknown>(1);
  @Output()
  readonly flowArgValues$: Observable<unknown> =
      this.flowArgValuesSubject.asObservable();

  private readonly validSubject = new ReplaySubject<boolean>(1);
  @Output()
  readonly valid$: Observable<boolean> = this.validSubject.asObservable();

  @ViewChild('formContainer', {read: ViewContainerRef, static: true})
  formContainer!: ViewContainerRef;

  // tslint:disable:no-any Generic type is dynamic at runtime.
  private formComponent?: FlowArgumentForm<{}, any>;

  ngAfterViewInit() {
    this.update();
  }

  ngOnChanges(changes: SimpleChanges) {
    this.update();
  }

  private update() {
    if (!this.formContainer || !this.flowDescriptor) {
      this.formContainer?.clear();
      this.formComponent = undefined;
      return;
    }

    const componentClass = FORMS[this.flowDescriptor.name] || DEFAULT_FORM;

    if (this.formComponent instanceof componentClass) {
      return;
    }

    this.formContainer.clear();

    const componentRef = this.formContainer.createComponent(componentClass);
    const component = componentRef.instance;
    this.formComponent = componentRef.instance;

    component.flowArgs$.pipe(takeUntil(this.ngOnDestroy.triggered$))
        .subscribe(values => {
          this.flowArgValuesSubject.next(values);
        });

    component.form.statusChanges.pipe(takeUntil(this.ngOnDestroy.triggered$))
        .subscribe(status => {
          this.validSubject.next(status === 'VALID');
        });

    componentRef.changeDetectorRef.detectChanges();
    component.resetFlowArgs(this.flowDescriptor.defaultArgs as {});

    if (this.autofocus) {
      component.focus(componentRef.location.nativeElement);
    }
  }
}
