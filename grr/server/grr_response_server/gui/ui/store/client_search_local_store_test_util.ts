/** Test helpers. */
// tslint:disable:enforce-comments-on-exported-symbols

import {ClientSearchLocalStore} from './client_search_local_store';
import {MockStore, mockStore} from './store_test_util';

export declare interface ClientSearchLocalStoreMock extends
    MockStore<ClientSearchLocalStore> {}

export function mockClientSearchLocalStore() {
  return mockStore(ClientSearchLocalStore);
}
