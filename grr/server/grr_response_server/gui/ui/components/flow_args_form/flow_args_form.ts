import {AfterViewInit, ChangeDetectionStrategy, ChangeDetectorRef, Component, ComponentFactoryResolver, Input, OnChanges, OnDestroy, Output, SimpleChanges, ViewChild, ViewContainerRef} from '@angular/core';
import {DEFAULT_FORM, FORMS} from '@app/components/flow_args_form/sub_forms';
import {Observable, ReplaySubject} from 'rxjs';
import {takeUntil} from 'rxjs/operators';

import {FlowDescriptor} from '../../lib/models/flow';
import {observeOnDestroy} from '../../lib/reactive';

/** Component that allows configuring Flow arguments. */
@Component({
  selector: 'flow-args-form',
  template: '<template #formContainer></template>',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FlowArgsForm implements OnChanges, AfterViewInit, OnDestroy {
  readonly ngOnDestroy = observeOnDestroy();

  @Input() flowDescriptor?: FlowDescriptor;

  private readonly flowArgValuesSubject = new ReplaySubject<unknown>(1);
  @Output()
  readonly flowArgValues$: Observable<unknown> = this.flowArgValuesSubject;

  private readonly validSubject = new ReplaySubject<boolean>(1);
  @Output() readonly valid$: Observable<boolean> = this.validSubject;

  @ViewChild('formContainer', {read: ViewContainerRef, static: true})
  formContainer!: ViewContainerRef;

  constructor(
      private readonly resolver: ComponentFactoryResolver,
      private readonly cdr: ChangeDetectorRef,
  ) {}

  ngAfterViewInit() {
    this.update();
  }

  ngOnChanges(changes: SimpleChanges) {
    this.update();
  }

  private update() {
    if (!this.formContainer) {
      return;
    }

    this.formContainer.clear();

    if (!this.flowDescriptor) {
      return;
    }

    const componentClass = FORMS[this.flowDescriptor.name] || DEFAULT_FORM;
    const factory = this.resolver.resolveComponentFactory(componentClass);
    const component = this.formContainer.createComponent(factory);
    component.instance.defaultFlowArgs = this.flowDescriptor.defaultArgs;
    // As it's not clear whether formValues$ observable is supposed to
    // complete when component.instance is destroyed, we should make sure
    // we don't have a hanging subscription left. Hence - takeUntil() pattern.
    component.instance.formValues$.pipe(takeUntil(this.ngOnDestroy.triggered$))
        .subscribe(values => {
          this.flowArgValuesSubject.next(values);
        });
    component.instance.status$.pipe(takeUntil(this.ngOnDestroy.triggered$))
        .subscribe(status => {
          this.validSubject.next(status === 'VALID');
        });

    this.cdr.detectChanges();
  }
}
