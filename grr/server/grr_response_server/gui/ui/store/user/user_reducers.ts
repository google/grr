/**
 * @fileoverview NgRx reducers for the user settings store.
 */

import {createEntityAdapter, EntityState} from '@ngrx/entity';
import {Action, createReducer, on} from '@ngrx/store';
import {GrrUser} from '@app/lib/models/user';

import * as actions from './user_actions';

/** The state of the flow feature. */
export interface UserState {
  readonly currentUserName: string;
  readonly users: EntityState<GrrUser>;
}

/** Adapter for managing the user entity collection. */
export const usersAdapter =
    createEntityAdapter<GrrUser>({selectId: user => user.name});

const initialState: UserState = {
  currentUserName: '',
  users: usersAdapter.getInitialState(),
};

const reducer = createReducer(
    initialState,

    // Updates the users list and the current user name.
    on(actions.fetchCurrentUserComplete,
       (state, {user}) => ({
         ...state,
         currentUserName: user.name,
         users: usersAdapter.upsertOne(user, state.users)
       })),
);

/**
 * Reducer for the flow feature. This function is needed for AoT, see
 * https://github.com/ngrx/platform/pull/2089.
 */
export function userReducer(state: UserState|undefined, action: Action) {
  return reducer(state, action);
}
