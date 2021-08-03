/** Test helpers. */
// tslint:disable:enforce-comments-on-exported-symbols

import {MockStore, mockStore} from './store_test_util';
import {UserGlobalStore} from './user_global_store';


export declare interface UserGlobalStoreMock extends
    MockStore<UserGlobalStore> {}

export function mockUserGlobalStore() {
  return mockStore(UserGlobalStore);
}
