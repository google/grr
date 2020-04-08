/**
 * @fileoverview NgRx effects for the flow store.
 */

import {Injectable} from '@angular/core';
import {Actions, Effect, ofType} from '@ngrx/effects';
import {Action} from '@ngrx/store';
import {HttpApiService} from '@app/lib/api/http_api_service';
import {translateFlowDescriptor} from '@app/lib/api_translation/flow';
import {Observable} from 'rxjs';
import {map, switchMap} from 'rxjs/operators';

import * as actions from './flow_actions';

/** Effects for the flow store. */
@Injectable({providedIn: 'root'})
export class FlowEffects {
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
}
