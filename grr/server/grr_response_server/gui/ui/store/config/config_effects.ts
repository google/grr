import {Injectable} from '@angular/core';
import {Actions, Effect, ofType} from '@ngrx/effects';
import {Action} from '@ngrx/store';
import {HttpApiService} from '@app/lib/api/http_api_service';
import {translateFlowDescriptor} from '@app/lib/api_translation/flow';
import {Observable} from 'rxjs';
import {map, switchMap} from 'rxjs/operators';

import * as actions from './config_actions';

/** Effects for the Config store. */
@Injectable({providedIn: 'root'})
export class ConfigEffects {
  constructor(
      private readonly actions$: Actions,
      private readonly httpApiService: HttpApiService,
  ) {}

  @Effect()
  listFlowDescriptors$: Observable<Action> = this.actions$.pipe(
      ofType(actions.listFlowDescriptors),
      switchMap(() => this.httpApiService.listFlowDescriptors()),
      map(flowDescriptors => flowDescriptors.map(translateFlowDescriptor)),
      map(flowDescriptors =>
              actions.listFlowDescriptorsComplete({flowDescriptors})),
  );

  @Effect()
  fetchApprovalConfig$: Observable<Action> = this.actions$.pipe(
      ofType(actions.fetchApprovalConfig),
      switchMap(() => this.httpApiService.fetchApprovalConfig()),
      map(approvalConfig =>
              actions.fetchApprovalConfigComplete({approvalConfig})),
  );
}
