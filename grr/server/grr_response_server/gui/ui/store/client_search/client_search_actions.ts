/**
 * @fileoverview Client search store actions.
 */

import {createAction, props} from '@ngrx/store';
import {Client} from '@app/lib/models/client';

/**
 * Triggers a client search fetch with a current search query.
 */
export const fetch = createAction(
    '[ClientSearch] Fetch',
    props<{query: string, count: number}>(),
);

/**
 * Dispatched when a client search fetch is complete.
 */
export const fetchComplete = createAction(
    '[ClientSearch] FetchComplete',
    props<{items: Client[]}>(),
);
