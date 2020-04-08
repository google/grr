/**
 * @fileoverview NgRx actions for the client store.
 */

import {createAction, props} from '@ngrx/store';
import {ApprovalConfig, ApprovalRequest, Client, ClientApproval} from '@app/lib/models/client';
import {Flow} from '@app/lib/models/flow';

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

/** Triggers loading static configuration values for the approval. */
export const fetchApprovalConfig = createAction('[Client] FetchApprovalConfig');

/** Dispatched when an approval configuration has been loaded. */
export const fetchApprovalConfigComplete = createAction(
    '[Client API] FetchApprovalConfig Complete',
    props<{approvalConfig: ApprovalConfig}>(),
);

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
    props<{clientId: string, flowName: string, flowArgs: unknown}>(),
);

/** Dispatched when a Flow has been started per user request. */
export const startFlowComplete = createAction(
    '[Client API] Start Flow Complete',
    props<{flow: Flow}>(),
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