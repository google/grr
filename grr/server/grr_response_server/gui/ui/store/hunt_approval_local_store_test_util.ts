/** Test helpers. */
// tslint:disable:enforce-comments-on-exported-symbols

import {HuntApprovalLocalStore} from './hunt_approval_local_store';
import {MockStore, mockStore} from './store_test_util';

export declare interface HuntApprovalLocalStoreMock extends
    MockStore<HuntApprovalLocalStore> {}

export function mockHuntApprovalLocalStore() {
  return mockStore(HuntApprovalLocalStore);
}
