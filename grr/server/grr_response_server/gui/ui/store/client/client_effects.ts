/**
 * @fileoverview NgRx effects for the client store.
 */

import {Injectable} from '@angular/core';
import {Actions, Effect, ofType} from '@ngrx/effects';
import {Action} from '@ngrx/store';
import {HttpApiService} from '@app/lib/api/http_api_service';
import {translateApproval, translateClient} from '@app/lib/api_translation/client';
import {translateFlow} from '@app/lib/api_translation/flow';
import {Observable} from 'rxjs';
import {map, switchMap} from 'rxjs/operators';

import {AnyObject} from '../../lib/api/api_interfaces';

import * as actions from './client_actions';


/** Effects for the client store. */
@Injectable({providedIn: 'root'})
export class ClientEffects {
  constructor(
      private readonly actions$: Actions,
      private readonly apiService: HttpApiService,
  ) {}

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
  fetchApprovalConfig$: Observable<Action> = this.actions$.pipe(
      ofType(actions.fetchApprovalConfig),
      switchMap(() => this.apiService.fetchApprovalConfig()),
      map(approvalConfig =>
              actions.fetchApprovalConfigComplete({approvalConfig})),
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
  startFlow$: Observable<Action> = this.actions$.pipe(
      ofType(actions.startFlow),
      switchMap(
          ({clientId, flowName, flowArgs}) => this.apiService.startFlow(
              clientId, flowName, flowArgs as AnyObject)),
      map(translateFlow),
      map(flow => actions.startFlowComplete({flow})),
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
