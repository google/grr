import {ChangeDetectionStrategy, ChangeDetectorRef, Component, ComponentRef, Input, OnChanges, OnDestroy, ViewChild, ViewContainerRef} from '@angular/core';
import {takeUntil} from 'rxjs/operators';

import {FlowResultViewSection} from '../../../lib/flow_adapters/adapter';
import {PaginatedResultView, PreloadedResultView, viewQueriesResults} from '../../../lib/models/flow';
import {observeOnDestroy} from '../../../lib/reactive';
import {FlowResultsLocalStore} from '../../../store/flow_results_local_store';

/** FlowResultViewSection including flow data in the query. */
export interface FlowResultViewSectionWithFullQuery extends
    FlowResultViewSection {
  readonly flow: {readonly clientId: string, readonly flowId: string};
  readonly totalResultCount: number;
}

/** Component that displays an expandable flow result row. */
@Component({
  selector: 'app-dynamic-result-section',
  templateUrl: './dynamic_result_section.ng.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [FlowResultsLocalStore],
})
export class DynamicResultSection implements OnDestroy {
  readonly ngOnDestroy = observeOnDestroy(this);

  @Input() section!: FlowResultViewSectionWithFullQuery;

  @ViewChild('viewContainer', {read: ViewContainerRef, static: true})
  viewContainer!: ViewContainerRef;

  protected view?:
      ComponentRef<PreloadedResultView<unknown>|PaginatedResultView<unknown>>;

  constructor(protected readonly flowResultsLocalStore: FlowResultsLocalStore) {
  }

  showResults() {
    this.view = this.viewContainer.createComponent(this.section.component);

    if (viewQueriesResults(this.view.instance)) {
      this.view.instance.totalCount = this.section.totalResultCount;
      this.view.instance.loadResults
          .pipe(
              takeUntil(this.ngOnDestroy.triggered$),
              )
          .subscribe(({count, offset}) => {
            this.flowResultsLocalStore.query({
              withType: this.section.query.type,
              withTag: this.section.query.tag,
              flow: this.section.flow,
              count,
              offset,
            });
          });
      this.view.injector.get(ChangeDetectorRef).markForCheck();
    } else {
      this.flowResultsLocalStore.query({
        withType: this.section.query.type,
        withTag: this.section.query.tag,
        count: this.section.totalResultCount,
        flow: this.section.flow,
      });
    }

    this.flowResultsLocalStore.results$.subscribe(results => {
      const view = this.view?.instance;

      if (!view) {
        return;
      } else if (viewQueriesResults(view)) {
        view.results = [...results];
      } else {
        view.data = results.map(result => result.payload);
      }

      // Trigger change detection and ngNonChanges() by calling markForCheck().
      // For an unknown reason, this does not trigger the component's
      // ngOnChanges(), so we trigger the hook manually. ¯\_(ツ)_/¯
      this.view!.injector.get(ChangeDetectorRef).markForCheck();
      if (hasNgOnChanges(view)) {
        view.ngOnChanges({});
      }
    });
  }
}

function hasNgOnChanges(view: {}): view is OnChanges {
  return Boolean((view as Partial<OnChanges>).ngOnChanges);
}
