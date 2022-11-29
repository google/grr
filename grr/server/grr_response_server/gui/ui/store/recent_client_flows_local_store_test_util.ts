/** Test helpers. */
// tslint:disable:enforce-comments-on-exported-symbols

import {RecentClientFlowsLocalStore} from './recent_client_flows_local_store';
import {mockStore, MockStore} from './store_test_util';

export declare interface RecentClientFlowsLocalStoreMock extends
    MockStore<RecentClientFlowsLocalStore> {}

export function mockRecentClientFlowsLocalStore() {
  return mockStore(RecentClientFlowsLocalStore);
}
