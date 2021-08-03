/** Test helpers. */
// tslint:disable:enforce-comments-on-exported-symbols

import {ClientSearchGlobalStore} from './client_search_global_store';
import {MockStore, mockStore} from './store_test_util';

export declare interface ClientSearchGlobalStoreMock extends
    MockStore<ClientSearchGlobalStore> {}

export function mockClientSearchGlobalStore() {
  return mockStore(ClientSearchGlobalStore);
}
