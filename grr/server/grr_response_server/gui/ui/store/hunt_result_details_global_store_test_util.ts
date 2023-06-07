/** Test helpers. */
// tslint:disable:enforce-comments-on-exported-symbols

import {HuntResultDetailsGlobalStore} from './hunt_result_details_global_store';
import {MockStore, mockStore} from './store_test_util';

export declare interface HuntResultDetailsGlobalStoreMock extends
    MockStore<HuntResultDetailsGlobalStore> {}

export function mockHuntResultDetailsGlobalStore() {
  return mockStore(HuntResultDetailsGlobalStore);
}