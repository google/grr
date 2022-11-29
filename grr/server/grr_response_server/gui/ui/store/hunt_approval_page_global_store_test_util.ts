/** Test helpers. */
// tslint:disable:enforce-comments-on-exported-symbols

import {HuntApprovalPageGlobalStore} from './hunt_approval_page_global_store';
import {MockStore, mockStore} from './store_test_util';

export declare interface HuntApprovalPageGlobalStoreMock extends
    MockStore<HuntApprovalPageGlobalStore> {}

export function mockHuntApprovalPageGlobalStore() {
  return mockStore(HuntApprovalPageGlobalStore);
}
