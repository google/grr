import {Action, createReducer, on} from '@ngrx/store';
import {FlowDescriptorMap} from '@app/lib/models/flow';

import {ApprovalConfig} from '../../lib/models/client';

import * as actions from './config_actions';

/** The state of the Config. */
export interface ConfigState {
  flowDescriptors?: FlowDescriptorMap;
  approvalConfig?: ApprovalConfig;
}

const initialState: ConfigState = {};

const reducer = createReducer(
    initialState,

    on(actions.listFlowDescriptorsComplete,
       (state, {flowDescriptors}) => ({
         ...state,
         flowDescriptors: new Map(flowDescriptors.map(fd => [fd.name, fd])),
       })),

    on(actions.fetchApprovalConfigComplete,
       (state, {approvalConfig}) => ({...state, approvalConfig})),

);

/**
 * Reducer for the Config feature. This function is needed for AoT, see
 * https://github.com/ngrx/platform/pull/2089.
 */
export function configReducer(state: ConfigState|undefined, action: Action) {
  return reducer(state, action);
}
