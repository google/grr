import {Injectable} from '@angular/core';
import {ComponentStore} from '@ngrx/component-store';
import {ConfigService} from '@app/components/config/config';
import {HttpApiService} from '@app/lib/api/http_api_service';
import {translateFlowResult} from '@app/lib/api_translation/flow';
import {FlowResult, FlowResultsQuery, FlowState} from '@app/lib/models/flow';
import {merge, Observable, timer} from 'rxjs';
import {distinctUntilChanged, filter, map, switchMap, takeUntil, tap, withLatestFrom} from 'rxjs/operators';

import {poll} from '../lib/polling';
import {isNonNull} from '../lib/preconditions';

function baseQueryEqual(a?: FlowResultsQuery, b?: FlowResultsQuery) {
  if (a === b) {  // Both are null or undefined.
    return true;
  }

  return a?.offset === b?.offset && a?.withTag === b?.withTag &&
      a?.withType === b?.withType && a?.flow.clientId === b?.flow.clientId &&
      a?.flow.flowId === b?.flow.flowId;
}

function queryAndCountEqual(a?: FlowResultsQuery, b?: FlowResultsQuery) {
  return baseQueryEqual(a, b) && a?.count === b?.count;
}

interface FlowResultStoreState {
  readonly query?: FlowResultsQuery;
  readonly results?: ReadonlyArray<FlowResult>;
}

class FlowResultsComponentStore extends ComponentStore<FlowResultStoreState> {
  constructor(
      private readonly httpApiService: HttpApiService,
      private readonly configService: ConfigService,
  ) {
    super({});
  }

  /** Observable, emitting the current query. */
  readonly query$ = this.select(state => state.query);

  /** Reducer resetting the store and setting the query. */
  readonly query = this.updater<FlowResultsQuery>((state, query) => {
    if (baseQueryEqual(state.query, query)) {
      return {
        ...state,
        query: {
          ...state.query,
          ...query,
        },
      };
    } else {
      return {query};
    }
  });

  /** Queries `additionalCount` more results. */
  readonly queryMore = this.updater<number>((state, additionalCount) => {
    if (!state.query) {
      return state;
    }

    return {
      ...state,
      query: {
        ...state.query,
        count: (state.query.count ?? 0) + additionalCount,
      },
    };
  });

  private readonly updateFlowResults =
      this.updater<FlowResult[]>((state, results) => ({...state, results}));

  private readonly queryFlowResultsEffect = this.effect<void>(
      obs$ => obs$.pipe(
          withLatestFrom(this.select(state => state.query)),
          map(([, query]) => query),
          filter(isNonNull),
          filter(query => (query.count ?? 0) > 0),
          switchMap((query) => this.httpApiService.listResultsForFlow({
            clientId: query.flow.clientId,
            flowId: query.flow.flowId,
            count: query.count!,
            offset: query.offset,
            withTag: query.withTag,
            withType: query.withType,
          })),
          tap((flowResults) => {
            this.updateFlowResults(flowResults.map(translateFlowResult));
          }),
          ));

  private readonly queryChanged$ =
      this.select(state => state.query)
          .pipe(distinctUntilChanged(queryAndCountEqual));

  private readonly flowFinished$ =
      this.select(state => state.query?.flow.state)
          .pipe(filter(state => state === FlowState.FINISHED));

  /** Observable, emitting the latest results. */
  readonly results$ =
      poll({
        pollOn: merge(
            timer(0, this.configService.config.flowResultsPollingIntervalMs)
                .pipe(takeUntil(this.flowFinished$)),
            this.queryChanged$,
            ),
        pollEffect: this.queryFlowResultsEffect,
        selector: this.select(state => state.results),
      }).pipe(filter(isNonNull));
}

/** Per-component Store for querying Flow results. */
@Injectable()
export class FlowResultsLocalStore {
  constructor(
      private readonly httpApiService: HttpApiService,
      private readonly configService: ConfigService) {}

  // "LocalStore" defines the public interface and proxies to "ComponentStore"
  // to hide away NgRx implementation details.
  private readonly store =
      new FlowResultsComponentStore(this.httpApiService, this.configService);

  /** Observable, emitting the current query. */
  readonly query$ = this.store.query$;

  /** Observable, emitting the latest results. */
  readonly results$ = this.store.results$;

  /** Queries results for the given client, flow, and result filters. */
  query(query: FlowResultsQuery|Observable<FlowResultsQuery>) {
    this.store.query(query);
  }

  /** Queries `additionalCount` more results. */
  queryMore(additionalCount: number) {
    this.store.queryMore(additionalCount);
  }
}
