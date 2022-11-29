import {Injectable} from '@angular/core';
import {ComponentStore} from '@ngrx/component-store';
import {Observable} from 'rxjs';
import {distinctUntilChanged, filter, map, shareReplay, switchMap, takeWhile} from 'rxjs/operators';

import {HttpApiService} from '../lib/api/http_api_service';
import {translateFlowResult} from '../lib/api_translation/flow';
import {FlowResultsQuery, FlowState} from '../lib/models/flow';
import {isNonNull} from '../lib/preconditions';

function canMergeQueries(a?: FlowResultsQuery, b?: FlowResultsQuery) {
  if (a === b) {  // Both are null or undefined.
    return true;
  }

  return a?.offset === b?.offset && a?.withTag === b?.withTag &&
      a?.withType === b?.withType && a?.flow.clientId === b?.flow.clientId &&
      a?.flow.flowId === b?.flow.flowId;
}

function queryEquals(a?: FlowResultsQuery, b?: FlowResultsQuery) {
  return canMergeQueries(a, b) && a?.count === b?.count &&
      a?.flow.state === b?.flow.state;
}

interface FlowResultStoreState {
  readonly query?: FlowResultsQuery;
}

class FlowResultsComponentStore extends ComponentStore<FlowResultStoreState> {
  constructor(
      private readonly httpApiService: HttpApiService,
  ) {
    super({});
  }

  /** Observable, emitting the current query. */
  readonly query$ = this.select(state => state.query);

  /** Reducer resetting the store and setting the query. */
  readonly query = this.updater<FlowResultsQuery>((state, query) => {
    if (canMergeQueries(state.query, query)) {
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

  /** Observable, emitting the latest results. */
  readonly results$ =
      this.select(state => state.query)
          .pipe(
              distinctUntilChanged(queryEquals),
              filter(isNonNull),
              filter(query => (query.count ?? 0) > 0),
              switchMap(
                  (query) =>
                      this.httpApiService
                          .subscribeToResultsForFlow({
                            clientId: query.flow.clientId,
                            flowId: query.flow.flowId,
                            count: query.count!,
                            offset: query.offset,
                            withTag: query.withTag,
                            withType: query.withType,
                          })
                          .pipe(
                              takeWhile(
                                  () => query.flow.state !== FlowState.FINISHED,
                                  true),
                              ),
                  ),
              map(flowResults => flowResults.map(translateFlowResult)),
              shareReplay({bufferSize: 1, refCount: true}),
              // Ideally, unsubscription from the last subscriber
              // should ONLY unsubscribe from the polling observable, but
              // retain and replay the latest value.
          );
}

/** Per-component Store for querying Flow results. */
@Injectable()
export class FlowResultsLocalStore {
  constructor(private readonly httpApiService: HttpApiService) {}

  // "LocalStore" defines the public interface and proxies to "ComponentStore"
  // to hide away NgRx implementation details.
  private readonly store = new FlowResultsComponentStore(this.httpApiService);

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
