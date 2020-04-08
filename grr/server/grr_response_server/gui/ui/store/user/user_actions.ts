/**
 * @fileoverview NgRx actions for the user settings store.
 */

import {createAction, props} from '@ngrx/store';
import {GrrUser} from '@app/lib/models/user';

/** Triggers the fetching of the current user. */
export const fetchCurrentUser = createAction('[User] FetchCurrentUser');

/** Dispatched when a user settings fetch is finished. */
export const fetchCurrentUserComplete = createAction(
    '[User API] FetchCurrentUserComplete',
    props<{user: GrrUser}>(),
);
