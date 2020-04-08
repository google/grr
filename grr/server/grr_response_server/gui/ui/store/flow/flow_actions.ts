/**
 * @fileoverview NgRx actions for the flow store.
 */

import {createAction, props} from '@ngrx/store';
import {FlowDescriptor} from '@app/lib/models/flow';

/** Triggers loading static configuration values for the approval. */
export const listFlowDescriptors = createAction('[Flow] ListFlowDescriptors');

/** Dispatched when an approval configuration has been loaded. */
export const listFlowDescriptorsComplete = createAction(
    '[Flow API] ListFlowDescriptors Complete',
    props<{flowDescriptors: ReadonlyArray<FlowDescriptor>}>(),
);

/** Dispatched when a Flow has been selected. */
export const selectFlow = createAction(
    '[Flow] Select Flow',
    props<{name: string, args?: unknown}>(),
);

/** Dispatched when the Flow selection is removed. */
export const unselectFlow = createAction('[Flow] Unselect Flow');
