/**
 * @fileoverview NgRx effects for the user settings store.
 */

import {Injectable} from '@angular/core';
import {Actions, Effect, ofType} from '@ngrx/effects';
import {Action} from '@ngrx/store';
import {HttpApiService} from '@app/lib/api/http_api_service';
import {translateGrrUser} from '@app/lib/api_translation/user';
import {Observable} from 'rxjs';
import {map, switchMap} from 'rxjs/operators';
import * as actions from './user_actions';


/** Effects for the flow store. */
@Injectable({providedIn: 'root'})
export class UserEffects {
  constructor(
      private readonly actions$: Actions,
      private readonly httpApiService: HttpApiService,
  ) {}

  @Effect()
  fetchCurrentUser$: Observable<Action> = this.actions$.pipe(
      ofType(actions.fetchCurrentUser),
      switchMap(() => this.httpApiService.fetchCurrentUser()),
      map(translateGrrUser),
      map(user => actions.fetchCurrentUserComplete({user})),
  );
}
