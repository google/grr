import {ChangeDetectionStrategy, ChangeDetectorRef, Component, ComponentFactoryResolver, ComponentRef, EventEmitter, Input, OnChanges, Output, SimpleChanges, ViewChild, ViewContainerRef} from '@angular/core';
import {Plugin as FlowDetailsPlugin} from '@app/components/flow_details/plugins/plugin';
import {Flow, FlowDescriptor, FlowListEntry} from '@app/lib/models/flow';

import {FLOW_DETAILS_DEFAULT_PLUGIN, FLOW_DETAILS_PLUGIN_REGISTRY} from './plugin_registry';

/** Enum of Actions that can be triggered in the Flow Context Menu. */
export enum FlowMenuAction {
  NONE = 0,
  CANCEL,
  DUPLICATE,
  CREATE_HUNT,
  START_VIA_API,
  DEBUG
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
export class FlowDetails implements OnChanges {
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
   * Event that is triggered when a user expands the details view.
   */
  @Output() expansionToggle = new EventEmitter<void>();

  /**
   * Event that is triggered when a flow context menu action is selected.
   */
  @Output() menuActionTriggered = new EventEmitter<FlowMenuAction>();

  @ViewChild('detailsContainer', {read: ViewContainerRef, static: true})
  detailsContainer!: ViewContainerRef;

  private detailsComponent: ComponentRef<FlowDetailsPlugin>|undefined;

  constructor(
      private readonly componentFactoryResolver: ComponentFactoryResolver,
  ) {}

  ngOnChanges(changes: SimpleChanges) {
    if (this.flowListEntry === undefined) {
      throw new Error('@Input() "flow" is required');
    }

    const componentClass =
        FLOW_DETAILS_PLUGIN_REGISTRY[this.flowListEntry.flow.name] ||
        FLOW_DETAILS_DEFAULT_PLUGIN;
    // Only recreate the component if the component class has changed.
    if (componentClass !== this.detailsComponent?.instance.constructor) {
      const factory =
          this.componentFactoryResolver.resolveComponentFactory(componentClass);
      this.detailsContainer.clear();
      this.detailsComponent = this.detailsContainer.createComponent(factory);
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

  get isExpanded(): boolean {
    return this.flowListEntry.isExpanded;
  }

  triggerExpansionToggle() {
    this.expansionToggle.emit();
  }

  triggerMenuEvent(action: FlowMenuAction) {
    this.menuActionTriggered.emit(action);
  }
}
