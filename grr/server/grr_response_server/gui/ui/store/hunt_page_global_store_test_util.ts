/** Test helpers. */
// tslint:disable:enforce-comments-on-exported-symbols

import {HuntPageGlobalStore} from './hunt_page_global_store';
import {MockStore, mockStore} from './store_test_util';

export interface HuntPageGlobalStoreMock extends
    MockStore<HuntPageGlobalStore> {}

export function mockHuntPageGlobalStore() {
  return mockStore(HuntPageGlobalStore);
}
