/** Test helpers. */
// tslint:disable:enforce-comments-on-exported-symbols

import {HuntApprovalGlobalStore} from './hunt_approval_global_store';
import {MockStore, mockStore} from './store_test_util';

export declare interface HuntApprovalGlobalStoreMock extends
    MockStore<HuntApprovalGlobalStore> {}

export function mockHuntApprovalGlobalStore() {
  return mockStore(HuntApprovalGlobalStore);
}
