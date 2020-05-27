import {Dictionary} from '@ngrx/entity';
import {createAction, props} from '@ngrx/store';
import {ApprovalRequest, Client, ClientApproval} from '@app/lib/models/client';
import {Flow, FlowListEntry, FlowResultSet, FlowResultsQuery} from '@app/lib/models/flow';

/** Triggers fetching a client and marking it as selected. */
export const select = createAction(
    '[Client] Select',
    props<{clientId: string}>(),
);

/** Triggers the fetching of a client by its ID. */
export const fetch = createAction(
    '[Client] Fetch',
    props<{clientId: string}>(),
);

/** Dispatched when a client has been fetched. */
export const fetchComplete = createAction(
    '[Client API] FetchComplete',
    props<{client: Client}>(),
);

/** Requests an approval for a client for the current user. */
export const requestApproval = createAction(
    '[Client] RequestApproval',
    props<{request: ApprovalRequest}>(),
);

/** Dispatched when an approval request has been sent. */
export const requestApprovalComplete = createAction(
    '[Client API] RequestApproval Complete',
    props<{approval: ClientApproval}>());

/** Triggers the fetching of a client by its ID. */
export const listApprovals = createAction(
    '[Client] ListApprovals',
    props<{clientId: string}>(),
);

/**
 * Dispatched when a client has been fetched.
 *
 * Approvals are in reversed chronological order.
 */
export const listApprovalsComplete = createAction(
    '[Client API] ListApprovals Complete',
    props<{approvals: ClientApproval[]}>(),
);

/**
 * Dispatched when a subset of executed Flows has been fetched from the server.
 *
 * The underlying data source might use pagination and offsets, so `flows` is
 * a subset of all executed flows.
 */
export const listFlowsComplete = createAction(
    '[Client API] ListFlows Complete',
    props<{flows: Flow[]}>(),
);

/** Triggers starting of a Flow on a Client. */
export const startFlow = createAction(
    '[Client] Start Flow',
    props<{flowArgs: unknown}>(),
);

/** Dispatched when a Flow has been started per user request. */
export const startFlowComplete = createAction(
    '[Client API] Start Flow Complete',
    props<{flow: Flow}>(),
);

/** Dispatched when a Flow has been started per user request. */
export const startFlowFailed = createAction(
    '[Client API] Start Flow Failed',
    props<{error: string}>(),
);

/** Dispatched when a flow expansion setting should be toggled. */
export const toggleFlowExpansion = createAction(
    '[Client] toggleFlowExpansion',
    props<{flowId: string}>(),
);

/** Triggers cancellation of a Flow on a Client. */
export const cancelFlow = createAction(
    '[Client] Cancel Flow',
    props<{clientId: string, flowId: string}>(),
);

/** Dispatched when a Flow has been cancelled per user request. */
export const cancelFlowComplete = createAction(
    '[Client API] Cancel Flow Complete',
    props<{flow: Flow}>(),
);

/** Dispatched to update flows on a given client. */
export const updateFlows = createAction(
    '[Client] Update Flows',
    props<{clientId: string}>(),
);

/** Dispatched when updated flows are fetched. */
export const updateFlowsComplete = createAction(
    '[Client API] Update Flows Complete',
    props<{flows: Flow[]}>(),
);

/** Dispatched when a Flow has been selected. */
export const startFlowConfiguration = createAction(
    '[Flow Form] Start Flow Configuration',
    props<{name: string, initialArgs?: unknown}>(),
);

/** Dispatched when the Flow selection is removed. */
export const stopFlowConfiguration =
    createAction('[Flow Form] Stop Flow Configuration');

/** Dispatched to update flow results. */
export const listFlowResults = createAction(
    '[Client] List Flow Results',
    props<{query: FlowResultsQuery}>(),
);

/** Dispatched when an list flow results response is received from the API. */
export const listFlowResultsComplete = createAction(
    '[Client API] List Flow Results Complete',
    props<{resultSet: FlowResultSet}>());

/** Dispatched to update results of multiple flows. */
export const updateFlowsResults = createAction(
    '[Client] Update Flows Results',
    props<{clientId: string, flowListEntries: Dictionary<FlowListEntry>}>(),
);

/** Dispatched when results of multiple flows update is received. */
export const updateFlowsResultsComplete = createAction(
    '[Client API] Update Flows Results Complete',
    props<{results: ReadonlyArray<FlowResultSet>}>(),
);
