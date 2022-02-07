import {ChangeDetectionStrategy, ChangeDetectorRef, Component, ComponentRef, EventEmitter, Input, OnChanges, Output, SimpleChanges, ViewChild, ViewContainerRef} from '@angular/core';
import {map, startWith} from 'rxjs/operators';

import {ExportMenuItem, Plugin as FlowDetailsPlugin} from '../../components/flow_details/plugins/plugin';
import {Flow, FlowDescriptor, FlowState} from '../../lib/models/flow';
import {isNonNull} from '../../lib/preconditions';
import {FlowResultsLocalStore} from '../../store/flow_results_local_store';
import {UserGlobalStore} from '../../store/user_global_store';

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
  providers: [FlowResultsLocalStore],
})
export class FlowDetails implements OnChanges {
  private detailsComponent: ComponentRef<FlowDetailsPlugin>|undefined;

  flowState = FlowState;
  flowMenuAction = FlowMenuAction;

  /**
   * Flow list entry to display.
   */
  @Input() flow: Flow|null|undefined;

  /**
   * Flow descriptor of the flow to display. May be undefined (for example,
   * if a flow got renamed on the backend).
   */
  @Input() flowDescriptor: FlowDescriptor|null|undefined;

  /**
   * Whether show "Create a hunt" in the menu.
   */
  @Input() showCreateHunt = true;

  /**
   * Event that is triggered when a flow context menu action is selected.
   */
  @Output() menuActionTriggered = new EventEmitter<FlowMenuAction>();

  @ViewChild('detailsContainer', {read: ViewContainerRef, static: true})
  detailsContainer!: ViewContainerRef;

  readonly canaryMode$ = this.userGlobalStore.currentUser$.pipe(
      map(user => user.canaryMode),
      startWith(false),
  );

  constructor(private readonly userGlobalStore: UserGlobalStore) {}

  ngOnChanges(changes: SimpleChanges) {
    if (!this.flow) {
      this.detailsContainer.clear();
      return;
    }

    let componentClass = FLOW_DETAILS_PLUGIN_REGISTRY[this.flow.name];

    // As fallback for flows without details plugin and flows that do not report
    // resultCount metadata, show a default view that links to the old UI.
    if (!componentClass || this.flow.resultCounts === undefined) {
      componentClass = FLOW_DETAILS_DEFAULT_PLUGIN;
    }

    // Only recreate the component if the component class has changed.
    if (componentClass !== this.detailsComponent?.instance.constructor) {
      this.detailsContainer.clear();
      this.detailsComponent =
          this.detailsContainer.createComponent(componentClass);
    }

    if (!this.detailsComponent) {
      throw new Error(
          'detailsComponentInstance was expected to be defined at this point.');
    }

    this.detailsComponent.instance.flow = this.flow;
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

  triggerMenuEvent(action: FlowMenuAction) {
    this.menuActionTriggered.emit(action);
  }

  get resultDescription() {
    return this.flow ?
        this.detailsComponent?.instance?.getResultDescription(this.flow) :
        undefined;
  }

  get exportMenuItems() {
    return (this.flow?.state === FlowState.FINISHED) ?
        this.detailsComponent?.instance?.getExportMenuItems(this.flow) :
        undefined;
  }

  get hasResults() {
    return isNonNull(this.flow?.resultCounts?.find(rc => rc.count > 0));
  }

  trackExportMenuItem(index: number, entry: ExportMenuItem) {
    return entry.title;
  }
}
