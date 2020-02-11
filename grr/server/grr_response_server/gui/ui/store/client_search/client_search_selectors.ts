/**
 * @fileoverview Client search store selectors.
 */

import {createFeatureSelector, createSelector} from '@ngrx/store';

import {clientSearchAdapter, ClientSearchState} from './client_search_reducers';

/** Feature name of the ClientSearch feature. */
export const CLIENT_SEARCH_FEATURE = 'clientSearch';

const featureSelector =
    createFeatureSelector<ClientSearchState>(CLIENT_SEARCH_FEATURE);

/**
 * Selector for the current search query.
 */
export const querySelector =
    createSelector(featureSelector, state => state.query);

/**
 * Selector for all fetched clients.
 */
export const clientsSelector = createSelector(
    featureSelector, clientSearchAdapter.getSelectors().selectAll);
