/**
 * Test helpers.
 */
// tslint:disable:enforce-comments-on-exported-symbols

import {ApprovalCardLocalStore} from './approval_card_local_store';
import {MockStore, mockStore} from './store_test_util';

export declare interface ApprovalCardLocalStoreMock
  extends MockStore<ApprovalCardLocalStore> {}

export function mockApprovalCardLocalStore() {
  return mockStore(ApprovalCardLocalStore);
}
