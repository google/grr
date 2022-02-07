import {ChangeDetectorRef, Directive, Input, OnDestroy, TemplateRef, ViewContainerRef} from '@angular/core';
import {takeUntil} from 'rxjs/operators';

import {FlowResult, FlowResultsQuery} from '../../../lib/models/flow';
import {observeOnDestroy} from '../../../lib/reactive';
import {FlowResultsLocalStore} from '../../../store/flow_results_local_store';

interface Context<R = ReadonlyArray<FlowResult>> {
  results?: R;
  queryMore: (additionalCount: number) => void;
}

interface WithAdapter<R> {
  resultMapper: FlowResultMapFunction<R>;
}

/** Flow query parameter with an optional mapping function. */
export declare interface FlowResultsQueryWithOptionalAdapter<R> extends
    FlowResultsQuery, Partial<WithAdapter<R>> {}

/** Flow query parameter with a mapping function. */
export declare interface FlowResultsQueryWithAdapter<R> extends
    FlowResultsQuery, WithAdapter<R> {}

/** Function that maps optional FlowResults[] to a desired data type.  */
export type FlowResultMapFunction<R> = (results?: ReadonlyArray<FlowResult>) =>
    R;

/** Directive that loads flow results and has callbacks to load more. */
@Directive({
  selector: '[loadFlowResults]',
  providers: [FlowResultsLocalStore],
})
export class LoadFlowResultsDirective<R = ReadonlyArray<FlowResult>> implements
    OnDestroy {
  private readonly context: Context<R>;
  private resultMapper?: FlowResultMapFunction<R>;
  readonly ngOnDestroy = observeOnDestroy(this);

  constructor(
      templateRef: TemplateRef<unknown>,
      viewContainer: ViewContainerRef,
      private readonly changeDetectorRef: ChangeDetectorRef,
      private readonly store: FlowResultsLocalStore,
  ) {
    this.context = {
      queryMore: (additionalCount) => {
        this.store.queryMore(additionalCount);
      }
    };

    viewContainer.createEmbeddedView(templateRef, this.context);

    this.store.results$
        .pipe(
            takeUntil(this.ngOnDestroy.triggered$),
            )
        .subscribe((results) => {
          if (this.resultMapper) {
            this.context.results = this.resultMapper(results);
          } else {
            // When no mapper is provided, FlowResult[] are passed through and
            // this class uses its default generic type.
            this.context.results = (results as unknown) as R;
          }

          this.changeDetectorRef.markForCheck();
        });
  }

  @Input()
  set loadFlowResults(query: FlowResultsQueryWithOptionalAdapter<R>|null|
                      undefined) {
    if (!query) {
      return;  // Ignore initial null values, e.g. from AsyncPipe.
    }

    this.resultMapper = query.resultMapper;
    this.store.query(query);
  }
}
