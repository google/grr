/** Test helpers. */
// tslint:disable:enforce-comments-on-exported-symbols

import {HuntPageLocalStore} from './hunt_page_local_store';
import {MockStore, mockStore} from './store_test_util';

export interface HuntPageLocalStoreMock extends MockStore<HuntPageLocalStore> {}

export function mockHuntPageLocalStore() {
  return mockStore(HuntPageLocalStore);
}
