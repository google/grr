import {Injectable} from '@angular/core';
import {Store} from '@ngrx/store';
import {Client} from '@app/lib/models/client';
import {Observable} from 'rxjs';

import * as actions from './client_search/client_search_actions';
import {ClientSearchState} from './client_search/client_search_reducers';
import * as selectors from './client_search/client_search_selectors';

/**
 * Facade object that hides the details of NgRX implementation from the rest
 * of the code. This would allow us to completely change the store
 * implementation (i.e. switch to websocket-based push-notifications instead of
 * HTTP GET polling) without updating the code using it.
 */
@Injectable({
  providedIn: 'root',
})
export class ClientSearchFacade {
  /**
   * An observable emitting the list of fetched Clients on every search.
   */
  readonly clients$: Observable<Client[]> =
      this.store.select(selectors.clientsSelector);
  /**
   * An observable emitting the current query string every time it gets updated.
   */
  readonly query$: Observable<string> =
      this.store.select(selectors.querySelector);

  constructor(private readonly store: Store<ClientSearchState>) {}

  /**
   * Searches for clients using the current search query.
   */
  searchClients(query: string): void {
    this.store.dispatch(actions.fetch({query, count: 100}));
  }
}
