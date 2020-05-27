import {createAction, props} from '@ngrx/store';
import {FlowDescriptor} from '@app/lib/models/flow';
import {ApprovalConfig} from '../../lib/models/client';

/** Triggers loading static configuration values for the approval. */
export const listFlowDescriptors = createAction('[Flow] ListFlowDescriptors');

/** Dispatched when an approval configuration has been loaded. */
export const listFlowDescriptorsComplete = createAction(
    '[Flow API] ListFlowDescriptors Complete',
    props<{flowDescriptors: ReadonlyArray<FlowDescriptor>}>(),
);

/** Triggers loading static configuration values for the approval. */
export const fetchApprovalConfig = createAction('[Config] FetchApprovalConfig');

/** Dispatched when an approval configuration has been loaded. */
export const fetchApprovalConfigComplete = createAction(
    '[API] FetchApprovalConfig Complete',
    props<{approvalConfig: ApprovalConfig}>(),
);
