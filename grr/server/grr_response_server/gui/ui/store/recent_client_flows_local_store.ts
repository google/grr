import {Injectable} from '@angular/core';
import {ComponentStore} from '@ngrx/component-store';
import {combineLatest, Observable, of, throwError} from 'rxjs';
import {catchError, distinctUntilChanged, map, shareReplay, startWith, switchMap, takeWhile} from 'rxjs/operators';

import {HttpApiService, MissingApprovalError} from '../lib/api/http_api_service';
import {translateFlow} from '../lib/api_translation/flow';
import {Flow} from '../lib/models/flow';
import {compareDateNewestFirst} from '../lib/type_utils';

interface RecentClientFlowsStoreState {
  readonly clientId?: string;
}

interface FlowListState {
  flows?: Flow[];
}

const LIST_FLOWS_COUNT = 3;

class RecentClientFlowsComponentStore extends
    ComponentStore<RecentClientFlowsStoreState> {
  constructor(private readonly httpApiService: HttpApiService) {
    super({});
  }

  /** Reducer resetting the store and setting the clientId. */
  readonly selectClient = this.updater<string>((state, clientId) => {
    if (state.clientId === clientId) {
      return state;
    }

    // Clear complete state when new client is selected to prevent stale
    // information.
    return {clientId};
  });

  /** An observable emitting the client id of the selected client. */
  readonly selectedClientId$: Observable<string|null> =
      this.select(state => state.clientId ?? null)
          .pipe(
              distinctUntilChanged(),
          );

  /** An observable emitting the access status for a client. */
  readonly hasAccess$: Observable<boolean|null> = this.selectedClientId$.pipe(
      switchMap(
          clientId => clientId ?
              this.httpApiService.subscribeToVerifyClientAccess(clientId).pipe(
                  takeWhile(hasAccess => !hasAccess, true),
                  startWith(null),
                  ) :
              of(null)),
      shareReplay({bufferSize: 1, refCount: true}),
  );

  private subscribeToFlowsForClient(clientId: string):
      Observable<FlowListState> {
    return this.httpApiService
        .subscribeToFlowsForClient({
          clientId,
          count: LIST_FLOWS_COUNT.toString(),
          topFlowsOnly: true,
          humanFlowsOnly: true,
        })
        .pipe(
            map(apiFlows =>
                    apiFlows.map(translateFlow)
                        .sort(compareDateNewestFirst(f => f.startedAt))),
            map(flows => ({flows}) as FlowListState),
            catchError<FlowListState, Observable<FlowListState>>(
                err => (err instanceof MissingApprovalError) ?
                    of({flows: []} as FlowListState) :
                    throwError(err)),
        );
  }

  /** An observable emitting current flow list entries sorted by start time. */
  readonly flowListEntries$: Observable<FlowListState> =
      combineLatest([this.selectedClientId$, this.hasAccess$])
          .pipe(
              switchMap(
                  ([clientId, hasAccess]) => (clientId && hasAccess) ?
                      this.subscribeToFlowsForClient(clientId) :
                      of({flows: []})),
              shareReplay({bufferSize: 1, refCount: true}),
              catchError<FlowListState, Observable<FlowListState>>(
                  err => (err instanceof MissingApprovalError) ?
                      of({flows: []} as FlowListState) :
                      throwError(err)),
          );
}

/** Per-component Store for getting the top 3 flows for a recent client. */
@Injectable()
export class RecentClientFlowsLocalStore {
  constructor(private readonly httpApiService: HttpApiService) {}

  private readonly store =
      new RecentClientFlowsComponentStore(this.httpApiService);

  readonly flowListEntries$: Observable<FlowListState> =
      this.store.flowListEntries$;

  /** Selects a client with a given id. */
  selectClient(clientId: string): void {
    this.store.selectClient(clientId);
  }
}