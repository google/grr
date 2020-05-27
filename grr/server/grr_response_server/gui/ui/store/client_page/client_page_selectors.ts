import {createFeatureSelector, createSelector} from '@ngrx/store';

import {approvalAdapter, clientAdapter, ClientPageState, flowListEntriesAdapter} from './client_page_reducers';

/** Feature name of the ClientPage feature. */
export const CLIENT_PAGE_FEATURE = 'client_page';

const featureSelector =
    createFeatureSelector<ClientPageState>(CLIENT_PAGE_FEATURE);
const selectClients = clientAdapter.getSelectors().selectEntities;
const selectApprovals = approvalAdapter.getSelectors().selectAll;
const selectFlowListEntryEntities =
    flowListEntriesAdapter.getSelectors().selectEntities;
const selectFlowListEntries = flowListEntriesAdapter.getSelectors().selectAll;

/** Selector for all clients fetched from the backend. */
export const clients =
    createSelector(featureSelector, state => selectClients(state.clients));

/** Selector for the ID of the currently selected client. */
export const selectedClientId =
    createSelector(featureSelector, state => state.selectedClientId);

/** Selector for all fetched approvals. */
export const approvals =
    createSelector(featureSelector, state => selectApprovals(state.approvals));

/** Selector for all fetched Flows for the currently selected client. */
export const flowListEntries = createSelector(
    featureSelector, state => selectFlowListEntries(state.flowListEntries));

/** Selector for the map of all the fetched flows. */
export const flowListEntryEntities = createSelector(
    featureSelector,
    state => selectFlowListEntryEntities(state.flowListEntries));

/**
 * Selector for the FlowDescriptor that is being configured by the user,
 * when they use the flow form to start a new flow.
 */
export const flowInConfiguration =
    createSelector(featureSelector, state => state.flowInConfiguration);

/** Selector for the state of the current flow start request. */
export const startFlowState =
    createSelector(featureSelector, state => state.startFlowState);
