import {AfterViewInit, ChangeDetectionStrategy, Component, ComponentFactoryResolver, Input, OnChanges, OnDestroy, Output, SimpleChanges, ViewChild, ViewContainerRef} from '@angular/core';
import {DEFAULT_FORM, FORMS} from '@app/components/flow_args_form/sub_forms';
import {Observable, Subject} from 'rxjs';
import {takeUntil} from 'rxjs/operators';

import {FlowDescriptor} from '../../lib/models/flow';

/** Component that allows configuring Flow arguments. */
@Component({
  selector: 'flow-args-form',
  template: '<template #formContainer></template>',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FlowArgsForm implements OnChanges, AfterViewInit, OnDestroy {
  private readonly unsubscribe$ = new Subject<void>();

  @Input() flowDescriptor?: FlowDescriptor;

  private readonly flowArgValuesSubject = new Subject<unknown>();
  @Output()
  readonly flowArgValues$: Observable<unknown> = this.flowArgValuesSubject;

  @ViewChild('formContainer', {read: ViewContainerRef, static: true})
  formContainer!: ViewContainerRef;

  constructor(
      private readonly resolver: ComponentFactoryResolver,
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
    component.instance.formValues$.pipe(takeUntil(this.unsubscribe$))
        .subscribe(values => {
          this.flowArgValuesSubject.next(values);
        });
  }

  ngOnDestroy() {
    this.unsubscribe$.next();
    this.unsubscribe$.complete();
  }
}
