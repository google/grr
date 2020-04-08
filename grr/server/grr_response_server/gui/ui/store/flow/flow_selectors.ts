/**
 * @fileoverview NgRx selectors for the flow store.
 */

import {createFeatureSelector, createSelector} from '@ngrx/store';
import {FlowState} from './flow_reducers';

/** Feature name of the flow feature. */
export const FLOW_FEATURE = 'flow';

const featureSelector = createFeatureSelector<FlowState>(FLOW_FEATURE);

/** Selector for the fetched FlowDescriptors. */
export const flowDescriptors =
    createSelector(featureSelector, state => state.flowDescriptors);

/** Selector for the currently selected Flow. */
export const selectedFlow =
    createSelector(featureSelector, state => state.selectedFlow);
