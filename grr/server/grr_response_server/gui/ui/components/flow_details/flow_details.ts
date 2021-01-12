import {ChangeDetectionStrategy, ChangeDetectorRef, Component, ComponentFactoryResolver, ComponentRef, EventEmitter, Input, OnChanges, OnDestroy, Output, SimpleChanges, ViewChild, ViewContainerRef} from '@angular/core';
import {Plugin as FlowDetailsPlugin} from '@app/components/flow_details/plugins/plugin';
import {Flow, FlowDescriptor, FlowListEntry, FlowResultsQuery, FlowState} from '@app/lib/models/flow';
import {Subject} from 'rxjs';
import {takeUntil} from 'rxjs/operators';

import {assertNonNull} from '../../lib/preconditions';

import {FLOW_DETAILS_DEFAULT_PLUGIN, FLOW_DETAILS_PLUGIN_REGISTRY} from './plugin_registry';

/** Enum of Actions that can be triggered in the Flow Context Menu. */
export enum FlowMenuAction {
  NONE = 0,
  CANCEL,
  DUPLICATE,
  CREATE_HUNT,
  START_VIA_API,
  DEBUG,
  VIEW_ARGS,
}

/**
 * Component that displays detailed information about a flow.
 */
@Component({
  selector: 'flow-details',
  templateUrl: './flow_details.ng.html',
  styleUrls: ['./flow_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FlowDetails implements OnChanges, OnDestroy {
  private readonly detailsComponentUnsubscribe$ = new Subject<void>();

  private detailsComponent: ComponentRef<FlowDetailsPlugin>|undefined;

  flowState = FlowState;
  flowMenuAction = FlowMenuAction;

  /**
   * Flow list entry to display.
   */
  @Input() flowListEntry!: FlowListEntry;
  /**
   * Flow descriptor of the flow to display. May be undefined (for example,
   * if a flow got renamed on the backend).
   */
  @Input() flowDescriptor!: FlowDescriptor;

  /**
   * Event that is triggered when additional flow results data is needed to
   * be flow plugin.
   */
  @Output() flowResultsQuery = new EventEmitter<FlowResultsQuery>();

  /**
   * Event that is triggered when a flow context menu action is selected.
   */
  @Output() menuActionTriggered = new EventEmitter<FlowMenuAction>();

  @ViewChild('detailsContainer', {read: ViewContainerRef, static: true})
  detailsContainer!: ViewContainerRef;

  constructor(
      private readonly componentFactoryResolver: ComponentFactoryResolver,
  ) {}

  ngOnChanges(changes: SimpleChanges) {
    assertNonNull(this.flowListEntry, '@Input() flow');

    const componentClass =
        FLOW_DETAILS_PLUGIN_REGISTRY[this.flowListEntry.flow.name] ||
        FLOW_DETAILS_DEFAULT_PLUGIN;
    // Only recreate the component if the component class has changed.
    if (componentClass !== this.detailsComponent?.instance.constructor) {
      this.detailsComponentUnsubscribe$.next();

      const factory =
          this.componentFactoryResolver.resolveComponentFactory(componentClass);
      this.detailsContainer.clear();
      this.detailsComponent = this.detailsContainer.createComponent(factory);

      // Propagate the flowResultsQuery event upwards.
      this.detailsComponent.instance.flowResultsQuery
          .pipe(
              takeUntil(this.detailsComponentUnsubscribe$),
              )
          .subscribe(e => {
            const flowId =
                this.detailsComponent?.instance.flowListEntry.flow.flowId;
            if (!flowId) {
              throw new Error(
                  'Logic error: can\'t determine flow id for a query.');
            }
            this.flowResultsQuery.emit({flowId, ...e});
          });
    }

    if (!this.detailsComponent) {
      throw new Error(
          'detailsComponentInstance was expected to be defined at this point.');
    }

    this.detailsComponent.instance.flowListEntry = this.flowListEntry;
    // If the input bindings are set programmatically and not through a
    // template, and you have OnPush strategy, then change detection won't
    // trigger. We have to explicitly mark the dynamically created component
    // for changes checking.
    //
    // For more context, see this excellent article:
    // https://netbasal.com/things-worth-knowing-about-dynamic-components-in-angular-166ce136b3eb
    // "When we dynamically create a component and insert it into the view by
    // using a ViewContainerRef, Angular will invoke each one of the
    // lifecycle hooks except for the ngOnChanges() hook.
    // The reason for that is the ngOnChanges hook isn’t called when inputs
    // are set programmatically only by the view."
    // Doing this.detailsComponent.changeDetectorRef.detectChanges() won't
    // help since, this way "we’re running detectChanges() on the host view,
    // not on the component itself and because we’re in onPush and setting
    // the input programmatically from Angular perspective nothing has changed."
    this.detailsComponent.injector.get(ChangeDetectorRef).markForCheck();
  }

  get flow(): Flow {
    return this.flowListEntry.flow;
  }

  triggerMenuEvent(action: FlowMenuAction) {
    this.menuActionTriggered.emit(action);
  }

  ngOnDestroy() {
    this.detailsComponentUnsubscribe$.next();
    this.detailsComponentUnsubscribe$.complete();
  }
}
