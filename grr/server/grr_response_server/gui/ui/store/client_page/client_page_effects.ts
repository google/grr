import {Injectable} from '@angular/core';
import {Actions, Effect, ofType} from '@ngrx/effects';
import {Dictionary} from '@ngrx/entity';
import {Action, Store} from '@ngrx/store';
import {HttpApiService} from '@app/lib/api/http_api_service';
import {translateApproval, translateClient} from '@app/lib/api_translation/client';
import {translateFlow, translateFlowResult} from '@app/lib/api_translation/flow';
import {buildUpdateResultsQueries, FlowListEntry, FlowResultSet, FlowResultSetState} from '@app/lib/models/flow';
import {combineLatest, from, Observable, of, ReplaySubject} from 'rxjs';
import {catchError, exhaustMap, filter, map, mergeMap, reduce, startWith, switchMap, withLatestFrom} from 'rxjs/operators';

import {AnyObject} from '../../lib/api/api_interfaces';

import * as actions from './client_page_actions';
import {ClientPageState} from './client_page_reducers';
import * as selectors from './client_page_selectors';



/** Effects for the ClientPage store. */
@Injectable({providedIn: 'root'})
export class ClientPageEffects {
  constructor(
      private readonly actions$: Actions,
      private readonly apiService: HttpApiService,
      private readonly store: Store<ClientPageState>,
  ) {}

  private readonly selectedClientId$ =
      this.store.select(selectors.selectedClientId)
          .pipe(
              filter((clientId): clientId is string => clientId !== undefined),
          );

  /**
   * Effect triggering on "fetch" action. Triggers an API call to fetch a
   * single client and emits results with "fetchComplete" action.
   */
  @Effect()
  fetchClient$: Observable<Action> = this.actions$.pipe(
      ofType(actions.fetch, actions.select),
      switchMap(({clientId}) => this.apiService.fetchClient(clientId)),
      map(translateClient),
      map(client => actions.fetchComplete({client})),
  );

  /**
   * Effect for `requestApproval` action, triggering API call to request an
   * approval.
   */
  @Effect()
  requestApproval$: Observable<Action> = this.actions$.pipe(
      ofType(actions.requestApproval),
      switchMap(({request}) => this.apiService.requestApproval(request)),
      map(translateApproval),
      map((approval) => actions.requestApprovalComplete({approval})),
  );

  @Effect()
  listApprovals$: Observable<Action> = this.actions$.pipe(
      ofType(actions.listApprovals, actions.select),
      switchMap(({clientId}) => this.apiService.listApprovals(clientId)),
      map(approvals => approvals.map(translateApproval)),
      map(approvals => actions.listApprovalsComplete({approvals})),
  );

  @Effect()
  listFlows$: Observable<Action> = this.actions$.pipe(
      ofType(actions.select),
      switchMap(({clientId}) => this.apiService.listFlowsForClient(clientId)),
      map(flows => flows.map(translateFlow)),
      map(flows => actions.listFlowsComplete({flows})),
  );

  @Effect()
  updateFlows$: Observable<Action> = this.actions$.pipe(
      ofType(actions.updateFlows),
      // Using exhaustMap ensures that we do not send too many network
      // requests: a new request will be sent only if the previous one has
      // finished.
      exhaustMap(({clientId}) => this.apiService.listFlowsForClient(clientId)),
      map(flows => flows.map(translateFlow)),
      map(flows => actions.updateFlowsComplete({flows})),
  );

  @Effect()
  listFlowResults$: Observable<Action> = this.actions$.pipe(
      ofType(actions.listFlowResults),
      withLatestFrom(this.selectedClientId$),
      mergeMap(
          ([params, clientId]) => {
            return combineLatest([
              of(params),
              this.apiService.listResultsForFlow(clientId, params.query),
            ]);
          },
          ),
      map(([params, flowResults]) => {
        const translatedResults = flowResults.map(translateFlowResult);
        return actions.listFlowResultsComplete({
          resultSet: {
            sourceQuery: params.query,
            state: FlowResultSetState.FETCHED,
            items: translatedResults,
          },
        });
      }),
  );

  // Keeping previous flow list entries dict so that we can compare the current
  // and the previous state. This is needed to handle an edge case of flows that
  // have just finished. I.e. they have FINISHED state now, but had RUNNING
  // state in the previous snapshot. Such flows are eligible for updates.
  private readonly prevFlowListEntryEntities$ =
      new ReplaySubject<Dictionary<FlowListEntry>>(1);

  @Effect()
  updateFlowsResults$: Observable<Action> = this.actions$.pipe(
      ofType(actions.updateFlowsResults),
      withLatestFrom(
          this.prevFlowListEntryEntities$.pipe(
              startWith({} as Dictionary<FlowListEntry>)),
          ),
      // Using exhaustMap to account for cases when a query may take longer
      // than the polling time.
      exhaustMap(([{clientId, flowListEntries}, prevFlowListEntries]) => {
        this.prevFlowListEntryEntities$.next(flowListEntries);

        const queries =
            buildUpdateResultsQueries(prevFlowListEntries, flowListEntries);
        if (queries.length === 0) {
          return from([]);
        }

        return this.apiService.batchListResultsForFlow(clientId, queries)
            .pipe(
                reduce(
                    (acc, next) => {
                      const translatedResults =
                          next.results.map(translateFlowResult);
                      const resultSet = {
                        sourceQuery: next.params,
                        state: FlowResultSetState.FETCHED,
                        items: translatedResults,
                      };
                      return [resultSet, ...acc];
                    },
                    [] as ReadonlyArray<FlowResultSet>),
            );
      }),
      map((results) => {
        return actions.updateFlowsResultsComplete({results});
      }),
  );

  @Effect()
  startFlow$: Observable<Action> = this.actions$.pipe(
      ofType(actions.startFlow),
      withLatestFrom(
          this.store.select(selectors.selectedClientId),
          this.store.select(selectors.flowInConfiguration)),
      switchMap(([{flowArgs}, selectedClientId, flowInConfiguration]) => {
        if (selectedClientId === undefined) {
          throw new Error('selectClient() before calling startFlow()!');
        }

        if (flowInConfiguration === undefined) {
          throw new Error(
              'startFlowConfiguration() before calling startFlow()!');
        }

        return this.apiService
            .startFlow(
                selectedClientId, flowInConfiguration.name,
                flowArgs as AnyObject)
            .pipe(
                map(translateFlow),
                map(flow => actions.startFlowComplete({flow})),
                // catchError inside switchMap so that @Effect observable is not
                // completed when an error happens.
                catchError(
                    (error: Error) =>
                        of(actions.startFlowFailed({error: error.message}))),
            );
      }),

  );

  @Effect()
  cancelFlow$: Observable<Action> = this.actions$.pipe(
      ofType(actions.cancelFlow),
      switchMap(
          ({clientId, flowId}) => this.apiService.cancelFlow(clientId, flowId)),
      map(translateFlow),
      map(flow => actions.cancelFlowComplete({flow})),
  );

}
