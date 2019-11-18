/**
 * @fileoverview Client search store effects.
 */

import {Injectable} from '@angular/core';
import {Actions, Effect, ofType} from '@ngrx/effects';
import {Action} from '@ngrx/store';
import {ApiSearchClientResult} from '@app/lib/api/client_api';
import {ClientApiService} from '@app/lib/api/client_api_service';
import {translateClient} from '@app/lib/api_translation/client';
import {Observable, of} from 'rxjs';
import {map, switchMap} from 'rxjs/operators';

import * as actions from './client_search_actions';

/**
 * Client search store effects.
 */
@Injectable({providedIn: 'root'})
export class ClientSearchEffects {
  constructor(
      private readonly actions$: Actions,
      private readonly clientApiService: ClientApiService,
  ) {}

  /**
   * Effect triggering on "fetch" action. Triggers an API call and returns
   * results with "fetchComplete" action.
   */
  @Effect()
  searchClients$: Observable<Action> = this.actions$.pipe(
      ofType(actions.fetch),
      switchMap(({query}) => this.searchClients(query)),
  );

  private searchClients(query: string) {
    let clientsResult: Observable<ApiSearchClientResult>;
    if (query) {
      clientsResult =
          this.clientApiService.searchClients({query, offset: 0, count: 100});
    } else {
      clientsResult = of({items: []});
    }

    return clientsResult.pipe(map(response => {
      return actions.fetchComplete({
        items: response.items.map(translateClient),
      });
    }));
  }
}
