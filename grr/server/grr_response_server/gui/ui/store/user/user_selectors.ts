/**
 * @fileoverview NgRx selectors for the user store.
 */

import {createFeatureSelector, createSelector} from '@ngrx/store';
import {UserState} from '@app/store/user/user_reducers';

/** Feature name of the user feature. */
export const USER_FEATURE = 'user';

const featureSelector = createFeatureSelector<UserState>(USER_FEATURE);

/** Selector for the current user name. */
export const currentUserName =
    createSelector(featureSelector, state => state.currentUserName);

/** Selector for the current user. */
export const currentUser = createSelector(
    featureSelector, currentUserName,
    (state, userName) => state.users.entities[userName]);
