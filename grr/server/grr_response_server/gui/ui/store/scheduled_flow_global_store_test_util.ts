/** Test helpers. */
// tslint:disable:enforce-comments-on-exported-symbols

import {ScheduledFlowGlobalStore} from './scheduled_flow_global_store';
import {MockStore, mockStore} from './store_test_util';

export interface ScheduledFlowGlobalStoreMock extends
    MockStore<ScheduledFlowGlobalStore> {}

export function mockScheduledFlowGlobalStore() {
  return mockStore(ScheduledFlowGlobalStore);
}
