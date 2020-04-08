/**
 * @fileoverview NgRx reducers for the flow store.
 */

import {Action, createReducer, on} from '@ngrx/store';
import {FlowDescriptor} from '@app/lib/models/flow';

import * as actions from './flow_actions';

/** Map from Flow name to FlowDescriptor. */
export type FlowDescriptorMap = ReadonlyMap<string, FlowDescriptor>;

/** The state of the flow feature. */
export interface FlowState {
  flowDescriptors?: FlowDescriptorMap;
  selectedFlow?: FlowDescriptor;
}

const initialState: FlowState = {};

const reducer = createReducer(
    initialState,

    on(actions.listFlowDescriptorsComplete,
       (state, {flowDescriptors}) => ({
         ...state,
         flowDescriptors: new Map(flowDescriptors.map(fd => [fd.name, fd])),
       })),

    on(actions.selectFlow,
       (state, {name, args}) => {
         if (state.flowDescriptors === undefined) {
           throw new Error(
               'Called selectFlow, but did not load flowDescriptors.');
         }
         const flowDescriptor = state.flowDescriptors.get(name);
         if (flowDescriptor === undefined) {
           throw new Error(`Selected Flow ${name} is not found.`);
         }

         return {
           ...state,
           selectedFlow: {
             ...flowDescriptor,
             defaultArgs: args ?? flowDescriptor.defaultArgs
           }
         };
       }),

    on(actions.unselectFlow, (state) => ({
                               ...state,
                               selectedFlow: undefined,
                             })),
);

/**
 * Reducer for the flow feature. This function is needed for AoT, see
 * https://github.com/ngrx/platform/pull/2089.
 */
export function flowReducer(state: FlowState|undefined, action: Action) {
  return reducer(state, action);
}
