import {ChangeDetectionStrategy, Component, EventEmitter, Input, Output} from '@angular/core';
import {FlowListItem, FlowsByCategory} from '@app/components/flow_picker/flow_list_item';
import {BehaviorSubject, Observable} from 'rxjs';
import {map} from 'rxjs/operators';

interface FlowOverviewCategory {
  readonly title: string;
  readonly items: ReadonlyArray<FlowListItem>;
}

/**
 * Component that displays available Flows.
 */
@Component({
  selector: 'flows-overview',
  templateUrl: './flows_overview.ng.html',
  styleUrls: ['./flows_overview.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FlowsOverview {
  private flowsByCategoryInternal: FlowsByCategory = new Map();

  @Input()
  set flowsByCategory(value: FlowsByCategory) {
    this.flowsByCategoryInternal = value;
    this.flowsByCategory$.next(value);
  }

  get flowsByCategory(): FlowsByCategory {
    return this.flowsByCategoryInternal;
  }

  private readonly flowsByCategory$ =
      new BehaviorSubject<FlowsByCategory>(this.flowsByCategoryInternal);

  readonly categories$: Observable<ReadonlyArray<FlowOverviewCategory>> =
      this.flowsByCategory$.pipe(
          map(fbc => {
            const result =
                Array.from(fbc.entries()).map(([categoryTitle, items]) => {
                  const sortedItems = [...items];
                  sortedItems.sort(
                      (a, b) => a.friendlyName.localeCompare(b.friendlyName));
                  return {
                    title: categoryTitle,
                    items: sortedItems,
                  };
                });
            result.sort((a, b) => a.title.localeCompare(b.title));
            return result;
          }),
      );

  /**
   * Event that is triggered when a flow is selected.
   */
  @Output() flowSelected = new EventEmitter<FlowListItem>();

  trackByCategoryTitle(category: FlowOverviewCategory): string {
    return category.title;
  }

  trackByFlowName(fli: FlowListItem): string {
    return fli.name;
  }
}
