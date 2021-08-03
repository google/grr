/** Test helpers. */
// tslint:disable:enforce-comments-on-exported-symbols

import {ApprovalPageGlobalStore} from './approval_page_global_store';
import {MockStore, mockStore} from './store_test_util';

export declare interface ApprovalPageGlobalStoreMock extends
    MockStore<ApprovalPageGlobalStore> {}

export function mockApprovalPageGlobalStore() {
  return mockStore(ApprovalPageGlobalStore);
}
