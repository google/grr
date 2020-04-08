/**
 * @fileoverview NgRx reducers for the client store.
 */

import {createEntityAdapter, EntityState} from '@ngrx/entity';
import {Action, createReducer, on} from '@ngrx/store';
import {ApprovalConfig, Client, ClientApproval} from '@app/lib/models/client';
import {FlowListEntry, flowListEntryFromFlow} from '@app/lib/models/flow';
import * as actions from './client_actions';


/** The state of the client feature. */
export interface ClientState {
  /** Current client that was fetched. */
  clients: EntityState<Client>;
  selectedClientId?: string;
  approvalConfig?: ApprovalConfig;
  approvals: EntityState<ClientApproval>;
  flowListEntries: EntityState<FlowListEntry>;
}

/** Adapter for managing the Client entity collection. */
export const clientAdapter = createEntityAdapter<Client>({
  selectId: client => client.clientId,
});

/** Adapter for managing the ClientApproval entity collection. */
export const approvalAdapter = createEntityAdapter<ClientApproval>({
  selectId: approval => approval.approvalId,
});

/**
 * Adapter for managing the Flow entity collection.
 *
 * Flows are sorted by start Date descendingly.
 */
export const flowListEntriesAdapter = createEntityAdapter<FlowListEntry>({
  selectId: fle => fle.flow.flowId,
  sortComparer: (a, b) =>
      b.flow.startedAt.valueOf() - a.flow.startedAt.valueOf(),
});

const initialState: ClientState = {
  clients: clientAdapter.getInitialState(),
  approvals: approvalAdapter.getInitialState(),
  flowListEntries: flowListEntriesAdapter.getInitialState(),
};

const reducer = createReducer(
    initialState,

    on(actions.select,
       (state, {clientId}) => ({...state, selectedClientId: clientId})),

    // Sets client when fetch has been completed.
    on(actions.fetchComplete,
       (state, {client}) => ({
         ...state,
         clients: clientAdapter.upsertOne(client, state.clients)
       })),

    on(actions.fetchApprovalConfigComplete,
       (state, {approvalConfig}) => ({...state, approvalConfig})),

    on(actions.listApprovalsComplete,
       (state, {approvals}) => ({
         ...state,
         approvals: approvalAdapter.upsertMany(approvals, state.approvals)
       })),

    on(actions.requestApprovalComplete,
       (state, {approval}) => ({
         ...state,
         approvals: approvalAdapter.upsertOne(approval, state.approvals)
       })),

    on(actions.listFlowsComplete,
       (state, {flows}) => ({
         ...state,
         flowListEntries: flowListEntriesAdapter.upsertMany(
             flows.map(flowListEntryFromFlow), state.flowListEntries)
       })),

    on(actions.startFlowComplete,
       (state, {flow}) => ({
         ...state,
         flowListEntries: flowListEntriesAdapter.upsertOne(
             flowListEntryFromFlow(flow), state.flowListEntries)
       })),

    on(actions.cancelFlowComplete,
       (state, {flow}) => ({
         ...state,
         flowListEntries: flowListEntriesAdapter.upsertOne(
             flowListEntryFromFlow(flow), state.flowListEntries)
       })),

    on(actions.toggleFlowExpansion,
       (state, {flowId}) => {
         const fle = state.flowListEntries.entities[flowId];
         if (!fle) {
           throw new Error(
               `Unexpected flow id in toggleFlowExpansion: ${flowId}`);
         }
         const result = {
           ...state,
           flowListEntries: flowListEntriesAdapter.upsertOne(
               {
                 ...fle,
                 isExpanded: !fle.isExpanded,
               },
               state.flowListEntries),
         };
         return result;
       }),
);

/**
 * Reducer for the Client feature. This function is needed for AoT, see
 * https://github.com/ngrx/platform/pull/2089.
 */
export function clientReducer(state: ClientState|undefined, action: Action) {
  return reducer(state, action);
}
