import {createEntityAdapter, EntityState} from '@ngrx/entity';
import {Action, createReducer, on} from '@ngrx/store';
import {Client, ClientApproval} from '@app/lib/models/client';
import {findFlowListEntryResultSet, Flow, FlowListEntry, flowListEntryFromFlow, FlowResultSetState, updateFlowListEntryResultSet} from '@app/lib/models/flow';
import * as actions from './client_page_actions';


/** State of the HTTP request to start a new Flow. */
export type StartFlowState = {
  state: 'request_not_sent'
}|{
  state: 'request_sent',
}|{
  state: 'success',
  flow: Flow,
}|{
  state: 'error',
  error: string,
};

/** The state of the ClientPage feature. */
export interface ClientPageState {
  /** Current client that was fetched. */
  clients: EntityState<Client>;
  selectedClientId?: string;
  approvals: EntityState<ClientApproval>;
  flowListEntries: EntityState<FlowListEntry>;
  flowInConfiguration?: {
    name: string,
    initialArgs?: unknown,
  };
  startFlowState: StartFlowState;
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

const initialState: ClientPageState = {
  clients: clientAdapter.getInitialState(),
  approvals: approvalAdapter.getInitialState(),
  flowListEntries: flowListEntriesAdapter.getInitialState(),
  startFlowState: {state: 'request_not_sent'},
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
             flows.map(f => flowListEntryFromFlow(f)), state.flowListEntries)
       })),

    on(actions.updateFlowsComplete,
       (state, {flows}) => {
         const flowsToUpdate = flows.map((f) => {
           const existing = state.flowListEntries.entities[f.flowId];
           if (existing) {
             return {...existing, flow: f};
           } else {
             return flowListEntryFromFlow(f);
           }
         });

         return {
           ...state,
           flowListEntries: flowListEntriesAdapter.upsertMany(
               flowsToUpdate, state.flowListEntries)
         };
       }),

    on(actions.startFlow, (state, {}): ClientPageState => ({
                            ...state,
                            startFlowState: {state: 'request_sent'},
                          })),

    on(actions.startFlowComplete,
       (state, {flow}): ClientPageState => ({
         ...state,
         flowListEntries: flowListEntriesAdapter.upsertOne(
             flowListEntryFromFlow(flow), state.flowListEntries),
         startFlowState: {state: 'success', flow},
         flowInConfiguration: undefined,
       })),

    on(actions.startFlowFailed, (state, {error}): ClientPageState => ({
                                  ...state,
                                  startFlowState: {state: 'error', error},
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
         return {
           ...state,
           flowListEntries: flowListEntriesAdapter.upsertOne(
               {
                 ...fle,
                 isExpanded: !fle.isExpanded,
               },
               state.flowListEntries),
         };
       }),

    on(actions.listFlowResults,
       (state, {query}) => {
         const fle = state.flowListEntries.entities[query.flowId];
         if (!fle) {
           // Assuming that there's no such flow in the list anymore.
           return state;
         }

         const existing =
             findFlowListEntryResultSet(fle, query.withType, query.withTag);
         return {
           ...state,
           flowListEntries: flowListEntriesAdapter.upsertOne(
               updateFlowListEntryResultSet(fle, {
                 state: FlowResultSetState.IN_PROGRESS,
                 sourceQuery: query,
                 items: existing?.items ?? [],
               }),
               state.flowListEntries)
         };
       }),

    on(actions.listFlowResultsComplete,
       (state, {resultSet}) => {
         const fle =
             state.flowListEntries.entities[resultSet.sourceQuery.flowId];
         if (!fle) {
           // Assuming that there's no such flow in the list anymore.
           return state;
         }

         return {
           ...state,
           flowListEntries: flowListEntriesAdapter.upsertOne(
               updateFlowListEntryResultSet(fle, resultSet),
               state.flowListEntries)
         };
       }),

    on(actions.updateFlowsResultsComplete,
       (state, {results}) => {
         const forUpdate = results.reduce((acc, resultSet) => {
           const fle =
               state.flowListEntries.entities[resultSet.sourceQuery.flowId];
           if (!fle) {
             return acc;
           }

           return [updateFlowListEntryResultSet(fle, resultSet), ...acc];
         }, [] as FlowListEntry[]);

         return {
           ...state,
           flowListEntries: flowListEntriesAdapter.upsertMany(
               forUpdate, state.flowListEntries)
         };
       }),

    on(actions.startFlowConfiguration,
       (state, {name, initialArgs}):
           ClientPageState => {
             return {
               ...state,
               flowInConfiguration: {name, initialArgs},
               startFlowState: {state: 'request_not_sent'},
             };
           }),

    on(actions.stopFlowConfiguration,
       (state): ClientPageState => ({
         ...state,
         flowInConfiguration: undefined,
         startFlowState: {state: 'request_not_sent'},
       })),

);

/**
 * Reducer for the Client feature. This function is needed for AoT, see
 * https://github.com/ngrx/platform/pull/2089.
 */
export function clientPageReducer(
    state: ClientPageState|undefined, action: Action) {
  return reducer(state, action);
}
