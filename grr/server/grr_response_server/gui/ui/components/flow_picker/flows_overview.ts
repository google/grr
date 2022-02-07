import {ChangeDetectionStrategy, Component, EventEmitter, Input, Output} from '@angular/core';
import {BehaviorSubject, Observable} from 'rxjs';
import {map} from 'rxjs/operators';

import {FlowListItem, FlowsByCategory} from '../../components/flow_picker/flow_list_item';
import {compareAlphabeticallyBy} from '../../lib/type_utils';

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
  @Input()
  set flowsByCategory(value: FlowsByCategory|null) {
    this.flowsByCategory$.next(value);
  }

  get flowsByCategory(): FlowsByCategory|null {
    return this.flowsByCategory$.value;
  }

  private readonly flowsByCategory$ =
      new BehaviorSubject<FlowsByCategory|null>(null);

  readonly categories$: Observable<ReadonlyArray<FlowOverviewCategory>> =
      this.flowsByCategory$.pipe(
          map(fbc => {
            const result = Array.from(fbc?.entries() ?? [])
                               .map(([categoryTitle, items]) => {
                                 const sortedItems = [...items];
                                 sortedItems.sort(compareAlphabeticallyBy(
                                     item => item.friendlyName));
                                 return {
                                   title: categoryTitle,
                                   items: sortedItems,
                                 };
                               });
            result.sort(compareAlphabeticallyBy(cat => cat.title));
            return result;
          }),
      );

  /**
   * Event that is triggered when a flow is selected.
   */
  @Output() flowSelected = new EventEmitter<FlowListItem>();

  trackByCategoryTitle(index: number, category: FlowOverviewCategory): string {
    return category.title;
  }

  trackByFlowName(index: number, fli: FlowListItem): string {
    return fli.name;
  }
}
