/**
 * @fileoverview Client search store selectors.
 */

import {createFeatureSelector, createSelector} from '@ngrx/store';

import {clientSearchAdapter, ClientSearchState} from './client_search_reducers';

const featureSelector =
    createFeatureSelector<ClientSearchState>('clientSearch');

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
