import {ChangeDetectionStrategy, ChangeDetectorRef, Component, ComponentRef, Inject, Injectable, Input, OnChanges, OnDestroy, ViewChild, ViewContainerRef} from '@angular/core';
import {BehaviorSubject} from 'rxjs';
import {filter, map} from 'rxjs/operators';

import {FlowResultViewSection} from '../../../lib/flow_adapters/adapter';
import {PaginatedResultView, PreloadedResultView, ResultQuery, ResultSource, viewQueriesResults} from '../../../lib/models/flow';
import {isNonNull} from '../../../lib/preconditions';
import {observeOnDestroy} from '../../../lib/reactive';
import {FlowResultsLocalStore} from '../../../store/flow_results_local_store';

/** FlowResultViewSection including flow data in the query. */
export interface FlowResultViewSectionWithFullQuery extends
    FlowResultViewSection {
  readonly flow: {readonly clientId: string, readonly flowId: string};
  readonly totalResultCount: number;
}

/** Adapter connecting FlowResultsLocalStore to PaginatedResultView. */
@Injectable()
export class FlowResultSource<T> extends ResultSource<T> {
  constructor(private readonly flowResultLocalStore: FlowResultsLocalStore) {
    super();
  }

  setTotalCount(totalCount: number) {
    this.totalCount$.next(totalCount);
  }

  readonly results$ = this.flowResultLocalStore.results$;
  readonly totalCount$ = new BehaviorSubject<number>(0);
  readonly query$ = this.flowResultLocalStore.query$.pipe(
      filter(isNonNull), map(q => ({type: q.withType, tag: q.withTag})));

  loadResults(query: ResultQuery) {
    this.flowResultLocalStore.queryPage(query);
  }
}


/** Component that displays an expandable flow result row. */
@Component({
  selector: 'app-dynamic-result-section',
  templateUrl: './dynamic_result_section.ng.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [
    FlowResultsLocalStore,
    {provide: ResultSource, useClass: FlowResultSource},
  ],
})
export class DynamicResultSection implements OnDestroy {
  readonly ngOnDestroy = observeOnDestroy(this);

  @Input() section!: FlowResultViewSectionWithFullQuery;

  @ViewChild('viewContainer', {read: ViewContainerRef, static: true})
  viewContainer!: ViewContainerRef;

  protected view?:
      ComponentRef<PreloadedResultView<unknown>|PaginatedResultView<unknown>>;

  constructor(
      protected readonly flowResultsLocalStore: FlowResultsLocalStore,
      @Inject(ResultSource) protected readonly resultSource:
          FlowResultSource<unknown>,
  ) {}

  showResults() {
    this.view = this.viewContainer.createComponent(this.section.component);

    this.resultSource.setTotalCount(this.section.totalResultCount);

    this.flowResultsLocalStore.query({
      withType: this.section.query.type,
      withTag: this.section.query.tag,
      flow: this.section.flow,
    });

    if (!viewQueriesResults(this.view.instance)) {
      this.flowResultsLocalStore.queryMore(this.section.totalResultCount);
    }

    this.flowResultsLocalStore.results$.subscribe(results => {
      const view = this.view?.instance;

      if (!view || viewQueriesResults(view)) {
        return;
      }

      view.data = results.map(result => result.payload);

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
