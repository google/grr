import {createFeatureSelector, createSelector} from '@ngrx/store';

import {ConfigState} from './config_reducers';

/** Feature name of the Config feature. */
export const CONFIG_FEATURE = 'config';

const featureSelector = createFeatureSelector<ConfigState>(CONFIG_FEATURE);

/** Selector for the fetched FlowDescriptors. */
export const flowDescriptors =
    createSelector(featureSelector, state => state.flowDescriptors);

/** Selector for the currently fetched approval config. */
export const approvalConfig =
    createSelector(featureSelector, state => state.approvalConfig);
