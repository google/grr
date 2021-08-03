/** Test helpers. */
// tslint:disable:enforce-comments-on-exported-symbols

import {HomePageGlobalStore} from './home_page_global_store';
import {mockStore, MockStore} from './store_test_util';

export declare interface HomePageGlobalStoreMock extends
    MockStore<HomePageGlobalStore> {}

export function mockHomePageGlobalStore(): HomePageGlobalStoreMock {
  return mockStore(HomePageGlobalStore);
}
