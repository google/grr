/**
 * @fileoverview NgRx selectors for the Client store.
 */

import {createFeatureSelector, createSelector} from '@ngrx/store';

import {approvalAdapter, clientAdapter, ClientState, flowListEntriesAdapter} from './client_reducers';

/** Feature name of the Client feature. */
export const CLIENT_FEATURE = 'client';

const featureSelector = createFeatureSelector<ClientState>(CLIENT_FEATURE);
const selectClients = clientAdapter.getSelectors().selectEntities;
const selectApprovals = approvalAdapter.getSelectors().selectAll;
const selectFlowListEntries = flowListEntriesAdapter.getSelectors().selectAll;

/** Selector for all clients fetched from the backend. */
export const clients =
    createSelector(featureSelector, state => selectClients(state.clients));

/** Selector for the ID of the currently selected client. */
export const selectedClientId =
    createSelector(featureSelector, state => state.selectedClientId);

/** Selector for the currently fetched approval config. */
export const approvalConfig =
    createSelector(featureSelector, state => state.approvalConfig);

/** Selector for all fetched approvals. */
export const approvals =
    createSelector(featureSelector, state => selectApprovals(state.approvals));

/** Selector for all fetched Flows for the currently selected client. */
export const flowListEntries = createSelector(
    featureSelector, state => selectFlowListEntries(state.flowListEntries));
