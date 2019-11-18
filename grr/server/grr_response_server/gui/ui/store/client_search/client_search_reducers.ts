/**
 * @fileoverview Client search store reducers.
 */

import {createEntityAdapter, EntityAdapter, EntityState} from '@ngrx/entity';
import {createReducer, on} from '@ngrx/store';
import {Client} from '@app/lib/models/client';

import * as actions from './client_search_actions';

/**
 * Client search feature state stored in the store. Inherits an EntityState
 * helper that provides an easy way to manage stored collections of entities.
 */
export interface ClientSearchState extends EntityState<Client> {
  /** Current client search query. */
  query: string;
}

/**
 * Client search EntityState adapter providing basic reducers and selectors
 * to manage a collection of Client entities.
 */
export const clientSearchAdapter: EntityAdapter<Client> =
    createEntityAdapter<Client>({
      selectId(client: Client): string {
        return client.clientId;
      },
      sortComparer(a: Client, b: Client): number {
        const bs = b.lastSeenAt || new Date(0);
        const as = a.lastSeenAt || new Date(0);
        return bs.getTime() - as.getTime();
      }
    });

/**
 * Initial client search feature state.
 */
export const INITIAL_CLIENT_SEARCH_STATE = {
  query: '',
  ...clientSearchAdapter.getInitialState()
};

/**
 * Client search feature reducer.
 */
export const clientSearchReducer = createReducer(
    INITIAL_CLIENT_SEARCH_STATE,
    // Sets current query when fetch is started with "fetch" action.
    on(actions.fetch,
       (state, {query}) => {
         return {...state, query};
       }),
    // Updates current collection of Client entities on "fetchComplete" action.
    on(actions.fetchComplete,
       (state, {items}) => {
         return clientSearchAdapter.upsertMany(items, state);
       }),
);
